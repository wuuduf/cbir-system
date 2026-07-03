"""Train a CIFAR-10 CNN and save it for CBIR deep feature extraction."""

from __future__ import annotations

import argparse
import json
import pickle
import random
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from tqdm import tqdm

from app.core.config import get_settings
from app.core.device import get_device
from app.features.cifar_cnn import build_cifar_resnet18

CIFAR_STATS = {
    "cifar10": {
        "mean": (0.4914, 0.4822, 0.4465),
        "std": (0.2470, 0.2435, 0.2616),
    },
    "cifar100": {
        "mean": (0.5071, 0.4867, 0.4408),
        "std": (0.2675, 0.2565, 0.2761),
    },
}


class CifarBatchDataset(Dataset):
    """Dataset backed by the official CIFAR Python batch files."""

    def __init__(
        self,
        root: Path,
        split: str,
        dataset: str,
        transform=None,
        label_level: str = "fine",
    ) -> None:
        self.root = root
        self.split = split
        self.dataset = dataset
        self.label_level = label_level
        self.transform = transform
        self.classes = self._load_classes()
        files = self._batch_files(split)
        arrays: list[np.ndarray] = []
        labels: list[int] = []
        for name in files:
            with (root / name).open("rb") as file:
                batch = pickle.load(file, encoding="latin1")
            arrays.append(np.asarray(batch["data"], dtype=np.uint8))
            labels.extend(int(label) for label in batch[self._label_key()])
        data = np.vstack(arrays).reshape(-1, 3, 32, 32).transpose(0, 2, 3, 1)
        self.data = data
        self.labels = np.asarray(labels, dtype=np.int64)

    def _load_classes(self) -> list[str]:
        meta_name = "batches.meta" if self.dataset == "cifar10" else "meta"
        with (self.root / meta_name).open("rb") as file:
            meta = pickle.load(file, encoding="latin1")
        key = "label_names"
        if self.dataset == "cifar100":
            key = (
                "fine_label_names"
                if self.label_level == "fine"
                else "coarse_label_names"
            )
        return [str(name) for name in meta[key]]

    def _batch_files(self, split: str) -> list[str]:
        if self.dataset == "cifar10":
            return (
                [f"data_batch_{index}" for index in range(1, 6)]
                if split == "train"
                else ["test_batch"]
            )
        return ["train"] if split == "train" else ["test"]

    def _label_key(self) -> str:
        if self.dataset == "cifar10":
            return "labels"
        return "fine_labels" if self.label_level == "fine" else "coarse_labels"

    def __len__(self) -> int:
        return int(self.labels.shape[0])

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        image = Image.fromarray(self.data[index])
        if self.transform is not None:
            image = self.transform(image)
        return image, int(self.labels[index])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train CIFAR-10 CNN for CBIR")
    parser.add_argument("--dataset", default="cifar10", choices=["cifar10", "cifar100"])
    parser.add_argument(
        "--src",
        default="../data/raw/cifar-10-batches-py",
        help="Path to official cifar-10-batches-py directory",
    )
    parser.add_argument("--label-level", default="fine", choices=["fine", "coarse"])
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--lr", type=float, default=0.1)
    parser.add_argument("--weight-decay", type=float, default=5e-4)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--amp", action="store_true", help="Use mixed precision on CUDA"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Checkpoint output path, relative to backend/",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    src = settings.resolve_backend_path(args.src)
    output_value = args.output or "../data/models/cifar_resnet18.pt"
    output = settings.resolve_backend_path(output_value)
    output.parent.mkdir(parents=True, exist_ok=True)
    set_seed(args.seed)

    device = torch.device(get_device())
    train_loader, val_loader, classes, mean, std = build_loaders(src, args)
    model = build_cifar_resnet18(num_classes=len(classes)).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.SGD(
        model.parameters(),
        lr=args.lr,
        momentum=0.9,
        weight_decay=args.weight_decay,
        nesterov=True,
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    scaler = torch.cuda.amp.GradScaler(enabled=args.amp and device.type == "cuda")

    best_acc = 0.0
    history: list[dict[str, float]] = []
    for epoch in range(1, args.epochs + 1):
        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, scaler, device
        )
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": train_loss,
                "train_acc": train_acc,
                "val_loss": val_loss,
                "val_acc": val_acc,
                "lr": float(scheduler.get_last_lr()[0]),
            }
        )
        print(
            json.dumps(
                {
                    "epoch": epoch,
                    "train_loss": round(train_loss, 4),
                    "train_acc": round(train_acc, 4),
                    "val_loss": round(val_loss, 4),
                    "val_acc": round(val_acc, 4),
                },
                ensure_ascii=False,
            )
        )
        if val_acc >= best_acc:
            best_acc = val_acc
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
    print(
        json.dumps(
            {"best_acc": best_acc, "checkpoint": str(output)}, ensure_ascii=False
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
            transforms.RandomErasing(p=0.25, scale=(0.02, 0.15), ratio=(0.3, 3.3)),
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
    )
    val_loader = DataLoader(
        val_set,
        batch_size=args.batch_size * 2,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available(),
    )
    return train_loader, val_loader, train_set.classes, mean, std


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: torch.cuda.amp.GradScaler,
    device: torch.device,
) -> tuple[float, float]:
    model.train()
    total_loss = 0.0
    total_correct = 0
    total = 0
    for images, labels in tqdm(loader, desc="train", leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        optimizer.zero_grad(set_to_none=True)
        with torch.cuda.amp.autocast(enabled=scaler.is_enabled()):
            logits = model(images)
            loss = criterion(logits, labels)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        total_loss += float(loss.item()) * images.size(0)
        total_correct += int((logits.argmax(dim=1) == labels).sum().item())
        total += int(images.size(0))
    return total_loss / total, total_correct / total


@torch.no_grad()
def evaluate(
    model: nn.Module, loader: DataLoader, criterion: nn.Module, device: torch.device
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    total_correct = 0
    total = 0
    for images, labels in tqdm(loader, desc="eval", leave=False):
        images = images.to(device, non_blocking=True)
        labels = labels.to(device, non_blocking=True)
        logits = model(images)
        loss = criterion(logits, labels)
        total_loss += float(loss.item()) * images.size(0)
        total_correct += int((logits.argmax(dim=1) == labels).sum().item())
        total += int(images.size(0))
    return total_loss / total, total_correct / total


def save_checkpoint(
    output: Path,
    model: nn.Module,
    classes: list[str],
    best_acc: float,
    epoch: int,
    history: list[dict[str, float]],
    *,
    dataset: str,
    mean: tuple[float, ...],
    std: tuple[float, ...],
    label_level: str,
) -> None:
    payload: dict[str, Any] = {
        "arch": "cifar_resnet18",
        "dataset": dataset,
        "model_state": model.state_dict(),
        "classes": classes,
        "class_to_idx": {name: index for index, name in enumerate(classes)},
        "feature_dim": int(getattr(model, "feature_dim", 512)),
        "image_size": 32,
        "mean": mean,
        "std": std,
        "label_level": label_level,
        "best_acc": float(best_acc),
        "epoch": int(epoch),
        "history": history,
    }
    torch.save(payload, output)


if __name__ == "__main__":
    main()
