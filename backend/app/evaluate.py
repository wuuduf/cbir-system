"""Evaluation metrics for CBIR retrieval quality."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np

from app.retrieval import IndexStore, Retriever


@dataclass(frozen=True)
class EvalResult:
    """Evaluation result returned by the algorithm layer."""

    map: float
    p_at_k: float
    pr_curve: list[tuple[float, float]]
    query_count: int


def precision_at_k(
    ranked_labels: list[str | None], query_label: str | None, k: int
) -> float:
    """Calculate Precision@K for one ranked label list."""

    if query_label is None or k <= 0:
        return 0.0
    top_labels = ranked_labels[:k]
    if not top_labels:
        return 0.0
    relevant = sum(1 for label in top_labels if label == query_label)
    return relevant / min(k, len(top_labels))


def average_precision(
    ranked_labels: list[str | None], query_label: str | None
) -> float:
    """Calculate average precision for one query."""

    if query_label is None:
        return 0.0
    hit_count = 0
    precision_sum = 0.0
    for rank, label in enumerate(ranked_labels, start=1):
        if label == query_label:
            # 每遇到一个相关样本，记录当前截断位置的准确率。
            hit_count += 1
            precision_sum += hit_count / rank
    if hit_count == 0:
        return 0.0
    return precision_sum / hit_count


def evaluate_feature(
    dataset: str,
    feature: str,
    metric: str,
    *,
    k: int = 12,
    sample: int | None = None,
    store: IndexStore | None = None,
    labels_by_id: dict[int, str | None] | None = None,
) -> EvalResult:
    """Evaluate one feature with leave-one-out retrieval over indexed vectors."""

    index_store = store or IndexStore()
    matrix, ids = index_store.get_matrix(dataset, feature)
    if labels_by_id is None:
        raise ValueError("评估需要 image_id 到类别标签的映射")
    labels = [labels_by_id.get(int(image_id)) for image_id in ids]
    query_positions = _select_query_positions(labels, sample)
    if not query_positions:
        return EvalResult(map=0.0, p_at_k=0.0, pr_curve=[], query_count=0)

    retriever = Retriever(store=index_store)
    ap_values: list[float] = []
    p_at_k_values: list[float] = []
    pr_samples: list[list[tuple[float, float]]] = []

    for query_pos in query_positions:
        query_label = labels[query_pos]
        if query_label is None or labels.count(query_label) <= 1:
            continue
        # 留一法：查询图来自图库本身，评分后必须排除自身，避免虚高。
        scores = _score_query(
            retriever, dataset, feature, matrix[query_pos], matrix, metric
        )
        scores[query_pos] = -np.inf
        ranked_positions = np.argsort(-scores)
        ranked_labels = [
            labels[position] for position in ranked_positions if position != query_pos
        ]
        relevant_total = max(labels.count(query_label) - 1, 0)
        if relevant_total <= 0:
            continue
        ap_values.append(average_precision(ranked_labels, query_label))
        p_at_k_values.append(precision_at_k(ranked_labels, query_label, k))
        pr_samples.append(
            _precision_recall_points(ranked_labels, query_label, relevant_total)
        )

    if not ap_values:
        return EvalResult(map=0.0, p_at_k=0.0, pr_curve=[], query_count=0)
    return EvalResult(
        map=float(np.mean(ap_values)),
        p_at_k=float(np.mean(p_at_k_values)),
        pr_curve=_average_pr_curve(pr_samples),
        query_count=len(ap_values),
    )


def _score_query(
    retriever: Retriever,
    dataset: str,
    feature: str,
    query_vec: np.ndarray,
    matrix: np.ndarray,
    metric: str,
) -> np.ndarray:
    """Score one indexed query against the whole matrix."""

    effective_metric = retriever._effective_metric(feature, metric)
    # 评估直接使用建库后的矩阵行作为查询向量，因此无需再次做标准化。
    return retriever._score(
        query_vec.astype(np.float32), matrix, effective_metric
    ).astype(np.float32)


def _select_query_positions(labels: list[str | None], sample: int | None) -> list[int]:
    """Select deterministic, class-balanced query positions."""

    valid_positions = [index for index, label in enumerate(labels) if label is not None]
    if sample is None or sample <= 0 or sample >= len(valid_positions):
        return valid_positions

    grouped: dict[str, list[int]] = {}
    for position in valid_positions:
        label = labels[position]
        if label is None:
            continue
        grouped.setdefault(label, []).append(position)
    per_class = max(1, int(np.ceil(sample / max(len(grouped), 1))))
    selected: list[int] = []
    # 按类别均匀抽取，保证 CIFAR-10 这类均衡数据集的报告结果更稳定。
    for label in sorted(grouped):
        selected.extend(grouped[label][:per_class])
    return selected[:sample]


def _precision_recall_points(
    ranked_labels: list[str | None],
    query_label: str | None,
    relevant_total: int,
) -> list[tuple[float, float]]:
    """Build the precision-recall curve for one query."""

    if query_label is None or relevant_total <= 0:
        return []
    points: list[tuple[float, float]] = []
    hit_count = 0
    for rank, label in enumerate(ranked_labels, start=1):
        if label != query_label:
            continue
        hit_count += 1
        recall = hit_count / relevant_total
        precision = hit_count / rank
        points.append((recall, precision))
        if hit_count >= relevant_total:
            break
    return points


def _average_pr_curve(
    samples: list[list[tuple[float, float]]],
) -> list[tuple[float, float]]:
    """Average query PR curves on fixed recall levels."""

    levels = np.linspace(0.0, 1.0, 11)
    averaged: list[tuple[float, float]] = []
    for level in levels:
        precisions: list[float] = []
        for points in samples:
            if not points:
                continue
            # 取达到该召回率后的最高精度，形成平滑、可报告的插值 PR 曲线。
            candidates = [precision for recall, precision in points if recall >= level]
            precisions.append(max(candidates) if candidates else 0.0)
        averaged.append(
            (float(level), float(np.mean(precisions)) if precisions else 0.0)
        )
    return averaged


def label_distribution(labels_by_id: dict[int, str | None]) -> dict[str, int]:
    """Return label counts for report summaries."""

    return dict(Counter(label for label in labels_by_id.values() if label))
