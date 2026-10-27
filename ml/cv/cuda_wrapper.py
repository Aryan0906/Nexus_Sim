"""NexusSim CV CUDA wrapper.

Provides GPU-accelerated OpenCV operations for image processing and
generation, with automatic fallback to CPU OpenCV when a CUDA-capable
OpenCV build is not available.

The wrapper mirrors the most commonly used CV operations in NexusSim:
  * color-space conversion (BGR <-> HSV)
  * thresholding / inRange
  * Gaussian blur
  * resize
  * bitwise operations (OR, AND)
  * count non-zero pixels

Usage:
    from ml.cv.cuda_wrapper import CvCuda
    cv = CvCuda()  # probes once, picks GPU if available
    img_gpu = cv.cvtColor(img, cv2.COLOR_BGR2HSV)
    mask = cv.inRange(img_hsv, lower, upper)
    result = cv.cvtColor(mask, cv2.COLOR_HSV2BGR)  # back to CPU if needed

Every method returns a regular numpy array (CPU memory), so callers never
need to know whether the work was done on GPU or CPU.
"""

from __future__ import annotations

from typing import Optional, Tuple

import cv2
import numpy as np


class CvCuda:
    """OpenCV wrapper with CUDA acceleration and CPU fallback.

    Probes once at construction. If ``cv2.cuda`` reports a CUDA-enabled
    device, GPU-accelerated GpuMat operations are used; otherwise every
    method falls back to standard CPU OpenCV. Callers interact with numpy
    arrays only -- the GPU/CPU distinction is invisible.
    """

    def __init__(self, force_cpu: bool = False):
        self._use_gpu = False
        self._device_count = 0

        if not force_cpu and hasattr(cv2, "cuda"):
            try:
                self._device_count = cv2.cuda.getCudaEnabledDeviceCount()
                if self._device_count > 0:
                    self._use_gpu = True
            except Exception:
                self._use_gpu = False

    @property
    def use_gpu(self) -> bool:
        return self._use_gpu

    @property
    def device_count(self) -> int:
        return self._device_count

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _to_gpu(self, arr: np.ndarray) -> "cv2.cuda.GpuMat":
        gmat = cv2.cuda_GpuMat()
        gmat.upload(arr)
        return gmat

    def _to_cpu(self, gmat: "cv2.cuda.GpuMat") -> np.ndarray:
        return gmat.download()

    # ------------------------------------------------------------------
    # Color-space conversion
    # ------------------------------------------------------------------
    def cvtColor(
        self, src: np.ndarray, code: int, dst: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """Convert color space (BGR<->HSV, etc.) with CUDA when available."""
        if self._use_gpu:
            g_src = self._to_gpu(src)
            g_dst = cv2.cuda.cvtColor(g_src, code)
            return self._to_cpu(g_dst)
        return cv2.cvtColor(src, code, dst)

    # ------------------------------------------------------------------
    # Thresholding
    # ------------------------------------------------------------------
    def inRange(
        self,
        src: np.ndarray,
        lowerb: np.ndarray,
        upperb: np.ndarray,
        dst: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Return mask where lowerb <= src <= upperb (CUDA when available)."""
        if self._use_gpu:
            g_src = self._to_gpu(src)
            g_mask = cv2.cuda.inRange(g_src, lowerb, upperb)
            return self._to_cpu(g_mask)
        return cv2.inRange(src, lowerb, upperb, dst)

    def threshold(
        self,
        src: np.ndarray,
        thresh: float,
        maxval: float,
        type: int,
        dst: Optional[np.ndarray] = None,
    ) -> Tuple[float, np.ndarray]:
        """Apply fixed-level threshold (CUDA when available)."""
        if self._use_gpu:
            g_src = self._to_gpu(src)
            _, g_dst = cv2.cuda.threshold(g_src, thresh, maxval, type)
            return _, self._to_cpu(g_dst)
        return cv2.threshold(src, thresh, maxval, type, dst)

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------
    def GaussianBlur(
        self,
        src: np.ndarray,
        ksize: Tuple[int, int],
        sigmaX: float,
        sigmaY: float = 0,
        borderType: int = cv2.BORDER_DEFAULT,
        dst: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Gaussian blur with CUDA when available."""
        if self._use_gpu:
            g_src = self._to_gpu(src)
            g_dst = cv2.cuda.createGaussianFilter(
                src.dtype, src.dtype, ksize, sigmaX, sigmaY, borderType
            )
            g_out = g_dst.apply(g_src)
            return self._to_cpu(g_out)
        return cv2.GaussianBlur(src, ksize, sigmaX, sigmaY, borderType, dst)

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------
    def resize(
        self,
        src: np.ndarray,
        dsize: Tuple[int, int],
        dst: Optional[np.ndarray] = None,
        fx: float = 0,
        fy: float = 0,
        interpolation: int = cv2.INTER_LINEAR,
    ) -> np.ndarray:
        """Resize image with CUDA when available."""
        if self._use_gpu:
            g_src = self._to_gpu(src)
            g_dst = cv2.cuda.resize(g_src, dsize, interpolation)
            return self._to_cpu(g_dst)
        return cv2.resize(src, dsize, dst, fx, fy, interpolation)

    # ------------------------------------------------------------------
    # Bitwise operations
    # ------------------------------------------------------------------
    def bitwise_or(
        self,
        src1: np.ndarray,
        src2: np.ndarray,
        dst: Optional[np.ndarray] = None,
        mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Bitwise OR with CUDA when available."""
        if self._use_gpu:
            g_s1 = self._to_gpu(src1)
            g_s2 = self._to_gpu(src2)
            g_mask = self._to_gpu(mask) if mask is not None else cv2.cuda_GpuMat()
            g_dst = cv2.cuda.bitwise_or(g_s1, g_s2, g_mask)
            return self._to_cpu(g_dst)
        return cv2.bitwise_or(src1, src2, dst, mask)

    def bitwise_and(
        self,
        src1: np.ndarray,
        src2: np.ndarray,
        dst: Optional[np.ndarray] = None,
        mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Bitwise AND with CUDA when available."""
        if self._use_gpu:
            g_s1 = self._to_gpu(src1)
            g_s2 = self._to_gpu(src2)
            g_mask = self._to_gpu(mask) if mask is not None else cv2.cuda_GpuMat()
            g_dst = cv2.cuda.bitwise_and(g_s1, g_s2, g_mask)
            return self._to_cpu(g_dst)
        return cv2.bitwise_and(src1, src2, dst, mask)

    # ------------------------------------------------------------------
    # Pixel statistics
    # ------------------------------------------------------------------
    def countNonZero(self, src: np.ndarray) -> int:
        """Count non-zero array elements with CUDA when available."""
        if self._use_gpu:
            g_src = self._to_gpu(src)
            return int(cv2.cuda.countNonZero(g_src))
        return int(cv2.countNonZero(src))

    # ------------------------------------------------------------------
    # Diagnostic
    # ------------------------------------------------------------------
    def info(self) -> str:
        return (
            f"CvCuda: GPU={'enabled' if self._use_gpu else 'disabled (CPU fallback)'}"
            + (f" ({self._device_count} CUDA device(s))" if self._use_gpu else "")
        )


# Singleton for convenience
_DEFAULT_INSTANCE: Optional[CvCuda] = None


def get_cv(force_cpu: bool = False) -> CvCuda:
    """Return a module-level CvCuda singleton (probed once)."""
    global _DEFAULT_INSTANCE
    if _DEFAULT_INSTANCE is None or force_cpu:
        _DEFAULT_INSTANCE = CvCuda(force_cpu=force_cpu)
    return _DEFAULT_INSTANCE


if __name__ == "__main__":
    cv = CvCuda()
    print(cv.info())
