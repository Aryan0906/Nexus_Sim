# P8 Evidence — ONNX Execution-Provider Plumbing (CUDA EP Experiment)

**Date:** 2026-10-19
**Status:** GPU-first default landed. CUDA EP **attempted and failed safe** on a
CUDA-linked build (missing CUDA/cuDNN runtime DLLs); explicit `--provider cuda`
can hard-crash when those DLLs are broken — see "Runtime crash caveat".

## GPU-first defaults (the user-facing change)

Every entry point now prefers GPU and falls back to CPU automatically:

| Entry point | Flag | Default | Behaviour |
|---|---|---|---|
| `ml/train/train.py` | `--device` | `auto` | CUDA when `torch.cuda.is_available()`, else CPU |
| `ml/train/transfer.py` | `--device` | `auto` | same |
| `ml/train/evaluate.py` | `--device` | `auto` | same |
| `ml/export/export_onnx.py` | `--device` | `auto` | same (via `ml/train/device.py`) |
| `engine.exe` | `--onnx-provider` | `auto` | CUDA EP when the linked ORT build exposes it, else CPU |
| `bench_inference.exe` | `--provider` | `cpu` (explicit micro-benchmark) | prints `Provider active: <p>` |

Verified on this machine (GTX 1650, torch 2.4.1+cu124):

```powershell
.venv\Scripts\python.exe -c "from train.device import resolve_device; print(resolve_device('auto'))"
# -> cuda (NVIDIA GeForce GTX 1650)

engine\build\engine.exe --city piedmont --agents 500 --duration 1 --fast --no-ws `
    --signal-mode rl --policy tests\fixtures\policy_extend.onnx
# -> [InferenceEngine] CUDA provider unavailable; using CPU
#    [InferenceEngine] execution provider: cpu
#    AI policy loaded: ... (obs_dim=11, actions=2, provider=cpu)
```

## What was added

- `InferenceEngine::set_provider("cpu"|"cuda"|"auto")` / `active_provider()`.
- On load: `auto`/`cuda` query `Ort::GetAvailableProviders()` for a CUDA EP and
  append `OrtCUDAProviderOptions` when present; if session creation throws
  (provider DLL missing / CUDA init failure) the same graph is retried on the
  CPU EP and the reason is logged.
- CMake: `ENABLE_ONNX_CUDA` option + `-DORT_ROOT=<dir>` to link a pre-extracted
  ONNX Runtime tree (the 280 MB GPU zip is too big for FetchContent on slow
  connections; SHA256-verified when downloaded:
  `176af2aade9eb9e429cd2a738aa5d71a1f20ec7123e4b99a382ad62b9db970fb`).
- `copy_ort_dll` post-build step fixed for `ORT_ROOT` builds (it previously
  referenced a FetchContent-only variable and broke the build with an
  unbalanced quote under CMake 4.3.3).

## CUDA-linked build — what actually happened

```powershell
cmake -S engine -B engine/build_cuda -DENABLE_TESTING=ON -DENABLE_ONNX=ON `
      -DENABLE_ONNX_CUDA=ON -DORT_ROOT=%TEMP%\opencode\ort-gpu
cmake --build engine/build_cuda --target bench_inference
engine\build_cuda\bench_inference.exe --model ..\tests\fixtures\policy_toy.onnx --provider auto
```

Observed:

1. `auto` → CUDA EP attempted → `onnxruntime_providers_shared.dll` missing
   (Error 126) → ORT logged the failure → `InferenceEngine` caught the
   exception, **retried on CPU**, benchmark completed: p95 0.0377 ms, PASS.
   This demonstrates the fail-safe fallback path working as designed.
2. With the ORT `lib/` dir on `PATH` and explicit `--provider cuda`, the
   provider DLL loaded but the process died with `0xC0000013`
   (missing/mismatched CUDA/cuDNN runtime DLL — no CUDA toolkit installed on
   this machine; PyTorch's bundled cuDNN 9.x does not satisfy ORT 1.24.1).

## Runtime crash caveat (honest limitation)

The CPU fallback catches ORT **exceptions** during session creation. A missing
CUDA *runtime* DLL can instead crash the provider DLL during `LoadLibrary`
inside `session->Run`, which C++ cannot catch. Consequences:

- `--provider auto` (the default): safe — provider load failure surfaces as a
  session-creation exception and falls back to CPU (demonstrated above).
- `--provider cuda` on a machine without working CUDA/cuDNN runtime DLLs: can
  hard-crash the engine. Documented; users should use `auto` unless they have
  a verified CUDA environment.
- The 20k gate and all fuzz/RL measurements in this audit were taken on the
  **CPU** build; no CUDA-EP latency numbers are claimed anywhere.

## Measured CPU inference (batch 64, 2000 iters, idle machine)

p95 across five runs: **0.0401 / 0.0586 / 0.0710 / 0.0812 / 0.1325 ms**
(recorded as "0.04–0.13 ms p95" in the README and matrix JSON). All runs PASS
the 8 ms budget by 60–200×.
