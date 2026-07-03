"""Texture feature extractors."""

from __future__ import annotations

import numpy as np
from skimage.feature import graycomatrix, graycoprops, local_binary_pattern

from app.core.config import get_settings
from app.features.base import FeatureExtractor
from app.preprocess import preprocess, to_gray


class GLCM(FeatureExtractor):
    """Gray-level co-occurrence matrix texture feature."""

    name = "glcm"
    dim = 8

    def __init__(
        self,
        levels: int | None = None,
        distances: list[int] | None = None,
        angles_deg: list[int] | None = None,
    ) -> None:
        cfg = get_settings().features.glcm
        self.levels = levels or int(cfg["levels"])
        self.distances = distances or [int(value) for value in cfg["distances"]]
        self.angles_deg = angles_deg or [int(value) for value in cfg["angles_deg"]]
        self.angles = [np.deg2rad(value) for value in self.angles_deg]

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract contrast/correlation/ASM/entropy mean and std over directions."""

        prepared = preprocess(img_bgr, get_settings().preprocess)
        gray = to_gray(prepared)
        # 灰度值先量化到 levels 级，降低共生矩阵维度并对应指导书 8 级量化要求。
        quantized = np.floor(gray.astype(np.float32) / 256.0 * self.levels).astype(
            np.uint8
        )
        quantized = np.clip(quantized, 0, self.levels - 1)
        matrix = graycomatrix(
            quantized,
            distances=self.distances,
            angles=self.angles,
            levels=self.levels,
            symmetric=True,
            normed=True,
        )

        values: list[np.ndarray] = []
        # 对比度、相关性和 ASM 由 skimage 计算，每个方向得到一个值。
        values.append(graycoprops(matrix, "contrast").reshape(-1))
        values.append(graycoprops(matrix, "correlation").reshape(-1))
        values.append(graycoprops(matrix, "ASM").reshape(-1))
        # 熵按 -sum(p*log2(p)) 手算，p=0 的项跳过以避免 log(0)。
        entropy_values = []
        for distance_index in range(len(self.distances)):
            for angle_index in range(len(self.angles)):
                p = matrix[:, :, distance_index, angle_index]
                non_zero = p[p > 0]
                entropy_values.append(float(-np.sum(non_zero * np.log2(non_zero))))
        values.append(np.asarray(entropy_values, dtype=np.float32))

        features: list[float] = []
        for prop_values in values:
            prop_values = np.nan_to_num(prop_values, nan=0.0, posinf=0.0, neginf=0.0)
            # 每个属性在多方向上取均值和标准差，形成 4 属性 x 2 统计量 = 8 维。
            features.extend([float(np.mean(prop_values)), float(np.std(prop_values))])
        return np.asarray(features, dtype=np.float32)


class LBP(FeatureExtractor):
    """Local binary pattern histogram feature."""

    name = "lbp"
    dim = 10

    def __init__(
        self, p: int | None = None, r: int | None = None, method: str | None = None
    ) -> None:
        cfg = get_settings().features.lbp
        self.p = p or int(cfg["P"])
        self.r = r or int(cfg["R"])
        self.method = method or str(cfg["method"])

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract a normalized uniform LBP histogram."""

        prepared = preprocess(img_bgr, get_settings().preprocess)
        gray = to_gray(prepared)
        # LBP 将局部邻域与中心像素比较，uniform 模式默认产生 P+2 个统计 bin。
        lbp = local_binary_pattern(gray, self.p, self.r, self.method)
        hist, _ = np.histogram(lbp.ravel(), bins=self.dim, range=(0, self.dim))
        hist = hist.astype(np.float32)
        total = float(hist.sum())
        if total > 0:
            hist /= total
        return hist
