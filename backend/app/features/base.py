"""Feature extractor base classes and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np


class FeatureExtractor(ABC):
    """Base class for all feature extractors."""

    name: str
    dim: int

    @abstractmethod
    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract a 1D float32 feature vector."""


REGISTRY: dict[str, FeatureExtractor] = {}
_DEFAULTS_READY = False


def register(extractor: FeatureExtractor) -> None:
    """Register one extractor instance by name."""

    REGISTRY[extractor.name] = extractor


def _ensure_defaults() -> None:
    global _DEFAULTS_READY
    if _DEFAULTS_READY:
        return
    from app.features.color import ColorMoments, HSVHistogram
    from app.features.clip import CLIPFeature
    from app.features.deep import ResNet50Feature
    from app.features.shape import EdgeOrientationHistogram, HuMoments
    from app.features.texture import GLCM, LBP

    register(HSVHistogram())
    register(ColorMoments())
    register(GLCM())
    register(LBP())
    register(HuMoments())
    register(EdgeOrientationHistogram())
    register(ResNet50Feature())
    register(CLIPFeature())
    _DEFAULTS_READY = True


def get_extractor(name: str) -> FeatureExtractor:
    """Return a registered extractor by name."""

    _ensure_defaults()
    if name not in REGISTRY:
        raise KeyError(f"未知特征: {name}")
    return REGISTRY[name]


def list_extractors() -> list[str]:
    """List registered extractor names."""

    _ensure_defaults()
    return sorted(REGISTRY)
