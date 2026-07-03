from __future__ import annotations

import json

import numpy as np

from app.retrieval import IndexStore, Retriever


def test_retrieval_returns_self_first(tmp_path) -> None:
    data_root = tmp_path / "data"
    index_dir = data_root / "datasets" / "mini" / "index"
    index_dir.mkdir(parents=True)
    registry_path = data_root / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "mini": {
                    "display_name": "Mini",
                    "image_dir": "datasets/mini/images",
                    "index_dir": "datasets/mini/index",
                    "count": 2,
                    "num_classes": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    matrix = np.array([[0.8, 0.2], [0.1, 0.9]], dtype=np.float32)
    ids = np.array([101, 102], dtype=np.int64)
    np.save(index_dir / "color_hist.npy", matrix)
    np.save(index_dir / "color_hist_ids.npy", ids)

    store = IndexStore(data_root=data_root, registry_path=registry_path)
    retriever = Retriever(store=store)
    hits = retriever.search_single("mini", "color_hist", matrix[0], "intersection", 1)

    assert hits[0].image_id == 101


def test_deep_non_cosine_metric_uses_matrix_scoring(tmp_path) -> None:
    data_root = tmp_path / "data"
    index_dir = data_root / "datasets" / "mini" / "index"
    index_dir.mkdir(parents=True)
    registry_path = data_root / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "mini": {
                    "display_name": "Mini",
                    "image_dir": "datasets/mini/images",
                    "index_dir": "datasets/mini/index",
                    "count": 2,
                    "num_classes": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    matrix = np.array([[0.9, 0.1], [0.1, 0.9]], dtype=np.float32)
    ids = np.array([101, 102], dtype=np.int64)
    np.save(index_dir / "deep.npy", matrix)
    np.save(index_dir / "deep_ids.npy", ids)

    store = IndexStore(data_root=data_root, registry_path=registry_path)
    retriever = Retriever(store=store)
    hits = retriever.search_single("mini", "deep", matrix[0], "intersection", 1)

    assert hits[0].image_id == 101
