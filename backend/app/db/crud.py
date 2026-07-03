"""CRUD functions for image metadata."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.db.models import Image


def add_image(
    db: Session,
    *,
    dataset: str,
    name: str,
    path: str,
    category: str | None,
    width: int,
    height: int,
) -> Image:
    """Add a single image metadata row."""

    image = Image(
        dataset=dataset,
        name=name,
        path=path,
        category=category,
        width=width,
        height=height,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def bulk_add(db: Session, images: Sequence[dict[str, object]]) -> list[Image]:
    """Add many image metadata rows."""

    rows = [Image(**image) for image in images]
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return rows


def delete_image(db: Session, image_id: int) -> bool:
    """Delete one image row by id."""

    image = get_image(db, image_id)
    if image is None:
        return False
    db.delete(image)
    db.commit()
    return True


def delete_dataset_images(db: Session, dataset: str) -> None:
    """Delete all image rows for a dataset."""

    db.execute(delete(Image).where(Image.dataset == dataset))
    db.commit()


def list_images(
    db: Session,
    dataset: str,
    page: int = 1,
    size: int = 24,
    category: str | None = None,
) -> tuple[list[Image], int]:
    """List images with pagination and optional category filtering."""

    filters = [Image.dataset == dataset]
    if category:
        filters.append(Image.category == category)

    total = db.scalar(select(func.count()).select_from(Image).where(*filters)) or 0
    stmt = (
        select(Image)
        .where(*filters)
        .order_by(Image.id.asc())
        .offset(max(page - 1, 0) * size)
        .limit(size)
    )
    return list(db.scalars(stmt)), int(total)


def get_image(db: Session, image_id: int) -> Image | None:
    """Return one image by id."""

    return db.get(Image, image_id)


def get_image_by_name(db: Session, dataset: str, name: str) -> Image | None:
    """Return one image by dataset and name."""

    stmt = select(Image).where(Image.dataset == dataset, Image.name == name)
    return db.scalar(stmt)


def count(db: Session, dataset: str) -> int:
    """Count images in a dataset."""

    return int(
        db.scalar(
            select(func.count()).select_from(Image).where(Image.dataset == dataset)
        )
        or 0
    )


def categories(db: Session, dataset: str) -> list[str]:
    """Return sorted non-empty category names for a dataset."""

    stmt = (
        select(Image.category)
        .where(Image.dataset == dataset, Image.category.is_not(None))
        .distinct()
    )
    return sorted(category for category in db.scalars(stmt) if category)
