# P5 Evidence — Dashboard AlgoExplorer, Signal Tick & Inference Providers

**Date:** 2026-10-19

## Dashboard (P5)

- **48-algorithm explorer mounted.** The previously orphaned
  `AlgoExplorer` component had no consumer (no import, no test). It is now
  mounted through a new `AlgoExplorerPanel` wrapper:
  - new right-dock tab **🧪 Algos**, and also included in the **All** tab;
  - loads `dashboard/public/data/36_algo_matrix.json` (legacy filename, 48
    entries), flattening the four `subjects` arrays;
  - component header renamed **NEXUSSIM 48-ALGORITHM EXPLORER**.
- **Simulation `tick` consumed.** `useWebSocket` previously ignored `data.tick`.
  It now stores `simTick`, resets it on reset, and exposes it; `RightDock`
  renders a `tick <n>` badge sourced from the engine frame.
- **Adaptive policy control.** `SignalMode` and `sendPolicySwitch` accept
  `type2_fuzzy`; the policy panel gained **Fuzzy (Mamdani)** and
  **Type-2 Fuzzy** buttons and distinct mode pills.
- **Honest provenance test.** The dashboard test now asserts the measured /
  not-measured wording instead of the fabricated catalog numbers.

## Inference providers (P7 / P8 plumbing)

- `InferenceEngine` gained `set_provider("cpu" | "cuda" | "auto")` and
  `active_provider()`:
  - `auto`/`cuda` inspect `Ort::GetAvailableProviders()` for a CUDA EP;
  - a CUDA session that fails to initialise (missing driver / cuDNN DLLs)
    automatically retries the same graph on the CPU EP and logs why;
  - `cpu` is still accepted for explicit CPU pinning, but is no longer the
  default anywhere: training (`--device auto`) and inference
  (`--onnx-provider auto`) are both GPU-first with automatic CPU fallback.
- New CLI flags `--signal-mode {auto,webster,rl,fuzzy,type2_fuzzy}` and
  `--onnx-provider {cpu,cuda,auto}`.
- `bench_inference --provider <p>` prints `Provider active: <p>`.
- Training entry points (`train.train`, `train.transfer`, `train.evaluate`) use
  `--device auto` (CUDA when available, else CPU) via the new
  `ml/train/device.py` helper.

## Verification

| Check | Command | Result |
|---|---|---|
| Dashboard tests | `cd dashboard && npm run test` | **8 / 8 passed** |
| Dashboard type-check + build | `cd dashboard && npm run build` | **exit 0** (`tsc -b && vite build`, 799 kB bundle) |
| Provider plumbing | `engine\build\bench_inference.exe --model ..\tests\fixtures\policy_toy.onnx --provider cpu` | `Provider active: cpu`, `PASS: p95 within 8ms budget` |
| CUDA training path | `.venv\Scripts\python.exe -m train.train --city toy --episodes 1 --device auto` | `Training device: cuda (NVIDIA GeForce GTX 1650)` |
| Signal-mode CLI | `engine.exe --signal-mode fuzzy/type2_fuzzy ...` | startup log prints the requested mode; run completes |

Measured ONNX inference at batch 64 (2000 iters, idle machine): **p95 0.0665 /
0.0401 / 0.0708 / 0.0586 / 0.0812 ms** across five runs — recorded as
**~0.04–0.08 ms p95** (≈100–200× inside the 8 ms budget). The README's earlier
`0.0808 ms` was a single-run figure and has been replaced by this range.

## Honest caveat

The optional **ONNX Runtime CUDA execution provider** path is plumbing-only
until an ONNX Runtime **GPU** package is linked (see
`p8_onnx_provider.md`). On the default CPU build, `--provider cuda` logs the
fallback and keeps the engine fully functional. The CUDA GPU package download
did not complete within the time box on this connection, so the CUDA EP was not
exercised end-to-end.
