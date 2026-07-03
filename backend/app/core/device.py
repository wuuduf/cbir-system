"""Device selection helpers for optional deep learning features."""

from __future__ import annotations

from app.core.config import get_settings


def get_device() -> str:
    """Select cuda or cpu according to settings and runtime availability."""

    configured = get_settings().app.device.lower()
    if configured == "cpu":
        return "cpu"
    if configured == "cuda":
        return "cuda" if _cuda_available() else "cpu"
    return "cuda" if _cuda_available() else "cpu"


def get_device_status() -> dict[str, str | int | bool | None]:
    """Return runtime device details for health checks and CUDA acceptance."""

    configured = get_settings().app.device.lower()
    status: dict[str, str | int | bool | None] = {
        "configured": configured,
        "selected": get_device(),
        "torch_version": None,
        "torch_cuda_version": None,
        "cuda_available": False,
        "cuda_device_count": 0,
        "cuda_device_name": None,
    }

    try:
        import torch
    except ImportError:
        return status

    cuda_available = bool(torch.cuda.is_available())
    device_count = int(torch.cuda.device_count()) if cuda_available else 0
    status.update(
        {
            "torch_version": torch.__version__,
            "torch_cuda_version": torch.version.cuda,
            "cuda_available": cuda_available,
            "cuda_device_count": device_count,
            "cuda_device_name": (
                torch.cuda.get_device_name(0) if device_count > 0 else None
            ),
        }
    )
    return status


def _cuda_available() -> bool:
    try:
        import torch
    except ImportError:
        return False
    return bool(torch.cuda.is_available())
