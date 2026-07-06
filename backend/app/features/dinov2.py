"""DINOv2 self-supervised visual feature extractor."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from app.core.config import get_settings
from app.core.device import get_device
from app.features.base import FeatureExtractor


class DINOv2Feature(FeatureExtractor):
    """Self-supervised ViT image embeddings from DINOv2."""

    name = "dinov2"
    dim = 384

    def __init__(self, device: str | None = None) -> None:
        self.device_name = device or get_device()
        self._model: Any | None = None
        self._torch: Any | None = None
        self._loaded_name: str | None = None

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract one L2-normalized DINOv2 embedding."""

        return self.extract_batch([img_bgr])[0]

    def extract_batch(self, imgs_bgr: list[np.ndarray]) -> np.ndarray:
        """Extract L2-normalized DINOv2 embeddings for BGR images."""

        if not imgs_bgr:
            return np.empty((0, self.dim), dtype=np.float32)
        model, torch = self._ensure_model()
        batch = self._to_tensor_batch(imgs_bgr, torch)
        with torch.inference_mode():
            features = model(batch)
            if isinstance(features, dict):
                cls_token = features.get("x_norm_clstoken")
                features = cls_token if cls_token is not None else next(iter(features.values()))
            features = torch.nn.functional.normalize(features, p=2, dim=1)
        output = features.cpu().numpy().astype(np.float32)
        self.dim = int(output.shape[1])
        return output

    def _ensure_model(self):
        settings = get_settings()
        config = settings.features.dinov2
        model_name = str(config.get("model", "dinov2_vits14"))
        if self._model is not None and self._torch is not None and self._loaded_name == model_name:
            return self._model, self._torch
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("DINOv2 feature requires torch to be installed.") from exc

        try:
            model = torch.hub.load("facebookresearch/dinov2", model_name)
        except Exception as exc:  # noqa: BLE001 - expose actionable model-loading error
            raise RuntimeError(
                "Failed to load DINOv2. The first run needs network access to download "
                "the torch hub repository and weights. Check the network or torch hub cache."
            ) from exc
        model.eval().to(self.device_name)
        self._model = model
        self._torch = torch
        self._loaded_name = model_name
        self.dim = int(config.get("dim", self.dim))
        return model, torch

    def _to_tensor_batch(self, imgs_bgr: list[np.ndarray], torch):
        """Convert BGR images to normalized DINOv2 tensor batch."""

        settings = get_settings()
        size = int(settings.features.dinov2.get("image_size", 224))
        rgb_images: list[np.ndarray] = []
        for img_bgr in imgs_bgr:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            if rgb.shape[0] != size or rgb.shape[1] != size:
                rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_CUBIC)
            rgb_images.append(rgb)
        array = np.stack(rgb_images, axis=0).astype(np.float32) / 255.0
        batch = torch.from_numpy(array).permute(0, 3, 1, 2).to(self.device_name)
        mean = torch.tensor(
            (0.485, 0.456, 0.406), dtype=torch.float32, device=self.device_name
        ).view(1, 3, 1, 1)
        std = torch.tensor(
            (0.229, 0.224, 0.225), dtype=torch.float32, device=self.device_name
        ).view(1, 3, 1, 1)
        return (batch - mean) / std
