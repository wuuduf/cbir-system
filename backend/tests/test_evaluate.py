from __future__ import annotations

import json

import numpy as np

from app.evaluate import average_precision, evaluate_feature, precision_at_k
from app.retrieval import IndexStore


def test_precision_and_average_precision() -> None:
    ranked = ["cat", "dog", "cat", "cat"]

    assert precision_at_k(ranked, "cat", 2) == 0.5
    assert round(average_precision(ranked, "cat"), 6) == round(
        (1 / 1 + 2 / 3 + 3 / 4) / 3, 6
    )


def test_evaluate_feature_on_toy_index(tmp_path) -> None:
    data_root = tmp_path / "data"
    index_dir = data_root / "datasets" / "toy" / "index"
    index_dir.mkdir(parents=True)
    registry_path = data_root / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "toy": {
                    "display_name": "Toy",
                    "image_dir": "datasets/toy/images",
                    "index_dir": "datasets/toy/index",
                    "count": 4,
                    "num_classes": 2,
                }
            }
        ),
        encoding="utf-8",
    )
    matrix = np.array(
        [
            [1.0, 0.0],
            [0.9, 0.1],
            [0.0, 1.0],
            [0.1, 0.9],
        ],
        dtype=np.float32,
    )
    ids = np.array([1, 2, 3, 4], dtype=np.int64)
    np.save(index_dir / "color_hist.npy", matrix)
    np.save(index_dir / "color_hist_ids.npy", ids)

    result = evaluate_feature(
        "toy",
        "color_hist",
        "cosine",
        k=1,
        store=IndexStore(data_root=data_root, registry_path=registry_path),
        labels_by_id={1: "a", 2: "a", 3: "b", 4: "b"},
    )

    assert result.query_count == 4
    assert result.p_at_k == 1.0
    assert result.map == 1.0
    assert result.pr_curve[-1] == (1.0, 1.0)
