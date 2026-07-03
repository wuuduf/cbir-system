"""Shape feature extractors."""

from __future__ import annotations

import cv2
import numpy as np

from app.core.config import get_settings
from app.features.base import FeatureExtractor
from app.preprocess import preprocess, to_gray


class HuMoments(FeatureExtractor):
    """Hu invariant moments after iterative thresholding."""

    name = "hu"
    dim = 7

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract log-transformed Hu invariant moments."""

        prepared = preprocess(img_bgr, get_settings().preprocess)
        gray = to_gray(prepared)
        # 中值滤波先抑制孤立噪声点，让后续边缘和二值化更稳定。
        denoised = cv2.medianBlur(gray, 3)
        # Sobel x/y 卷积核计算梯度，用梯度幅值增强形状边界。
        gx = cv2.Sobel(denoised, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(denoised, cv2.CV_32F, 0, 1, ksize=3)
        sharpened = cv2.convertScaleAbs(cv2.magnitude(gx, gy))
        binary = self._iterative_threshold(sharpened)
        moments = cv2.moments(binary)
        hu = cv2.HuMoments(moments).flatten()
        # Hu 矩跨数量级变化，使用 -sign(x)*log10(abs(x)) 压缩尺度并保留符号。
        transformed = -np.sign(hu) * np.log10(np.maximum(np.abs(hu), 1e-30))
        return transformed.astype(np.float32)

    def _iterative_threshold(self, gray: np.ndarray) -> np.ndarray:
        """Binarize an image with the iterative threshold method."""

        threshold = float(np.mean(gray))
        while True:
            lower = gray[gray <= threshold]
            upper = gray[gray > threshold]
            lower_mean = float(np.mean(lower)) if lower.size else 0.0
            upper_mean = float(np.mean(upper)) if upper.size else 0.0
            next_threshold = (lower_mean + upper_mean) / 2.0
            if abs(next_threshold - threshold) <= 0.5:
                break
            threshold = next_threshold
        return (gray > threshold).astype(np.uint8) * 255


class EdgeOrientationHistogram(FeatureExtractor):
    """Edge orientation histogram feature."""

    name = "eoh"

    def __init__(self, bins: int | None = None) -> None:
        cfg = get_settings().features.eoh
        self.bins = bins or int(cfg["bins"])
        self.dim = self.bins

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract a normalized gradient orientation histogram."""

        prepared = preprocess(img_bgr, get_settings().preprocess)
        gray = to_gray(prepared)
        # 高斯滤波减少细小噪声对方向统计的干扰。
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        gx = cv2.Sobel(blurred, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(blurred, cv2.CV_32F, 0, 1, ksize=3)
        magnitude, angle = cv2.cartToPolar(gx, gy, angleInDegrees=True)
        # 方向角按梯度幅值加权投票，强边缘对形状方向贡献更大。
        hist, _ = np.histogram(
            angle.ravel(),
            bins=self.bins,
            range=(0.0, 360.0),
            weights=magnitude.ravel(),
        )
        hist = hist.astype(np.float32)
        # 滑动平均平滑相邻方向 bin，减少方向落在 bin 边界造成的突变。
        hist = (np.roll(hist, 1) + hist + np.roll(hist, -1)) / 3.0
        total = float(hist.sum())
        if total > 0:
            hist /= total
        return hist.astype(np.float32)
