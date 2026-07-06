"""Search service orchestration."""

from __future__ import annotations

import json
import time
from typing import Protocol

import numpy as np
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
    "deep_cnn",
    "deep_triplet",
    "clip",
    "dinov2",
    "fusion",
}
SUPPORTED_METRICS = {"intersection", "cosine", "euclidean", "weighted"}
FUSION_FEATURES = {
    "color": "color_hist",
    "texture": "glcm",
    "shape": "hu",
    "deep": "deep_triplet",
}
INDEX_STORE = IndexStore()
CALIBRATED_DEEP_FEATURES = {"deep", "deep_cnn", "deep_triplet"}
CIFAR10_PROMPTS = [
    "a photo of an airplane",
    "a photo of an automobile",
    "a photo of a bird",
    "a photo of a cat",
    "a photo of a deer",
    "a photo of a dog",
    "a photo of a frog",
    "a photo of a horse",
    "a photo of a ship",
    "a photo of a truck",
]
OOD_PROMPTS = [
    "a portrait photo of a person",
    "a human face",
    "an ID photo",
    "a document photo",
    "a photo of food",
    "a photo of a building",
    "a photo of a flower",
]
_CLIP_PROMPT_CACHE: dict[str, np.ndarray] = {}


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
    query_info: dict[str, str | int | float | bool | None] = {
        "dataset": dataset,
        "feature": feature,
        "metric": metric,
        "image": image_name,
    }
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
        if file_bytes and dataset == "cifar10" and feature in CALIBRATED_DEEP_FEATURES:
            query_info.update(_calibrate_cifar10_deep_scores(img_bgr, hits))
    elapsed_ms = (time.perf_counter() - start) * 1000
    return SearchResponse(
        query=query_info,
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


def _calibrate_cifar10_deep_scores(img_bgr, hits) -> dict[str, str | float | bool]:
    """Down-weight CIFAR deep scores when CLIP sees an out-of-distribution query."""

    try:
        confidence, top_prompt = _clip_cifar10_membership(img_bgr)
    except Exception as exc:  # noqa: BLE001 - search should still work without calibration
        return {"score_calibrated": False, "calibration_error": str(exc)}
    scale = _cifar10_score_scale(confidence)
    for hit in hits:
        hit.score = float(hit.score) * scale
    return {
        "score_calibrated": True,
        "cifar10_confidence": float(confidence),
        "score_scale": float(scale),
        "clip_gate_top_prompt": top_prompt,
    }


def _clip_cifar10_membership(img_bgr) -> tuple[float, str]:
    """Estimate whether a query image belongs to CIFAR-10 semantic classes."""

    extractor = get_extractor("clip")
    if not hasattr(extractor, "extract_text"):
        raise RuntimeError("clip extractor missing extract_text")
    image_vec = extractor.extract(img_bgr)
    text_matrix = _clip_prompt_matrix(extractor)
    scores = image_vec @ text_matrix.T
    exp_scores = np.exp((scores - scores.max()) * 50.0)
    probs = exp_scores / max(float(exp_scores.sum()), 1e-12)
    cifar_confidence = float(probs[: len(CIFAR10_PROMPTS)].sum())
    prompts = CIFAR10_PROMPTS + OOD_PROMPTS
    return cifar_confidence, prompts[int(np.argmax(probs))]


def _clip_prompt_matrix(extractor) -> np.ndarray:
    cache_key = "cifar10_ood_prompts"
    if cache_key not in _CLIP_PROMPT_CACHE:
        prompts = CIFAR10_PROMPTS + OOD_PROMPTS
        _CLIP_PROMPT_CACHE[cache_key] = np.vstack(
            [extractor.extract_text(prompt) for prompt in prompts]
        ).astype(np.float32)
    return _CLIP_PROMPT_CACHE[cache_key]


def _cifar10_score_scale(confidence: float) -> float:
    """Map CLIP CIFAR membership into a display-score multiplier."""

    return float(np.clip((confidence - 0.10) / 0.60, 0.08, 1.0))
