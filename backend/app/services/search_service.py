"""Search service orchestration."""

from __future__ import annotations

import json
import time
from typing import Protocol

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.crud import get_image
from app.features.base import get_extractor
from app.preprocess import decode_image_bytes, load_image
from app.retrieval import IndexStore, Retriever
from app.schemas import SearchResponse
from app.services.text_translation import rewrite_clip_query

SUPPORTED_FEATURES = {
    "color_hist",
    "color_moments",
    "glcm",
    "lbp",
    "hu",
    "eoh",
    "deep",
    "clip",
    "fusion",
}
SUPPORTED_METRICS = {"intersection", "cosine", "euclidean", "weighted"}
FUSION_FEATURES = {
    "color": "color_hist",
    "texture": "glcm",
    "shape": "hu",
    "deep": "deep",
}
INDEX_STORE = IndexStore()


class TextFeatureExtractor(Protocol):
    """Protocol for text-capable multimodal feature extractors."""

    def extract_text(self, text: str):
        """Extract a text embedding."""


def search_uploaded(
    db: Session,
    *,
    dataset: str,
    feature: str,
    metric: str,
    top_k: int | None,
    file_bytes: bytes | None,
    image_id: int | None,
    weights_json: str | None = None,
) -> SearchResponse:
    """Run single-feature search for an uploaded or library image."""

    if feature not in SUPPORTED_FEATURES:
        raise ValueError(f"不支持特征: {feature}")
    if metric not in SUPPORTED_METRICS:
        raise ValueError(f"不支持度量: {metric}")
    start = time.perf_counter()
    image_name: str | None = None
    if image_id is not None:
        image = get_image(db, image_id)
        if image is None:
            raise FileNotFoundError(f"图像不存在: {image_id}")
        img_bgr = load_image(get_settings().data_root_path / image.path)
        image_name = image.name
    elif file_bytes:
        img_bgr = decode_image_bytes(file_bytes)
        image_name = "uploaded"
    else:
        raise ValueError("必须上传图片或提供 image_id")

    retriever = Retriever(store=INDEX_STORE, db=db)
    limit = top_k or get_settings().app.top_k
    if feature == "fusion":
        weights = _parse_weights(weights_json)
        query_vectors = {
            feature_name: get_extractor(feature_name).extract(img_bgr)
            for feature_name in weights
            if weights[feature_name] > 0
        }
        hits = retriever.search_fusion(dataset, query_vectors, weights, metric, limit)
    else:
        extractor = get_extractor(feature)
        query_vec = extractor.extract(img_bgr)
        hits = retriever.search_single(dataset, feature, query_vec, metric, limit)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return SearchResponse(
        query={
            "dataset": dataset,
            "feature": feature,
            "metric": metric,
            "image": image_name,
        },
        hits=hits,
        elapsed_ms=elapsed_ms,
    )


def search_text(
    db: Session,
    *,
    dataset: str,
    text: str,
    top_k: int | None,
) -> SearchResponse:
    """Run CLIP text-to-image retrieval."""

    query_text = text.strip()
    if not query_text:
        raise ValueError("文本检索内容不能为空")
    clip_text, translated = rewrite_clip_query(query_text)
    start = time.perf_counter()
    extractor = get_extractor("clip")
    if not hasattr(extractor, "extract_text"):
        raise RuntimeError("clip extractor 缺少 extract_text")
    query_vec = extractor.extract_text(clip_text)  # type: ignore[attr-defined]
    retriever = Retriever(store=INDEX_STORE, db=db)
    limit = top_k or get_settings().app.top_k
    hits = retriever.search_single(dataset, "clip", query_vec, "cosine", limit)
    elapsed_ms = (time.perf_counter() - start) * 1000
    return SearchResponse(
        query={
            "dataset": dataset,
            "feature": "clip",
            "metric": "cosine",
            "text": query_text,
            "clip_text": clip_text,
            "translated": translated,
        },
        hits=hits,
        elapsed_ms=elapsed_ms,
    )


def _parse_weights(weights_json: str | None) -> dict[str, float]:
    """Parse group or feature weights into concrete feature weights."""

    if not weights_json:
        raw_weights = {"color": 0.25, "texture": 0.25, "shape": 0.25, "deep": 0.25}
    else:
        try:
            raw_weights = json.loads(weights_json)
        except json.JSONDecodeError as exc:
            raise ValueError("weights 不是合法 JSON") from exc
    if not isinstance(raw_weights, dict):
        raise ValueError("weights 必须是对象")
    weights: dict[str, float] = {}
    for key, value in raw_weights.items():
        feature = FUSION_FEATURES.get(str(key), str(key))
        if feature not in FUSION_FEATURES.values():
            continue
        weights[feature] = max(float(value), 0.0)
    if not weights or sum(weights.values()) <= 0:
        raise ValueError("融合权重至少需要一个大于 0")
    return weights
