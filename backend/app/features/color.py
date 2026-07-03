"""Color feature extractors."""

from __future__ import annotations

import cv2
import numpy as np

from app.core.config import get_settings
from app.features.base import FeatureExtractor
from app.preprocess import preprocess


class HSVHistogram(FeatureExtractor):
    """HSV joint histogram feature with L1 normalization."""

    name = "color_hist"

    def __init__(
        self,
        h_bins: int | None = None,
        s_bins: int | None = None,
        v_bins: int | None = None,
    ) -> None:
        cfg = get_settings().features.color_hist
        self.h_bins = h_bins or int(cfg["h_bins"])
        self.s_bins = s_bins or int(cfg["s_bins"])
        self.v_bins = v_bins or int(cfg["v_bins"])
        self.dim = self.h_bins * self.s_bins * self.v_bins

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract a 512D HSV histogram by default."""

        prepared = preprocess(img_bgr, get_settings().preprocess)
        hsv = cv2.cvtColor(prepared, cv2.COLOR_BGR2HSV)
        # H/S/V 三通道联合统计，bins 数来自配置，用于描述整体颜色分布。
        hist = cv2.calcHist(
            [hsv],
            [0, 1, 2],
            None,
            [self.h_bins, self.s_bins, self.v_bins],
            [0, 180, 0, 256, 0, 256],
        ).flatten()
        total = float(hist.sum())
        # L1 归一化让不同尺寸图像的直方图可比较，直方图相交值落在稳定范围。
        if total > 0:
            hist = hist / total
        return hist.astype(np.float32)


class ColorMoments(FeatureExtractor):
    """HSV color moment feature."""

    name = "color_moments"
    dim = 9

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract mean, standard deviation and cubic-root skewness for H/S/V."""

        prepared = preprocess(img_bgr, get_settings().preprocess)
        hsv = cv2.cvtColor(prepared, cv2.COLOR_BGR2HSV).astype(np.float32)
        features: list[float] = []
        for channel_index in range(3):
            channel = hsv[:, :, channel_index].reshape(-1)
            # 一阶矩: E[x]，描述该 HSV 通道的平均颜色水平。
            mean = float(np.mean(channel))
            centered = channel - mean
            # 二阶中心矩开方: sqrt(E[(x-mean)^2])，即标准差，描述颜色分散程度。
            std = float(np.sqrt(np.mean(centered**2)))
            # 三阶中心矩立方根: cbrt(E[(x-mean)^3])，保留符号描述分布偏斜。
            skew = float(np.cbrt(np.mean(centered**3)))
            features.extend([mean, std, skew])
        return np.asarray(features, dtype=np.float32)
