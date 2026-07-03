"""Index loading and retrieval logic."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.crud import get_image
from app.schemas import Hit
from app.services.url_service import static_url
from app.similarity import (
    cosine_sim,
    euclidean,
    histogram_intersection,
    to_similarity,
    weighted_euclidean,
)


class IndexStore:
    """按 (dataset, feature) 懒加载 .npy 索引到内存并缓存。"""

    def __init__(
        self, data_root: Path | None = None, registry_path: Path | None = None
    ) -> None:
        settings = get_settings()
        self.data_root = data_root or settings.data_root_path
        self.registry_path = registry_path or settings.registry_path
        self._matrix_cache: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
        self._faiss_cache: dict[tuple[str, str], object] = {}
        self._meta_cache: dict[str, dict[str, object]] = {}

    def _load_registry(self) -> dict[str, dict[str, object]]:
        if not self.registry_path.exists():
            return {}
        with self.registry_path.open("r", encoding="utf-8") as file:
            return dict(json.load(file))

    def index_dir(self, dataset: str) -> Path:
        """Return absolute index directory for a dataset."""

        registry = self._load_registry()
        if dataset not in registry:
            raise KeyError(f"数据集不存在: {dataset}")
        return self.data_root / str(registry[dataset]["index_dir"])

    def get_matrix(self, dataset: str, feature: str) -> tuple[np.ndarray, np.ndarray]:
        """Return feature matrix and aligned image ids."""

        cache_key = (dataset, feature)
        if cache_key in self._matrix_cache:
            return self._matrix_cache[cache_key]
        index_dir = self.index_dir(dataset)
        matrix_path = index_dir / f"{feature}.npy"
        ids_path = index_dir / f"{feature}_ids.npy"
        if not matrix_path.exists() or not ids_path.exists():
            raise FileNotFoundError(f"索引不存在，请先建库: {matrix_path}")
        matrix = np.load(matrix_path).astype(np.float32)
        ids = np.load(ids_path).astype(np.int64)
        self._matrix_cache[cache_key] = (matrix, ids)
        return matrix, ids

    def get_faiss(self, dataset: str, feature: str):
        """Return a cached FAISS index."""

        cache_key = (dataset, feature)
        if cache_key in self._faiss_cache:
            return self._faiss_cache[cache_key]
        import faiss

        index_path = self.index_dir(dataset) / f"{feature}.faiss"
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS 索引不存在，请先建库: {index_path}")
        index = faiss.read_index(str(index_path))
        self._faiss_cache[cache_key] = index
        return index

    def clear(self, dataset: str | None = None) -> None:
        """Clear cached matrices and metadata after indexes are rebuilt."""

        if dataset is None:
            self._matrix_cache.clear()
            self._faiss_cache.clear()
            self._meta_cache.clear()
            return
        self._matrix_cache = {
            key: value for key, value in self._matrix_cache.items() if key[0] != dataset
        }
        self._faiss_cache = {
            key: value for key, value in self._faiss_cache.items() if key[0] != dataset
        }
        self._meta_cache.pop(dataset, None)

    def get_meta(self, dataset: str) -> dict[str, object]:
        """Return index metadata for a dataset."""

        if dataset in self._meta_cache:
            return self._meta_cache[dataset]
        meta_path = self.index_dir(dataset) / "meta.json"
        if not meta_path.exists():
            return {}
        with meta_path.open("r", encoding="utf-8") as file:
            meta = dict(json.load(file))
        self._meta_cache[dataset] = meta
        return meta


class Retriever:
    """Single-feature image retriever."""

    def __init__(
        self, store: IndexStore | None = None, db: Session | None = None
    ) -> None:
        self.store = store or IndexStore()
        self.db = db

    def search_single(
        self,
        dataset: str,
        feature: str,
        query_vec: np.ndarray,
        metric: str = "intersection",
        top_k: int = 12,
    ) -> list[Hit]:
        """Search one feature matrix and return ranked hits."""

        matrix, ids = self.store.get_matrix(dataset, feature)
        transformed_query = self._transform_query(
            dataset, feature, query_vec.astype(np.float32)
        )
        effective_metric = self._effective_metric(feature, metric)
        if feature in {"deep", "clip"} and effective_metric == "cosine":
            return self._search_faiss(dataset, feature, transformed_query, top_k)
        scores = self._score(transformed_query, matrix, effective_metric)
        order = np.argsort(-scores)[:top_k]
        return [self._to_hit(int(ids[index]), float(scores[index])) for index in order]

    def search_fusion(
        self,
        dataset: str,
        query_vectors: dict[str, np.ndarray],
        weights: dict[str, float],
        metric: str = "cosine",
        top_k: int = 12,
    ) -> list[Hit]:
        """Fuse normalized similarities from multiple features."""

        fused_scores: np.ndarray | None = None
        fused_ids: np.ndarray | None = None
        weight_sum = 0.0
        for feature, weight in weights.items():
            if weight <= 0 or feature not in query_vectors:
                continue
            # 某个特征索引缺失（例如未训练深度模型）时跳过该特征，只用剩余特征融合，
            # 避免因单个特征未建库导致整个综合检索失败，提升演示稳定性。
            try:
                matrix, ids = self.store.get_matrix(dataset, feature)
            except FileNotFoundError:
                continue
            query_vec = self._transform_query(
                dataset, feature, query_vectors[feature].astype(np.float32)
            )
            effective_metric = self._effective_metric(feature, metric)
            scores = self._score(query_vec, matrix, effective_metric)
            normalized = self._minmax(scores)
            if fused_scores is None:
                fused_scores = np.zeros_like(normalized, dtype=np.float32)
                fused_ids = ids
            if fused_ids is None or not np.array_equal(fused_ids, ids):
                raise RuntimeError("融合特征索引的 image_id 顺序不一致，请重建索引")
            fused_scores += normalized.astype(np.float32) * float(weight)
            weight_sum += float(weight)
        if fused_scores is None or fused_ids is None or weight_sum <= 0:
            raise ValueError("融合检索没有可用特征，请先为所选特征建立索引，或调整权重")
        fused_scores /= weight_sum
        order = np.argsort(-fused_scores)[:top_k]
        return [
            self._to_hit(int(fused_ids[index]), float(fused_scores[index]))
            for index in order
        ]

    def _search_faiss(
        self, dataset: str, feature: str, query_vec: np.ndarray, top_k: int
    ) -> list[Hit]:
        """Search L2-normalized vectors with FAISS inner product."""

        _matrix, ids = self.store.get_matrix(dataset, feature)
        index = self.store.get_faiss(dataset, feature)
        query = query_vec.reshape(1, -1).astype(np.float32)
        scores, positions = index.search(query, top_k)
        return [
            self._to_hit(int(ids[position]), float(score))
            for score, position in zip(scores[0], positions[0])
            if position >= 0
        ]

    def _effective_metric(self, feature: str, metric: str) -> str:
        """Use histogram intersection only for non-negative histogram features."""

        if metric == "intersection" and feature not in {
            "color_hist",
            "lbp",
            "eoh",
            "deep",
            "clip",
        }:
            return "cosine"
        return metric

    def _transform_query(
        self, dataset: str, feature: str, query_vec: np.ndarray
    ) -> np.ndarray:
        """Apply index-time normalization to a query vector when needed."""

        feature_meta = self.store.get_meta(dataset).get(feature, {})
        if not isinstance(feature_meta, dict):
            return query_vec
        standardization = feature_meta.get("standardization")
        if not isinstance(standardization, dict):
            return query_vec
        mean = np.asarray(standardization["mean"], dtype=np.float32)
        std = np.asarray(standardization["std"], dtype=np.float32)
        return ((query_vec - mean) / np.maximum(std, 1e-6)).astype(np.float32)

    def _score(
        self, query_vec: np.ndarray, matrix: np.ndarray, metric: str
    ) -> np.ndarray:
        if metric == "intersection":
            return histogram_intersection(query_vec, matrix)
        if metric == "cosine":
            return cosine_sim(query_vec, matrix)
        if metric == "euclidean":
            return to_similarity(euclidean(query_vec, matrix))
        if metric == "weighted":
            weights = self._weights(matrix)
            return to_similarity(weighted_euclidean(query_vec, matrix, weights))
        raise ValueError(f"不支持度量: {metric}")

    def _weights(self, matrix: np.ndarray) -> np.ndarray:
        """Build stable per-dimension weights from the indexed feature spread."""

        weights = 1.0 / np.maximum(matrix.std(axis=0), 1e-6)
        mean_weight = max(float(weights.mean()), 1e-6)
        weights = weights / mean_weight
        return np.clip(weights, 0.1, 10.0).astype(np.float32)

    def _minmax(self, scores: np.ndarray) -> np.ndarray:
        """Normalize score vector to [0, 1]."""

        min_value = float(np.min(scores))
        max_value = float(np.max(scores))
        if max_value - min_value < 1e-12:
            return np.ones_like(scores, dtype=np.float32)
        return ((scores - min_value) / (max_value - min_value)).astype(np.float32)

    def _to_hit(self, image_id: int, score: float) -> Hit:
        if self.db is None:
            return Hit(image_id=image_id, name=str(image_id), path="", score=score)
        image = get_image(self.db, image_id)
        if image is None:
            return Hit(image_id=image_id, name=str(image_id), path="", score=score)
        return Hit(
            image_id=image.id,
            name=image.name,
            path=image.path,
            url=static_url(image.path),
            score=score,
            category=image.category,
            width=image.width,
            height=image.height,
        )
