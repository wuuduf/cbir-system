from __future__ import annotations

import numpy as np

from app.features.base import get_extractor


def test_traditional_extractors_shape_and_repeatability() -> None:
    image = np.zeros((32, 32, 3), dtype=np.uint8)
    image[:, :, 0] = np.arange(32, dtype=np.uint8).reshape(1, 32)
    image[:, :, 1] = 128
    image[:, :, 2] = np.arange(32, dtype=np.uint8).reshape(32, 1)
    expected_dims = {
        "color_hist": 512,
        "color_moments": 9,
        "glcm": 8,
        "lbp": 10,
        "hu": 7,
        "eoh": 36,
    }

    for name, dim in expected_dims.items():
        extractor = get_extractor(name)
        first = extractor.extract(image)
        second = extractor.extract(image)

        assert first.shape == (dim,)
        assert first.dtype == np.float32
        assert not np.isnan(first).any()
        np.testing.assert_allclose(first, second)
