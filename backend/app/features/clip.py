"""CLIP/OpenCLIP multimodal feature extractor."""

from __future__ import annotations

import cv2
import numpy as np

from app.core.config import get_settings
from app.core.device import get_device
from app.features.base import FeatureExtractor


class CLIPFeature(FeatureExtractor):
    """Image and text encoder backed by open_clip_torch."""

    name = "clip"
    dim = 512

    def __init__(self, device: str | None = None) -> None:
        self.device_name = device or get_device()
        self._model = None
        self._preprocess = None
        self._tokenizer = None
        self._torch = None
        self._loaded_key: tuple[str, str] | None = None

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract one L2-normalized CLIP image embedding."""

        return self.extract_batch([img_bgr])[0]

    def extract_batch(self, imgs_bgr: list[np.ndarray]) -> np.ndarray:
        """Extract L2-normalized CLIP image embeddings for BGR images."""

        if not imgs_bgr:
            return np.empty((0, self.dim), dtype=np.float32)
        model, _preprocess, _tokenizer, torch = self._ensure_model()
        batch = self._to_tensor_batch(imgs_bgr, torch)
        with torch.inference_mode():
            features = model.encode_image(batch)
            features = torch.nn.functional.normalize(features, p=2, dim=1)
        output = features.cpu().numpy().astype(np.float32)
        self.dim = int(output.shape[1])
        return output

    def extract_text(self, text: str) -> np.ndarray:
        """Extract one L2-normalized CLIP text embedding."""

        clean_text = text.strip()
        if not clean_text:
            raise ValueError("文本检索内容不能为空")
        model, _preprocess, tokenizer, torch = self._ensure_model()
        tokens = tokenizer([clean_text]).to(self.device_name)
        with torch.no_grad():
            features = model.encode_text(tokens)
            features = torch.nn.functional.normalize(features, p=2, dim=1)
        output = features[0].cpu().numpy().astype(np.float32)
        self.dim = int(output.shape[0])
        return output

    def _ensure_model(self):
        settings = get_settings()
        clip_config = settings.features.clip
        model_name = str(clip_config.get("model", "ViT-B-32"))
        pretrained = str(clip_config.get("pretrained", "openai"))
        key = (model_name, pretrained)
        if (
            self._model is not None
            and self._preprocess is not None
            and self._tokenizer is not None
            and self._torch is not None
            and self._loaded_key == key
        ):
            return self._model, self._preprocess, self._tokenizer, self._torch
        try:
            import open_clip
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "CLIP 文本搜图需要安装 open_clip_torch，请先运行: "
                ".\\.venv\\Scripts\\python.exe -m pip install open_clip_torch"
            ) from exc

        model, _train_transform, preprocess = open_clip.create_model_and_transforms(
            model_name,
            pretrained=pretrained,
            device=self.device_name,
        )
        tokenizer = open_clip.get_tokenizer(model_name)
        model.eval()
        self._model = model
        self._preprocess = preprocess
        self._tokenizer = tokenizer
        self._torch = torch
        self._loaded_key = key
        self.dim = int(clip_config.get("dim", self.dim))
        return model, preprocess, tokenizer, torch

    def _to_tensor_batch(self, imgs_bgr: list[np.ndarray], torch):
        """Convert BGR images to a normalized CLIP tensor batch."""

        settings = get_settings()
        size = int(settings.features.clip.get("image_size", 224))
        rgb_images: list[np.ndarray] = []
        for img_bgr in imgs_bgr:
            rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
            if rgb.shape[0] != size or rgb.shape[1] != size:
                rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_CUBIC)
            rgb_images.append(rgb)
        array = np.stack(rgb_images, axis=0).astype(np.float32) / 255.0
        batch = torch.from_numpy(array).permute(0, 3, 1, 2).to(self.device_name)
        mean = torch.tensor(
            (0.48145466, 0.4578275, 0.40821073),
            dtype=torch.float32,
            device=self.device_name,
        ).view(1, 3, 1, 1)
        std = torch.tensor(
            (0.26862954, 0.26130258, 0.27577711),
            dtype=torch.float32,
            device=self.device_name,
        ).view(1, 3, 1, 1)
        return (batch - mean) / std
