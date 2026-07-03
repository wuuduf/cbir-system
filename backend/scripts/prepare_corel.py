"""Prepare Corel-1000 images for the CBIR system."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image as PillowImage

from app.core.config import get_settings
from app.db import crud
from app.db.database import SessionLocal, init_db
from app.services.dataset_service import load_registry, save_registry

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def infer_category(path: Path, root: Path) -> str:
    """Infer category from subdirectory name or filename prefix."""

    if path.parent != root:
        return path.parent.name
    stem = path.stem
    for separator in ("_", "-", " "):
        if separator in stem:
            return stem.split(separator)[0]
    return "unknown"


def iter_images(src: Path) -> list[Path]:
    """Return all supported image files under src."""

    return sorted(
        path for path in src.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS
    )


def prepare_corel(src: Path) -> int:
    """Copy source images into data/datasets/corel1000/images and update DB/registry."""

    settings = get_settings()
    image_root = settings.data_root_path / "datasets" / "corel1000" / "images"
    index_root = settings.data_root_path / "datasets" / "corel1000" / "index"
    image_root.mkdir(parents=True, exist_ok=True)
    index_root.mkdir(parents=True, exist_ok=True)

    files = iter_images(src)
    rows: list[dict[str, object]] = []
    counters: dict[str, int] = {}
    for file_path in files:
        category = infer_category(file_path, src)
        counters[category] = counters.get(category, 0) + 1
        target_name = f"{category}_{counters[category]:04d}.jpg"
        target_path = image_root / target_name
        with PillowImage.open(file_path) as image:
            rgb_image = image.convert("RGB")
            rgb_image.save(target_path, format="JPEG", quality=95)
            width, height = rgb_image.size
        rows.append(
            {
                "dataset": "corel1000",
                "name": target_name,
                "path": f"datasets/corel1000/images/{target_name}",
                "category": category,
                "width": width,
                "height": height,
            }
        )

    init_db()
    with SessionLocal() as db:
        crud.delete_dataset_images(db, "corel1000")
        if rows:
            crud.bulk_add(db, rows)

    registry = load_registry()
    registry["corel1000"] = {
        "display_name": "Corel-1000",
        "image_dir": "datasets/corel1000/images",
        "index_dir": "datasets/corel1000/index",
        "count": len(rows),
        "num_classes": len(counters),
    }
    save_registry(registry)
    return len(rows)


def main() -> None:
    """Command-line entry."""

    parser = argparse.ArgumentParser(description="Prepare Corel-1000 dataset")
    parser.add_argument(
        "--src", required=True, type=Path, help="Corel-1000 source directory"
    )
    args = parser.parse_args()
    if not args.src.exists():
        raise FileNotFoundError(f"源目录不存在: {args.src}")
    count = prepare_corel(args.src)
    print(f"prepared {count} images")


if __name__ == "__main__":
    main()
