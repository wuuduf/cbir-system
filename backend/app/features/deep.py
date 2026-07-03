"""Deep feature extractor based on ResNet50."""

from __future__ import annotations

import cv2
import numpy as np

from app.core.config import get_settings
from app.core.device import get_device
from app.features.base import FeatureExtractor


class ResNet50Feature(FeatureExtractor):
    """Deep feature extractor using a trained CIFAR model or ResNet50 fallback."""

    name = "deep"
    dim = 2048

    def __init__(self, device: str | None = None) -> None:
        self.device_name = device or get_device()
        self._model = None
        self._weights = None
        self._torch = None
        self._checkpoint_stamp: float | None = None

    def extract(self, img_bgr: np.ndarray) -> np.ndarray:
        """Extract one L2-normalized 2048D deep feature."""

        return self.extract_batch([img_bgr])[0]

    def extract_batch(self, imgs_bgr: list[np.ndarray]) -> np.ndarray:
        """Extract L2-normalized deep features for a batch of BGR images."""

        if not imgs_bgr:
            return np.empty((0, self.dim), dtype=np.float32)
        model, preprocess, torch = self._ensure_model()
        tensors = [self._to_tensor(image, preprocess, torch) for image in imgs_bgr]
        batch = torch.stack(tensors).to(self.device_name)
        with torch.no_grad():
            if hasattr(model, "forward_features"):
                features = model.forward_features(batch)
            else:
                # ResNet50 去掉 fc 后输出 avgpool 的 2048 维语义特征。
                features = model(batch).flatten(1)
            # L2 归一化后，内积即可表示余弦相似度，方便 FAISS IndexFlatIP 检索。
            features = torch.nn.functional.normalize(features, p=2, dim=1)
        return features.cpu().numpy().astype(np.float32)

    def _ensure_model(self):
        checkpoint_stamp = self._custom_checkpoint_stamp()
        if (
            self._model is not None
            and self._weights is not None
            and self._torch is not None
        ):
            if checkpoint_stamp == self._checkpoint_stamp:
                return self._model, self._weights, self._torch
            self._model = None
            self._weights = None
            self._torch = None
        custom = self._load_custom_model()
        if custom is not None:
            self._model, self._weights, self._torch = custom
            return custom
        return self._load_resnet50()

    def _load_resnet50(self):
        try:
            import torch
            from torchvision.models import ResNet50_Weights, resnet50
        except ImportError as exc:
            raise RuntimeError("深度特征需要安装 torch 和 torchvision") from exc

        weights = ResNet50_Weights.IMAGENET1K_V2
        backbone = resnet50(weights=weights)
        # 删除最终分类层，只保留卷积骨干和 avgpool 输出。
        model = torch.nn.Sequential(*list(backbone.children())[:-1])
        model.eval().to(self.device_name)
        preprocess = {
            "kind": "imagenet_resnet50",
            "size": 224,
            "mean": tuple(weights.transforms().mean),
            "std": tuple(weights.transforms().std),
        }
        self._model = model
        self._weights = preprocess
        self._torch = torch
        self._checkpoint_stamp = None
        self.dim = 2048
        return model, preprocess, torch

    def _custom_checkpoint_stamp(self) -> float | None:
        checkpoint_path = self._resolve_custom_checkpoint()
        return checkpoint_path.stat().st_mtime if checkpoint_path is not None else None

    def _load_custom_model(self):
        settings = get_settings()
        deep_config = settings.features.deep
        model_name = str(deep_config.get("model", "resnet50"))
        checkpoint_path = self._resolve_custom_checkpoint()
        should_try = model_name in {"auto", "cifar_resnet18"} or checkpoint_path
        if not should_try or checkpoint_path is None:
            if model_name == "cifar_resnet18":
                raise FileNotFoundError("CIFAR CNN 模型不存在")
            return None
        try:
            import torch

            from app.features.cifar_cnn import build_cifar_resnet18
        except ImportError as exc:
            raise RuntimeError("自训练 CNN 特征需要安装 torch 和 torchvision") from exc

        checkpoint = torch.load(checkpoint_path, map_location="cpu")
        classes = checkpoint.get("classes", [])
        feature_dim = int(checkpoint.get("feature_dim", 512))
        model = build_cifar_resnet18(
            num_classes=max(len(classes), 10), feature_dim=feature_dim
        )
        model.load_state_dict(checkpoint["model_state"])
        model.eval().to(self.device_name)
        preprocess = {
            "kind": "cifar_resnet18",
            "size": int(checkpoint.get("image_size", 32)),
            "mean": tuple(
                float(value)
                for value in checkpoint.get("mean", (0.4914, 0.4822, 0.4465))
            ),
            "std": tuple(
                float(value)
                for value in checkpoint.get("std", (0.2470, 0.2435, 0.2616))
            ),
            "checkpoint": str(checkpoint_path),
            "best_acc": float(checkpoint.get("best_acc", 0.0)),
        }
        self.dim = feature_dim
        self._checkpoint_stamp = checkpoint_path.stat().st_mtime
        return model, preprocess, torch

    def _resolve_custom_checkpoint(self):
        """Return the preferred trained CIFAR checkpoint if one exists."""

        settings = get_settings()
        checkpoint_value = str(
            settings.features.deep.get(
                "checkpoint", "../data/models/cifar_resnet18_metric.pt"
            )
        )
        candidates = [
            settings.resolve_backend_path(checkpoint_value),
            settings.resolve_backend_path("../data/models/cifar_resnet18_metric.pt"),
            settings.resolve_backend_path("../data/models/cifar_resnet18.pt"),
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _to_tensor(self, img_bgr: np.ndarray, preprocess: dict[str, object], torch):
        """Convert BGR ndarray to normalized tensor for the active deep model."""

        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        size = int(preprocess["size"])
        rgb = cv2.resize(rgb, (size, size), interpolation=cv2.INTER_CUBIC)
        array = rgb.astype(np.float32) / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1)
        mean = torch.tensor(preprocess["mean"], dtype=torch.float32).view(3, 1, 1)
        std = torch.tensor(preprocess["std"], dtype=torch.float32).view(3, 1, 1)
        return (tensor - mean) / std
