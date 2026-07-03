"""Evaluation service orchestration."""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.db import crud
from app.evaluate import evaluate_feature
from app.retrieval import IndexStore
from app.schemas import EvalResponse

SUPPORTED_EVAL_FEATURES = {
    "color_hist",
    "color_moments",
    "glcm",
    "lbp",
    "hu",
    "eoh",
    "deep",
    "clip",
}
SUPPORTED_EVAL_METRICS = {"intersection", "cosine", "euclidean", "weighted"}


def evaluate_dataset_feature(
    db: Session,
    *,
    dataset: str,
    feature: str,
    metric: str,
    k: int,
    sample: int | None,
) -> EvalResponse:
    """Evaluate a dataset feature and return API-ready metrics."""

    if feature not in SUPPORTED_EVAL_FEATURES:
        raise ValueError(f"不支持评估特征: {feature}")
    if metric not in SUPPORTED_EVAL_METRICS:
        raise ValueError(f"不支持度量: {metric}")
    images, total = crud.list_images(db, dataset, page=1, size=100000)
    if total == 0:
        raise FileNotFoundError(f"数据集没有图像: {dataset}")
    labels_by_id = {int(image.id): image.category for image in images}
    started = time.perf_counter()
    result = evaluate_feature(
        dataset,
        feature,
        metric,
        k=k,
        sample=sample,
        store=IndexStore(),
        labels_by_id=labels_by_id,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return EvalResponse(
        map=result.map,
        p_at_k=result.p_at_k,
        pr_curve=result.pr_curve,
        query_count=result.query_count,
        feature=feature,
        metric=metric,
        k=k,
        elapsed_ms=elapsed_ms,
    )
