"""Dataset service functions."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.models import Image
from app.schemas import DatasetInfo, ImageItem
from app.services.url_service import static_url


def load_registry() -> dict[str, dict[str, object]]:
    """Load dataset registry JSON."""

    path = get_settings().registry_path
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        return dict(json.load(file))


def save_registry(registry: dict[str, dict[str, object]]) -> None:
    """Save dataset registry JSON."""

    path = get_settings().registry_path
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(registry, file, ensure_ascii=False, indent=2)


def list_datasets(db: Session) -> list[DatasetInfo]:
    """Return all registered datasets with live DB counts."""

    items: list[DatasetInfo] = []
    for key, value in load_registry().items():
        data = dict(value)
        data["count"] = crud.count(db, key)
        items.append(DatasetInfo(key=key, **data))
    return items


def image_to_item(image: Image) -> ImageItem:
    """Convert an Image ORM row to API schema."""

    return ImageItem(
        id=image.id,
        dataset=image.dataset,
        name=image.name,
        path=image.path,
        url=static_url(image.path),
        category=image.category,
        width=image.width,
        height=image.height,
    )


def list_dataset_images(
    db: Session,
    dataset: str,
    page: int,
    size: int,
    category: str | None,
) -> tuple[list[ImageItem], int]:
    """List dataset images for API responses."""

    images, total = crud.list_images(db, dataset, page, size, category)
    return [image_to_item(image) for image in images], total
