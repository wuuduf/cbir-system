"""Evaluation API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas import EvalResponse
from app.services.eval_service import evaluate_dataset_feature

router = APIRouter(prefix="/api/evaluate", tags=["evaluate"])


@router.get("", response_model=EvalResponse)
def evaluate(
    dataset: str = Query(...),
    feature: str = Query("deep"),
    metric: str = Query("cosine"),
    k: int = Query(12, ge=1, le=100),
    sample: int | None = Query(100, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> EvalResponse:
    """Evaluate one feature on one dataset."""

    try:
        return evaluate_dataset_feature(
            db,
            dataset=dataset,
            feature=feature,
            metric=metric,
            k=k,
            sample=sample,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
