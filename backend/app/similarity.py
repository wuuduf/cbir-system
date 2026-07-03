"""Vectorized similarity and distance functions."""

from __future__ import annotations

import numpy as np


def euclidean(q: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return Euclidean distance from q to each row in matrix."""

    diff = matrix - q.reshape(1, -1)
    return np.linalg.norm(diff, axis=1)


def cosine_sim(q: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return cosine similarity from q to each row in matrix."""

    q_norm = np.linalg.norm(q)
    m_norm = np.linalg.norm(matrix, axis=1)
    denom = np.maximum(q_norm * m_norm, 1e-12)
    return (matrix @ q) / denom


def histogram_intersection(q: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return histogram intersection similarity in [0, 1] for L1 histograms."""

    q_sum = max(float(q.sum()), 1e-12)
    return np.minimum(matrix, q.reshape(1, -1)).sum(axis=1) / q_sum


def weighted_euclidean(
    q: np.ndarray, matrix: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    """Return weighted Euclidean distance from q to each row in matrix."""

    diff = (matrix - q.reshape(1, -1)) * weights.reshape(1, -1)
    return np.linalg.norm(diff, axis=1)


def to_similarity(dist: np.ndarray) -> np.ndarray:
    """Convert distances to similarities; larger means more similar."""

    return 1.0 / (1.0 + dist)
