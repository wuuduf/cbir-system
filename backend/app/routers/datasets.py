"""Dataset API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import crud
from app.db.database import get_db
from app.schemas import DatasetInfo, ImageListResponse
from app.services import dataset_service

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetInfo])
def list_datasets(db: Session = Depends(get_db)) -> list[DatasetInfo]:
    """List registered datasets."""

    return dataset_service.list_datasets(db)


@router.get("/{dataset}/images", response_model=ImageListResponse)
def list_images(
    dataset: str,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=24, ge=1, le=100),
    category: str | None = None,
    db: Session = Depends(get_db),
) -> ImageListResponse:
    """List images in a dataset."""

    items, total = dataset_service.list_dataset_images(
        db, dataset, page, size, category
    )
    return ImageListResponse(items=items, total=total)


@router.get("/{dataset}/categories", response_model=list[str])
def categories(dataset: str, db: Session = Depends(get_db)) -> list[str]:
    """List categories in a dataset."""

    return crud.categories(db, dataset)
