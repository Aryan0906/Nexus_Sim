"""Shared PyTorch device selection for training/evaluation entry points.

``--device auto`` (the default) uses CUDA when the local torch build reports
an available GPU and otherwise falls back to CPU, so the same commands work on
GPU and CPU-only machines. Explicit values ("cpu", "cuda", "cuda:1") are passed
through unchanged.
"""

from __future__ import annotations

import torch


def resolve_device(requested: str = "auto") -> torch.device:
    if requested is None or requested == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(requested)


def describe_device(device: torch.device) -> str:
    if device.type == "cuda":
        index = device.index if device.index is not None else torch.cuda.current_device()
        return "%s (%s)" % (device, torch.cuda.get_device_name(index))
    return str(device)
