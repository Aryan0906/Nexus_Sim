# P3 Evidence — Benchmark / Metric Honesty Pass

**Date:** 2026-10-19

## Problem found in the audit

- `ml/eval/benchmark_36.py` advertised that it "executes and audits all 36
  algorithms" but only copied hard-coded latency/accuracy strings out of
  `ALGORITHM_CATALOG` into JSON.
- Eight RL `evaluate()` methods returned a **constant** `mean_wait`
  (38.2, 39.1, 33.4, 31.8, 30.5, 35.8, 31.2, 28.4, 29.8, 28.9, 27.5) that was
  never computed — the toy env exposes no wait-time signal.
- The catalog marked RL-1 (MAPPO) and RL-4 (DQN) as `DEPLOYED_C++`, but no C++
  DQN or C++ MAPPO exists in the engine. Only the *ONNX policy deployment* path
  is C++.
- `performance_summary` carried four unverified headline claims.

## Changes

1. **Fabricated waits removed.** `ml/algo/{value_based,policy_based,continuous_control}.py`
   now return `mean_wait: None` with a comment explaining the toy env has no
   wait signal. `base_trainer.run_benchmark` prints `n/a (not measured)` and
   serialises `null` instead of inventing a number.
2. **Catalog status corrected.** RL-1 and RL-9 → `ACTIVE`; RL-4 → `BENCHMARKED`
   with the metric string `"Wait 33.4s (catalog value; no C++ DQN in engine)"`.
   RL-1/RL-9 metrics are suffixed `(catalog, not independently verified)`.
3. **`performance_summary` rewritten** to state, in the JSON itself, which
   numbers are measured and which are not:

   | Key | New value |
   |---|---|
   | `fastest_subsystem` | `C++ ONNX policy inference, 0.05 ms p95 per batch (engine bench_inference, measured)` |
   | `most_accurate_cv` | `Not independently measured; CV detectors are classical/surrogate (no real YOLO/U-Net/Mask R-CNN weights in repo)` |
   | `best_calibration_optimizer` | `Not measured; MAPE figures in the catalog are design targets` |
   | `highest_rl_throughput` | `Not measured; reward-gain figures in the catalog are training-log claims` |

4. **Provenance field** `metrics_provenance` added to the generated matrix,
   stating that per-algorithm `latency_ms`/`accuracy`/`metric` values are
   catalog design targets unless suffixed `(measured)`.
5. **Dashboard contract test updated** to assert the honest strings (no longer
   asserting the fabricated `0.08 ms` / `97.5%` / `16.2%` / `+26.3%`).
6. **Doc-level provenance notes** added to `README.md` and `docs/results.md`
   (per-table "catalog, not re-measured" callouts).

## Verification

```powershell
.venv\Scripts\python.exe ml\eval\benchmark_36.py
.venv\Scripts\python.exe -c "import json;d=json.load(open('dashboard/public/data/36_algo_matrix.json'));print(d['total_algorithms'], d['metrics_provenance'][:60])"
.venv\Scripts\python.exe -m pytest ml\tests -q      # 84 passed
cd dashboard; npm run test                           # 8 passed
```

Result: matrix regenerated with `total_algorithms = 48` and
`metrics_provenance` present; `ml/tests` 84/84; Vitest 8/8.

## Honest caveat

This pass makes the unverified claims *visible*, it does not make them true.
The catalog latency/accuracy values would need per-algorithm measurement runs
(out of scope; real YOLO/U-Net/Mask R-CNN weights are not in the repo) before
they can be upgraded to `measured`.
