"""Prepare CIFAR-10 images for the CBIR system."""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image as PillowImage

from app.core.config import get_settings
from app.db import crud
from app.db.database import SessionLocal, init_db
from app.services.dataset_service import load_registry, save_registry

CIFAR_BATCHES = {
    "train": [f"data_batch_{index}" for index in range(1, 6)],
    "test": ["test_batch"],
}
DEFAULT_PER_CLASS = 500
CIFAR10_FULL_PER_CLASS = 6000


def _load_pickle(path: Path) -> dict[bytes, Any]:
    """Load one CIFAR pickle file with byte keys preserved."""

    with path.open("rb") as file:
        return dict(pickle.load(file, encoding="bytes"))


def _load_class_names(src: Path) -> list[str]:
    """Load CIFAR-10 class names from batches.meta."""

    meta_path = src / "batches.meta"
    if not meta_path.exists():
        raise FileNotFoundError(f"缺少 CIFAR 元数据文件: {meta_path}")
    meta = _load_pickle(meta_path)
    label_names = meta.get(b"label_names")
    if not isinstance(label_names, list):
        raise ValueError("batches.meta 中缺少 label_names")
    return [
        name.decode("utf-8") if isinstance(name, bytes) else str(name)
        for name in label_names
    ]


def _selected_batches(split: str) -> list[str]:
    """Return batch filenames for the selected split."""

    if split == "all":
        return CIFAR_BATCHES["train"] + CIFAR_BATCHES["test"]
    if split not in CIFAR_BATCHES:
        raise ValueError("split 必须是 train、test 或 all")
    return CIFAR_BATCHES[split]


def _batch_samples(src: Path, split: str) -> list[tuple[np.ndarray, int]]:
    """Read selected CIFAR batches and return image arrays with labels."""

    samples: list[tuple[np.ndarray, int]] = []
    for batch_name in _selected_batches(split):
        batch_path = src / batch_name
        if not batch_path.exists():
            raise FileNotFoundError(f"缺少 CIFAR batch 文件: {batch_path}")
        batch = _load_pickle(batch_path)
        data = batch.get(b"data")
        labels = batch.get(b"labels")
        if not isinstance(data, np.ndarray) or not isinstance(labels, list):
            raise ValueError(f"CIFAR batch 格式不正确: {batch_path}")
        for flat_image, label in zip(data, labels):
            # 官方 CIFAR-10 每张图以 R/G/B 三段连续存储，这里还原为 32x32x3 RGB。
            rgb = flat_image.reshape(3, 32, 32).transpose(1, 2, 0).astype(np.uint8)
            samples.append((rgb, int(label)))
    return samples


def _target_per_class(per_class: int | None, split: str) -> int:
    """Return the requested per-class sample count."""

    if per_class is not None and per_class > 0:
        return per_class
    if split == "all":
        return CIFAR10_FULL_PER_CLASS
    if split == "test":
        return 1000
    return DEFAULT_PER_CLASS


def _clear_indexes(index_root: Path) -> None:
    """Remove stale indexes because image ids change after re-import."""

    for pattern in ("*.npy", "*.faiss", "meta.json"):
        for existing in index_root.glob(pattern):
            existing.unlink()


def prepare_cifar(
    src: Path, per_class: int | None = DEFAULT_PER_CLASS, split: str = "train"
) -> int:
    """Convert CIFAR-10 batches into JPG files and update DB/registry."""

    settings = get_settings()
    keep_per_class = _target_per_class(per_class, split)
    class_names = _load_class_names(src)
    image_root = settings.data_root_path / "datasets" / "cifar10" / "images"
    index_root = settings.data_root_path / "datasets" / "cifar10" / "index"
    image_root.mkdir(parents=True, exist_ok=True)
    index_root.mkdir(parents=True, exist_ok=True)

    for existing in image_root.glob("*.jpg"):
        existing.unlink()
    _clear_indexes(index_root)

    counters = {name: 0 for name in class_names}
    rows: list[dict[str, object]] = []
    for rgb, label in _batch_samples(src, split):
        category = class_names[label]
        if counters[category] >= keep_per_class:
            continue
        counters[category] += 1
        target_name = f"{category}_{counters[category]:04d}.jpg"
        target_path = image_root / target_name
        # CIFAR 原图是 32x32，检索时会在 preprocess 中统一放大到配置尺寸。
        PillowImage.fromarray(rgb).save(target_path, format="JPEG", quality=95)
        rows.append(
            {
                "dataset": "cifar10",
                "name": target_name,
                "path": f"datasets/cifar10/images/{target_name}",
                "category": category,
                "width": 32,
                "height": 32,
            }
        )
        if all(count >= keep_per_class for count in counters.values()):
            break

    init_db()
    with SessionLocal() as db:
        crud.delete_dataset_images(db, "cifar10")
        if rows:
            crud.bulk_add(db, rows)

    registry = load_registry()
    registry["cifar10"] = {
        "display_name": "CIFAR-10",
        "image_dir": "datasets/cifar10/images",
        "index_dir": "datasets/cifar10/index",
        "count": len(rows),
        "num_classes": sum(1 for count in counters.values() if count > 0),
    }
    save_registry(registry)
    return len(rows)


def main() -> None:
    """Command-line entry."""

    parser = argparse.ArgumentParser(description="Prepare CIFAR-10 dataset")
    parser.add_argument(
        "--src", required=True, type=Path, help="cifar-10-batches-py directory"
    )
    parser.add_argument(
        "--per-class",
        default=None,
        type=int,
        help="Images to keep per class. Omit with --split all for all 6000/class.",
    )
    parser.add_argument(
        "--split", default="train", choices=["train", "test", "all"], help="CIFAR split"
    )
    args = parser.parse_args()
    if not args.src.exists():
        raise FileNotFoundError(f"源目录不存在: {args.src}")
    count = prepare_cifar(args.src, per_class=args.per_class, split=args.split)
    print(f"prepared {count} CIFAR-10 images")


if __name__ == "__main__":
    main()
