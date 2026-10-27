"""NexusSim CUDA / GPU auto-detection module.

Probes every GPU-capable subsystem in the project and reports a single
unified verdict so launchers, tests, and CI can configure the stack
dynamically -- no manual ``--device cuda`` or ``--onnx-provider cuda``
required.

Subsystems probed:
  * PyTorch (training)              -- torch.cuda.is_available()
  * ONNX Runtime (engine inference) -- CUDAExecutionProvider present
  * OpenCV (CV image processing)    -- cv2.cuda.getCudaEnabledDeviceCount()

Usage:
    from nexussim.cuda_detect import CudaEnv
    env = CudaEnv.probe()
    print(env.summary())
    if env.torch_cuda:
        ... # launch training with --device cuda
    if env.onnx_cuda:
        ... # launch engine with --onnx-provider cuda
    if env.opencv_cuda:
        ... # CV sidecars use cv2.cuda ops
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import List


@dataclass
class CudaEnv:
    """Result of probing the machine for GPU/CUDA capability."""

    torch_cuda: bool = False
    torch_device_name: str = ""
    torch_cuda_version: str = ""

    onnx_cuda: bool = False
    onnx_providers: List[str] = field(default_factory=list)

    opencv_cuda: bool = False
    opencv_device_count: int = 0
    opencv_version: str = ""

    @property
    def any_cuda(self) -> bool:
        """True when at least one subsystem can use a GPU."""
        return self.torch_cuda or self.onnx_cuda or self.opencv_cuda

    @property
    def recommended_device(self) -> str:
        """``cuda`` if any GPU subsystem is available, else ``cpu``."""
        return "cuda" if self.any_cuda else "cpu"

    @property
    def recommended_onnx_provider(self) -> str:
        """``cuda`` if ONNX Runtime has the CUDA EP, else ``cpu``."""
        return "cuda" if self.onnx_cuda else "cpu"

    def summary(self) -> str:
        lines = ["NexusSim CUDA / GPU probe:"]
        lines.append(
            f"  PyTorch (training):  {'CUDA' if self.torch_cuda else 'CPU'}"
            + (f" ({self.torch_device_name}, CUDA {self.torch_cuda_version})" if self.torch_cuda else "")
        )
        lines.append(
            f"  ONNX Runtime (engine): {'CUDA EP' if self.onnx_cuda else 'CPU EP'}"
            + (f" ({', '.join(self.onnx_providers)})" if self.onnx_providers else "")
        )
        lines.append(
            f"  OpenCV (CV):           {'CUDA' if self.opencv_cuda else 'CPU'}"
            + (f" ({self.opencv_device_count} device(s))" if self.opencv_cuda else "")
        )
        lines.append(f"  Recommended device:    {self.recommended_device}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Probing
    # ------------------------------------------------------------------
    @classmethod
    def probe(cls) -> "CudaEnv":
        env = cls()

        # ---- PyTorch ----
        try:
            torch = importlib.import_module("torch")
            if torch.cuda.is_available():
                env.torch_cuda = True
                env.torch_device_name = torch.cuda.get_device_name(0)
                env.torch_cuda_version = getattr(torch.version, "cuda", "unknown")
        except ImportError:
            pass

        # ---- ONNX Runtime ----
        try:
            ort = importlib.import_module("onnxruntime")
            env.onnx_providers = ort.get_available_providers()
            env.onnx_cuda = "CUDAExecutionProvider" in env.onnx_providers
        except ImportError:
            pass

        # ---- OpenCV ----
        try:
            cv2 = importlib.import_module("cv2")
            env.opencv_version = getattr(cv2, "__version__", "unknown")
            if hasattr(cv2, "cuda"):
                env.opencv_device_count = cv2.cuda.getCudaEnabledDeviceCount()
                env.opencv_cuda = env.opencv_device_count > 0
        except ImportError:
            pass

        return env


if __name__ == "__main__":
    print(CudaEnv.probe().summary())
