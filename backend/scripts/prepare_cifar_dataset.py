"""Prepare CIFAR-10 or CIFAR-100 images for the CBIR system."""

from __future__ import annotations

import argparse
import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image as PillowImage

from app.core.config import get_settings
from app.db import crud
from app.db.database import SessionLocal, init_db
from app.services.dataset_service import load_registry, save_registry

CIFAR10_BATCHES = {
    "train": [f"data_batch_{index}" for index in range(1, 6)],
    "test": ["test_batch"],
}
CIFAR100_BATCHES = {"train": ["train"], "test": ["test"]}
DEFAULT_LABEL_LEVEL = "fine"


def prepare_cifar_dataset(
    *,
    dataset: str,
    src: Path,
    split: str = "all",
    per_class: int | None = None,
    label_level: str = DEFAULT_LABEL_LEVEL,
) -> int:
    """Convert official CIFAR batch files into JPG images and DB rows."""

    dataset = dataset.lower()
    if dataset not in {"cifar10", "cifar100"}:
        raise ValueError("dataset 必须是 cifar10 或 cifar100")
    if split not in {"train", "test", "all"}:
        raise ValueError("split 必须是 train、test 或 all")
    if dataset == "cifar10" and label_level != "fine":
        label_level = "fine"
    if dataset == "cifar100" and label_level not in {"fine", "coarse"}:
        raise ValueError("CIFAR-100 label_level 必须是 fine 或 coarse")

    settings = get_settings()
    class_names = _load_class_names(src, dataset, label_level)
    keep_per_class = _target_per_class(dataset, split, per_class, len(class_names))
    image_root = settings.data_root_path / "datasets" / dataset / "images"
    index_root = settings.data_root_path / "datasets" / dataset / "index"
    image_root.mkdir(parents=True, exist_ok=True)
    index_root.mkdir(parents=True, exist_ok=True)

    for existing in image_root.glob("*.jpg"):
        existing.unlink()
    _clear_indexes(index_root)

    counters = {name: 0 for name in class_names}
    rows: list[dict[str, object]] = []
    for rgb, label in _batch_samples(src, dataset, split, label_level):
        category = class_names[label]
        if counters[category] >= keep_per_class:
            continue
        counters[category] += 1
        safe_category = _safe_name(category)
        target_name = f"{safe_category}_{counters[category]:04d}.jpg"
        target_path = image_root / target_name
        PillowImage.fromarray(rgb).save(target_path, format="JPEG", quality=95)
        rows.append(
            {
                "dataset": dataset,
                "name": target_name,
                "path": f"datasets/{dataset}/images/{target_name}",
                "category": category,
                "width": 32,
                "height": 32,
            }
        )
        if all(count >= keep_per_class for count in counters.values()):
            break

    init_db()
    with SessionLocal() as db:
        crud.delete_dataset_images(db, dataset)
        if rows:
            crud.bulk_add(db, rows)

    registry = load_registry()
    registry[dataset] = {
        "display_name": "CIFAR-10" if dataset == "cifar10" else "CIFAR-100",
        "image_dir": f"datasets/{dataset}/images",
        "index_dir": f"datasets/{dataset}/index",
        "count": len(rows),
        "num_classes": sum(1 for count in counters.values() if count > 0),
    }
    save_registry(registry)
    return len(rows)


def _load_pickle(path: Path) -> dict[bytes, Any]:
    with path.open("rb") as file:
        return dict(pickle.load(file, encoding="bytes"))


def _load_class_names(src: Path, dataset: str, label_level: str) -> list[str]:
    meta_path = src / ("batches.meta" if dataset == "cifar10" else "meta")
    if not meta_path.exists():
        raise FileNotFoundError(f"缺少 CIFAR 元数据文件: {meta_path}")
    meta = _load_pickle(meta_path)
    key = b"label_names"
    if dataset == "cifar100":
        key = b"fine_label_names" if label_level == "fine" else b"coarse_label_names"
    label_names = meta.get(key)
    if not isinstance(label_names, list):
        raise ValueError(f"{meta_path} 中缺少 {key.decode('utf-8')}")
    return [
        name.decode("utf-8") if isinstance(name, bytes) else str(name)
        for name in label_names
    ]


def _batch_samples(
    src: Path, dataset: str, split: str, label_level: str
) -> list[tuple[np.ndarray, int]]:
    samples: list[tuple[np.ndarray, int]] = []
    for batch_name in _selected_batches(dataset, split):
        batch_path = src / batch_name
        if not batch_path.exists():
            raise FileNotFoundError(f"缺少 CIFAR batch 文件: {batch_path}")
        batch = _load_pickle(batch_path)
        data = batch.get(b"data")
        label_key = b"labels"
        if dataset == "cifar100":
            label_key = b"fine_labels" if label_level == "fine" else b"coarse_labels"
        labels = batch.get(label_key)
        if not isinstance(data, np.ndarray) or not isinstance(labels, list):
            raise ValueError(f"CIFAR batch 格式不正确: {batch_path}")
        for flat_image, label in zip(data, labels):
            rgb = flat_image.reshape(3, 32, 32).transpose(1, 2, 0).astype(np.uint8)
            samples.append((rgb, int(label)))
    return samples


def _selected_batches(dataset: str, split: str) -> list[str]:
    batches = CIFAR10_BATCHES if dataset == "cifar10" else CIFAR100_BATCHES
    if split == "all":
        return batches["train"] + batches["test"]
    return batches[split]


def _target_per_class(
    dataset: str, split: str, per_class: int | None, num_classes: int
) -> int:
    if per_class is not None and per_class > 0:
        return per_class
    total = {
        ("cifar10", "train"): 5000,
        ("cifar10", "test"): 1000,
        ("cifar10", "all"): 6000,
        ("cifar100", "train"): 500,
        ("cifar100", "test"): 100,
        ("cifar100", "all"): 600,
    }[(dataset, split)]
    if dataset == "cifar100" and num_classes == 20:
        return total * 5
    return total


def _clear_indexes(index_root: Path) -> None:
    for pattern in ("*.npy", "*.faiss", "meta.json"):
        for existing in index_root.glob(pattern):
            existing.unlink()


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value).strip("_").lower() or "class"


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare CIFAR dataset")
    parser.add_argument("--dataset", required=True, choices=["cifar10", "cifar100"])
    parser.add_argument("--src", required=True, type=Path)
    parser.add_argument("--split", default="all", choices=["train", "test", "all"])
    parser.add_argument("--per-class", default=None, type=int)
    parser.add_argument("--label-level", default="fine", choices=["fine", "coarse"])
    args = parser.parse_args()
    count = prepare_cifar_dataset(
        dataset=args.dataset,
        src=args.src,
        split=args.split,
        per_class=args.per_class,
        label_level=args.label_level,
    )
    print(f"prepared {count} {args.dataset.upper()} images")


if __name__ == "__main__":
    main()
