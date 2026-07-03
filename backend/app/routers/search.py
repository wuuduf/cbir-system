"""Search API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import SearchResponse
from app.services.search_service import search_text, search_uploaded

router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(
    dataset: str = Form(...),
    feature: str = Form("color_hist"),
    metric: str = Form("intersection"),
    top_k: int = Form(12),
    weights: str | None = Form(None),
    image_id: int | None = Form(None),
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search the dataset with an uploaded image or image_id."""

    file_bytes = await file.read() if file is not None else None
    try:
        return search_uploaded(
            db,
            dataset=dataset,
            feature=feature,
            metric=metric,
            top_k=top_k,
            file_bytes=file_bytes,
            image_id=image_id,
            weights_json=weights,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/text", response_model=SearchResponse)
async def text_search(
    dataset: str = Form(...),
    text: str = Form(...),
    top_k: int = Form(12),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search images by natural language text with CLIP."""

    try:
        return search_text(db, dataset=dataset, text=text, top_k=top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
