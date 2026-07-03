"""Image management and histogram API routes."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from PIL import Image as PillowImage
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import crud
from app.db.database import get_db
from app.features.base import list_extractors
from app.preprocess import load_image, to_gray
from app.services.search_service import INDEX_STORE
from app.schemas import BuildIndexRequest, BuildIndexResponse, HistogramData, ImageItem
from app.services.dataset_service import image_to_item, load_registry, save_registry
from scripts.build_index import build_index

router = APIRouter(tags=["images"])


@router.post("/api/images", response_model=ImageItem)
async def upload_image(
    dataset: str = Form(...),
    category: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ImageItem:
    """Upload an image into a dataset and rebuild existing feature indexes."""

    registry = load_registry()
    if dataset not in registry:
        raise HTTPException(status_code=404, detail=f"数据集不存在: {dataset}")
    try:
        content = await file.read()
        image = PillowImage.open(BytesIO(content)).convert("RGB")
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="上传文件不是有效图像") from exc

    settings = get_settings()
    image_dir = settings.data_root_path / str(registry[dataset]["image_dir"])
    image_dir.mkdir(parents=True, exist_ok=True)
    label = _safe_name(category or "uploaded")
    next_index = crud.count(db, dataset) + 1
    target_name = _unique_name(image_dir, f"{label}_{next_index:04d}.jpg")
    target_path = image_dir / target_name
    image.save(target_path, format="JPEG", quality=95)

    relative_path = f"{registry[dataset]['image_dir']}/{target_name}"
    item = crud.add_image(
        db,
        dataset=dataset,
        name=target_name,
        path=relative_path,
        category=category,
        width=image.width,
        height=image.height,
    )
    _refresh_registry_counts(db, dataset)
    _rebuild_existing_indexes(dataset)
    return image_to_item(item)


@router.delete("/api/images/{image_id}", status_code=204)
def delete_image(image_id: int, db: Session = Depends(get_db)) -> None:
    """Delete an image from metadata, disk, and existing feature indexes."""

    image = crud.get_image(db, image_id)
    if image is None:
        raise HTTPException(status_code=404, detail=f"图像不存在: {image_id}")
    dataset = image.dataset
    file_path = get_settings().data_root_path / image.path
    crud.delete_image(db, image_id)
    if file_path.exists():
        file_path.unlink()
    _refresh_registry_counts(db, dataset)
    _rebuild_existing_indexes(dataset)


@router.get("/api/histogram", response_model=HistogramData)
def histogram(
    dataset: str = Query(...),
    image_id: int = Query(...),
    type_: str = Query("hsv", alias="type", pattern="^(hsv|gray)$"),
    db: Session = Depends(get_db),
) -> HistogramData:
    """Return HSV hue or gray histogram data for a library image."""

    image = crud.get_image(db, image_id)
    if image is None or image.dataset != dataset:
        raise HTTPException(status_code=404, detail="图像不存在")
    img_bgr = load_image(get_settings().data_root_path / image.path)
    if type_ == "gray":
        gray = to_gray(img_bgr)
        values, edges = np.histogram(gray.ravel(), bins=32, range=(0, 256))
        bins = [str(int(edge)) for edge in edges[:-1]]
    else:
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        values, edges = np.histogram(hsv[:, :, 0].ravel(), bins=36, range=(0, 180))
        bins = [str(int(edge)) for edge in edges[:-1]]
    values = values.astype(np.float32)
    total = float(values.sum())
    if total > 0:
        values /= total
    return HistogramData(bins=bins, values=[float(value) for value in values])


@router.post("/api/index/build", response_model=BuildIndexResponse)
def build_dataset_index(payload: BuildIndexRequest) -> BuildIndexResponse:
    """Build selected feature indexes for a dataset."""

    try:
        meta = build_index(payload.dataset, payload.features)
    except (KeyError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    INDEX_STORE.clear(payload.dataset)
    return BuildIndexResponse(
        dataset=payload.dataset,
        features=payload.features,
        meta=meta,
    )


def _safe_name(value: str) -> str:
    cleaned = "".join(
        char if char.isalnum() or char in {"_", "-"} else "_" for char in value
    )
    return cleaned.strip("_") or "uploaded"


def _unique_name(image_dir: Path, candidate: str) -> str:
    stem = Path(candidate).stem
    suffix = Path(candidate).suffix
    name = candidate
    index = 1
    while (image_dir / name).exists():
        name = f"{stem}_{index}{suffix}"
        index += 1
    return name


def _refresh_registry_counts(db: Session, dataset: str) -> None:
    registry = load_registry()
    if dataset not in registry:
        return
    registry[dataset]["count"] = crud.count(db, dataset)
    registry[dataset]["num_classes"] = len(crud.categories(db, dataset))
    save_registry(registry)


def _rebuild_existing_indexes(dataset: str) -> None:
    registry = load_registry()
    if dataset not in registry:
        return
    index_dir = get_settings().data_root_path / str(registry[dataset]["index_dir"])
    existing = [
        feature
        for feature in list_extractors()
        if (index_dir / f"{feature}.npy").exists()
        and (index_dir / f"{feature}_ids.npy").exists()
    ]
    if existing:
        build_index(dataset, existing)
        INDEX_STORE.clear(dataset)
