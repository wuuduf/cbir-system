"""Train a CIFAR metric-learning model with Triplet Loss for CBIR."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader
from torchvision import transforms
from tqdm import tqdm

from app.core.config import get_settings
from app.core.device import get_device
from app.features.cifar_cnn import build_cifar_resnet18
from scripts.train_cifar_cnn import CIFAR_STATS, CifarBatchDataset, save_checkpoint


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train CIFAR ResNet with CrossEntropy + Triplet Loss"
    )
    parser.add_argument("--dataset", default="cifar10", choices=["cifar10", "cifar100"])
    parser.add_argument(
        "--src",
        default="../data/raw/cifar-10-batches-py",
        help="Path to official CIFAR Python directory",
    )
    parser.add_argument("--label-level", default="fine", choices=["fine", "coarse"])
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=0.01)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--margin", type=float, default=0.2)
    parser.add_argument("--triplet-weight", type=float, default=1.0)
    parser.add_argument("--ce-weight", type=float, default=0.5)
    parser.add_argument("--eval-k", type=int, default=12)
    parser.add_argument("--pretrained", default="../data/models/cifar_resnet18.pt")
    parser.add_argument("--output", default="../data/models/cifar_resnet18_metric.pt")
    parser.add_argument("--amp", action="store_true", help="Use mixed precision on CUDA")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    src = settings.resolve_backend_path(args.src)
    output = settings.resolve_backend_path(args.output)
    pretrained = settings.resolve_backend_path(args.pretrained)
    output.parent.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)

    device = torch.device(get_device())
    train_loader, val_loader, classes, mean, std = build_loaders(src, args)
    model = build_cifar_resnet18(num_classes=len(classes)).to(device)
    load_pretrained_if_available(model, pretrained)

    criterion = nn.CrossEntropyLoss(label_smoothing=0.05)
    optimizer = torch.optim.SGD(
        model.parameters(),
        lr=args.lr,
        momentum=0.9,
        weight_decay=args.weight_decay,
        nesterov=True,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.cuda.amp.GradScaler(enabled=args.amp and device.type == "cuda")

    best_score = -1.0
    best_acc = 0.0
    best_p_at_k = 0.0
    history: list[dict[str, float]] = []
    for epoch in range(1, args.epochs + 1):
        train_metrics = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device, args
        )
        val_loss, val_acc, p_at_k = evaluate(model, val_loader, criterion, device, args.eval_k)
        scheduler.step()
        epoch_record = {
            "epoch": float(epoch),
            **train_metrics,
            "val_loss": val_loss,
            "val_acc": val_acc,
            "p_at_k": p_at_k,
            "lr": float(scheduler.get_last_lr()[0]),
        }
        history.append(epoch_record)
        payload = {
            "epoch": epoch,
            "train_loss": round(train_metrics["train_loss"], 4),
            "triplet_loss": round(train_metrics["triplet_loss"], 4),
            "ce_loss": round(train_metrics["ce_loss"], 4),
            "train_acc": round(train_metrics["train_acc"], 4),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc, 4),
            "p_at_k": round(p_at_k, 4),
        }
        print(json.dumps(payload, ensure_ascii=False))
        score = p_at_k + 0.1 * val_acc
        if score >= best_score:
            best_score = score
            best_acc = val_acc
            best_p_at_k = p_at_k
            save_metric_checkpoint(
                output,
                model,
                classes,
                val_acc,
                p_at_k,
                epoch,
                history,
                args=args,
                mean=mean,
                std=std,
            )
    print(
        json.dumps(
            {
                "best_acc": best_acc,
                "best_p_at_k": best_p_at_k,
                "best_score": best_score,
                "checkpoint": str(output),
            },
            ensure_ascii=False,
        )
    )


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_loaders(
    src: Path, args: argparse.Namespace
) -> tuple[DataLoader, DataLoader, list[str], tuple[float, ...], tuple[float, ...]]:
    stats = CIFAR_STATS[args.dataset]
    mean = stats["mean"]
    std = stats["std"]
    train_transform = transforms.Compose(
        [
            transforms.RandomCrop(32, padding=4),
            transforms.RandomHorizontalFlip(),
            transforms.ToTensor(),
            transforms.Normalize(mean, std),
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.12), ratio=(0.3, 3.3)),
        ]
    )
    val_transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize(mean, std)]
    )
    train_set = CifarBatchDataset(
        src, "train", args.dataset, train_transform, args.label_level
    )
    val_set = CifarBatchDataset(
        src, "test", args.dataset, val_transform, args.label_level
    )
    train_loader = DataLoader(
        train_set,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available(),
        drop_last=True,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=args.batch_size * 2,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader, train_set.classes, mean, std


def load_pretrained_if_available(model: nn.Module, checkpoint_path: Path) -> None:
    if not checkpoint_path.exists():
        return
    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    state = checkpoint.get("model_state")
    if isinstance(state, dict):
        current = model.state_dict()
        compatible = {
            key: value
            for key, value in state.items()
            if key in current and tuple(value.shape) == tuple(current[key].shape)
        }
        model.load_state_dict(compatible, strict=False)


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: torch.cuda.amp.GradScaler,
    device: torch.device,
    args: argparse.Namespace,
) -> dict[str, float]:
    model.train()
    total_loss = 0.0
    total_triplet = 0.0
    total_ce = 0.0
    total_correct = 0
    total = 0
    for images, labels in tqdm(loader, desc="triplet-train", leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.cuda.amp.autocast(enabled=scaler.is_enabled()):
            raw_embeddings = model.forward_features(images)
            embeddings = nn.functional.normalize(raw_embeddings, p=2, dim=1)
            logits = model.fc(raw_embeddings)
            ce_loss = criterion(logits, labels)
            triplet_loss = batch_hard_triplet_loss(embeddings, labels, args.margin)
            loss = args.ce_weight * ce_loss + args.triplet_weight * triplet_loss
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        batch_size = int(images.size(0))
        total_loss += float(loss.item()) * batch_size
        total_ce += float(ce_loss.item()) * batch_size
        total_triplet += float(triplet_loss.item()) * batch_size
        total_correct += int((logits.argmax(dim=1) == labels).sum().item())
        total += batch_size
    return {
        "train_loss": total_loss / total,
        "ce_loss": total_ce / total,
        "triplet_loss": total_triplet / total,
        "train_acc": total_correct / total,
    }


def batch_hard_triplet_loss(
    embeddings: torch.Tensor, labels: torch.Tensor, margin: float
) -> torch.Tensor:
    """Batch-hard triplet loss on L2-normalized embeddings."""

    distances = torch.cdist(embeddings, embeddings, p=2)
    same = labels[:, None].eq(labels[None, :])
    eye = torch.eye(labels.size(0), dtype=torch.bool, device=labels.device)
    positive_mask = same & ~eye
    negative_mask = ~same

    hardest_positive = distances.masked_fill(~positive_mask, 0.0).max(dim=1).values
    max_distance = distances.detach().max().clamp_min(1.0)
    hardest_negative = distances.masked_fill(~negative_mask, max_distance + 1.0).min(
        dim=1
    ).values
    valid = positive_mask.any(dim=1) & negative_mask.any(dim=1)
    losses = torch.relu(hardest_positive - hardest_negative + margin)
    if not bool(valid.any()):
        return losses.mean() * 0.0
    return losses[valid].mean()


@torch.no_grad()
def evaluate(
    model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device, k: int
) -> tuple[float, float, float]:
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total = 0
    embeddings: list[torch.Tensor] = []
    labels_list: list[torch.Tensor] = []
    for images, labels in tqdm(loader, desc="triplet-eval", leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        raw_feats = model.forward_features(images)
        feats = nn.functional.normalize(raw_feats, p=2, dim=1)
        logits = model.fc(raw_feats)
        loss = criterion(logits, labels)
        total_loss += float(loss.item()) * images.size(0)
        total_correct += int((logits.argmax(dim=1) == labels).sum().item())
        total += int(images.size(0))
        embeddings.append(feats.cpu())
        labels_list.append(labels.cpu())
    p_at_k = retrieval_precision_at_k(torch.cat(embeddings), torch.cat(labels_list), k)
    return total_loss / total, total_correct / total, p_at_k


def retrieval_precision_at_k(
    embeddings: torch.Tensor, labels: torch.Tensor, k: int
) -> float:
    """Compute validation P@K from cosine similarity among embeddings."""

    if embeddings.size(0) <= 1:
        return 0.0
    similarity = embeddings @ embeddings.T
    similarity.fill_diagonal_(-1.0)
    top_k = min(k, embeddings.size(0) - 1)
    indices = similarity.topk(top_k, dim=1).indices
    matches = labels[indices].eq(labels[:, None])
    return float(matches.float().mean().item())


def save_metric_checkpoint(
    output: Path,
    model: nn.Module,
    classes: list[str],
    best_acc: float,
    p_at_k: float,
    epoch: int,
    history: list[dict[str, float]],
    *,
    args: argparse.Namespace,
    mean: tuple[float, ...],
    std: tuple[float, ...],
) -> None:
    save_checkpoint(
        output,
        model,
        classes,
        best_acc,
        epoch,
        history,
        dataset=args.dataset,
        mean=mean,
        std=std,
        label_level=args.label_level,
    )
    payload = torch.load(output, map_location="cpu")
    payload.update(
        {
            "training_objective": "cross_entropy_plus_triplet",
            "triplet_margin": float(args.margin),
            "triplet_weight": float(args.triplet_weight),
            "ce_weight": float(args.ce_weight),
            "best_p_at_k": float(p_at_k),
            "eval_k": int(args.eval_k),
        }
    )
    torch.save(payload, output)


if __name__ == "__main__":
    main()
