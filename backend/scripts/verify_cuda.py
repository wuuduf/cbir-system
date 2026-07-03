"""Verify CUDA availability for the CBIR deep feature path."""

from __future__ import annotations

import sys

import torch

from app.core.device import get_device, get_device_status


def main() -> int:
    status = get_device_status()
    print(f"configured: {status['configured']}")
    print(f"selected: {status['selected']}")
    print(f"torch: {status['torch_version']}")
    print(f"torch_cuda: {status['torch_cuda_version']}")
    print(f"cuda_available: {status['cuda_available']}")
    print(f"cuda_device_count: {status['cuda_device_count']}")
    print(f"cuda_device_name: {status['cuda_device_name']}")

    if get_device() != "cuda":
        print("CUDA is not selected by the application.", file=sys.stderr)
        return 1

    x = torch.randn(1024, 1024, device="cuda")
    y = x @ x
    torch.cuda.synchronize()
    print(f"cuda_tensor_ok: shape={tuple(y.shape)} device={y.device}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
