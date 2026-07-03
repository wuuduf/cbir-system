from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np

from scripts.prepare_cifar import _batch_samples, _load_class_names


def _write_pickle(path: Path, payload: dict[bytes, object]) -> None:
    with path.open("wb") as file:
        pickle.dump(payload, file)


def test_prepare_cifar_reads_official_batch_shape(tmp_path) -> None:
    src = tmp_path / "cifar-10-batches-py"
    src.mkdir()
    class_names = [f"class_{index}".encode("utf-8") for index in range(10)]
    _write_pickle(src / "batches.meta", {b"label_names": class_names})

    flat = np.arange(3 * 32 * 32, dtype=np.uint8)
    _write_pickle(src / "test_batch", {b"data": np.vstack([flat]), b"labels": [3]})

    names = _load_class_names(src)
    samples = _batch_samples(src, "test")

    assert names[3] == "class_3"
    assert len(samples) == 1
    image, label = samples[0]
    assert image.shape == (32, 32, 3)
    assert label == 3
