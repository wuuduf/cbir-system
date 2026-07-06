"""Model registry helpers for choosing the active deep feature checkpoint."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.config import get_settings

ACTIVE_MODEL_FILE = "active_deep_model.json"


def list_deep_models() -> dict[str, object]:
    """Return available trained deep checkpoints and the active selection."""

    models_dir = _models_dir()
    models_dir.mkdir(parents=True, exist_ok=True)
    active_path = get_active_deep_model_path()
    items = []
    for path in sorted(
        models_dir.glob("*.pt"), key=lambda item: item.stat().st_mtime, reverse=True
    ):
        info = _checkpoint_info(path)
        items.append(
            {
                "name": path.name,
                "path": str(path),
                "relative_path": _relative_backend_path(path),
                "size": path.stat().st_size,
                "updated_at": path.stat().st_mtime,
                "active": active_path is not None and path.resolve() == active_path.resolve(),
                **info,
            }
        )
    return {
        "active": str(active_path) if active_path is not None else "",
        "models": items,
    }


def set_active_deep_model(model_path: str) -> dict[str, object]:
    """Persist the selected deep checkpoint for future index builds."""

    resolved = _resolve_model_path(model_path)
    if not resolved.exists():
        raise FileNotFoundError(f"模型不存在: {resolved}")
    if resolved.suffix.lower() != ".pt":
        raise ValueError("只支持 .pt 模型文件")
    active_file = _active_file()
    active_file.parent.mkdir(parents=True, exist_ok=True)
    with active_file.open("w", encoding="utf-8") as file:
        json.dump({"path": str(resolved)}, file, ensure_ascii=False, indent=2)
    return {"active": str(resolved), "model": _checkpoint_info(resolved)}


def get_active_deep_model_path() -> Path | None:
    """Return active checkpoint path if configured and available."""

    active_file = _active_file()
    if active_file.exists():
        with active_file.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        raw_path = str(payload.get("path", ""))
        if raw_path:
            path = Path(raw_path)
            if not path.is_absolute():
                path = get_settings().resolve_backend_path(raw_path)
            if path.exists():
                return path
    default_metric = _models_dir() / "cifar_resnet18_metric.pt"
    if default_metric.exists():
        return default_metric
    default_classifier = _models_dir() / "cifar_resnet18.pt"
    if default_classifier.exists():
        return default_classifier
    return None


def _checkpoint_info(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {
        "arch": "",
        "dataset": "",
        "training_objective": "",
        "feature_dim": None,
        "best_acc": None,
        "best_p_at_k": None,
        "epoch": None,
    }
    try:
        import torch

        checkpoint = torch.load(path, map_location="cpu")
    except Exception as exc:  # noqa: BLE001 - metadata display should be best effort
        info["error"] = str(exc)
        return info
    if not isinstance(checkpoint, dict):
        return info
    for key in info:
        if key in checkpoint:
            info[key] = checkpoint[key]
    return info


def _resolve_model_path(model_path: str) -> Path:
    path = Path(model_path)
    if path.is_absolute():
        return path.resolve()
    models_candidate = (_models_dir() / model_path).resolve()
    if models_candidate.exists():
        return models_candidate
    return get_settings().resolve_backend_path(model_path)


def _relative_backend_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(get_settings().backend_root))
    except ValueError:
        return str(path)


def _models_dir() -> Path:
    return get_settings().data_root_path / "models"


def _active_file() -> Path:
    return _models_dir() / ACTIVE_MODEL_FILE
