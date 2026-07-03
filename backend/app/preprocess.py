"""Image loading and preprocessing utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cv2
import numpy as np


class PreprocessLike(Protocol):
    """Minimal protocol for preprocessing settings."""

    size: tuple[int, int]
    denoise: str
    equalize: bool


def load_image(path: str | Path) -> np.ndarray:
    """Load an image as BGR uint8, supporting paths with Chinese characters."""

    file_path = Path(path)
    data = np.fromfile(str(file_path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图像: {file_path}")
    return image


def decode_image_bytes(data: bytes) -> np.ndarray:
    """Decode uploaded image bytes as BGR uint8."""

    array = np.frombuffer(data, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("上传文件不是有效图像")
    return image


def preprocess(img: np.ndarray, cfg: PreprocessLike) -> np.ndarray:
    """统一尺寸 -> 可选降噪 -> 可选 Y 通道均衡化，返回 BGR 图像。"""

    width, height = cfg.size
    processed = cv2.resize(img, (width, height), interpolation=cv2.INTER_AREA)
    if cfg.denoise == "median":
        processed = cv2.medianBlur(processed, 3)
    elif cfg.denoise == "gaussian":
        processed = cv2.GaussianBlur(processed, (3, 3), 0)

    if cfg.equalize:
        yuv = cv2.cvtColor(processed, cv2.COLOR_BGR2YUV)
        yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
        processed = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
    return processed


def to_gray(img: np.ndarray) -> np.ndarray:
    """Gray = 0.30R + 0.59G + 0.11B，按指导书系数手写转换。"""

    b = img[:, :, 0].astype(np.float32)
    g = img[:, :, 1].astype(np.float32)
    r = img[:, :, 2].astype(np.float32)
    gray = 0.30 * r + 0.59 * g + 0.11 * b
    return np.clip(gray, 0, 255).astype(np.uint8)
