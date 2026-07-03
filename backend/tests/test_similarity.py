from __future__ import annotations

import numpy as np

from app.similarity import histogram_intersection


def test_histogram_intersection_self_is_highest() -> None:
    q = np.array([0.2, 0.3, 0.5], dtype=np.float32)
    matrix = np.array([[0.2, 0.3, 0.5], [0.5, 0.2, 0.3]], dtype=np.float32)

    scores = histogram_intersection(q, matrix)

    assert 0 <= scores.min() <= scores.max() <= 1
    assert scores[0] == scores.max()
