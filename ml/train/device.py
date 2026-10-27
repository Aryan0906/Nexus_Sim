"""Device resolution shared by the NexusSim training entry points.

Every entry point takes ``--device`` with the same semantics:

``auto``    Use CUDA when the installed PyTorch has a working CUDA build,
            otherwise fall back to the CPU.
``cpu``     Force the CPU.
``cuda``    Force CUDA. Raises ``RuntimeError`` when CUDA is not usable, so a
            silent CPU fallback can never hide a misconfigured install.
``cuda:N``  Force one specific CUDA device.

``NEXUS_DEVICE`` supplies the default when ``--device`` is not given.
"""

from __future__ import annotations

import os

import torch

CUDA_INDEX_URL = "https://download.pytorch.org/whl/cu130"


def cuda_is_available() -> bool:
    """Return True when the installed PyTorch has a working CUDA build."""
    try:
        return torch.cuda.is_available()
    except Exception:  # pragma: no cover - driver/loader faults
        return False


def _install_hint() -> str:
    base_version = torch.__version__.split("+")[0]
    return (
        "  installed torch: %s (CUDA runtime: %s)\n"
        "  Install a CUDA build, for example:\n"
        "      pip install --upgrade torch==%s+cu130 --index-url %s\n"
        "  Or run with --device cpu."
        % (torch.__version__, torch.version.cuda or "none",
           base_version, CUDA_INDEX_URL)
    )


def resolve_device(spec: str | None = None) -> torch.device:
    """Resolve a ``--device`` spec into a usable ``torch.device``.

    Raises ``RuntimeError`` when CUDA is requested but not available, and
    ``ValueError`` when the spec is not a recognised device name.
    """
    spec = (spec or os.environ.get("NEXUS_DEVICE") or "auto").strip().lower()

    if spec in ("auto", ""):
        return torch.device("cuda" if cuda_is_available() else "cpu")

    if spec == "cpu":
        return torch.device("cpu")

    if spec == "cuda" or spec.startswith("cuda:"):
        if not cuda_is_available():
            raise RuntimeError(
                "CUDA device '%s' requested but this PyTorch build has no "
                "usable CUDA support.\n%s" % (spec, _install_hint())
            )
        if ":" in spec:
            index = int(spec.split(":", 1)[1])
            count = torch.cuda.device_count()
            if index < 0 or index >= count:
                raise RuntimeError(
                    "CUDA device '%s' requested but only %d CUDA device(s) "
                    "are visible." % (spec, count)
                )
        return torch.device(spec)

    raise ValueError(
        "Unknown device %r. Use one of: auto, cpu, cuda, cuda:N." % spec
    )


def describe_device(device: torch.device) -> str:
    """Return a human-readable description of the resolved device."""
    if device.type == "cuda":
        index = device.index if device.index is not None else torch.cuda.current_device()
        return "cuda:%d (%s)" % (index, torch.cuda.get_device_name(index))
    return device.type


def gpu_status(device: torch.device) -> str:
    """Return a short GPU telemetry string for progress output.

    Returns an empty string when the device is not CUDA, so callers can
    append it unconditionally.
    """
    if device.type != "cuda":
        return ""
    try:
        index = device.index if device.index is not None else torch.cuda.current_device()
        util = torch.cuda.utilization(index)
        reserved_mb = torch.cuda.memory_reserved(index) / (1024 ** 2)
        return "gpu %d%% %.0fMiB" % (util, reserved_mb)
    except Exception:  # pragma: no cover - pynvml/driver faults
        return "gpu n/a"
