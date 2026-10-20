# P2 Evidence — 20k-Agent Tick Performance

**Date:** 2026-10-19
**Machine:** Ryzen 5 3550H (4C/8T), 16 GB RAM, Windows 11 x64
**Build:** MinGW-w64 GCC 16.1, CMake Release (`engine/build`), ONNX Runtime 1.24.1 (CPU EP)
**Gate:** average tick ≤ 16.7 ms **and** p95 ≤ 25 ms at 20,000 agents.

## Verdict

**PASS** — measured **avg 8.64 ms, p95 12 ms** (≈113 ticks/s) over a 1-minute
`--fast` run. Both gate conditions met with ~2× headroom on average and ~2.1×
on p95.

## What changed

| Area | Before | After |
|---|---|---|
| Spatial index | `Quadtree` rebuilt every tick | Counting-sort uniform grid (`engine/src/spatial/SpatialGrid.h`), reuse of buffers, O(n + cells) rebuild |
| Leader query | Radius query + full distance scan | Oriented **capsule** query (`target_speed*3 + 20` m forward, 5 m half-width) with exact distance confirmation |
| Randomness | `std::mt19937` constructed per agent per tick | Counter-based SplitMix64 (`mix64`) |
| Edge length lookups | Hash lookup per agent tick | Cached `cur_edge_len` in the AgentSystem SoA |
| Snapshot | Serial `compute_world` | Parallel `compute_world` via `ThreadPool` |

## Results

| Run | Avg | p50 | p90 | p95 | p99 | Max |
|---|---:|---:|---:|---:|---:|---:|
| Pre-optimization (prior verified baseline) | 49.18 ms | — | — | 60 ms | — | — |
| Pre-optimization (this audit, `--profile` on) | 64.53 ms | — | — | — | — | — |
| **Post-optimization (gate run)** | **8.64 ms** | 8.14 ms | 12 ms | **12 ms** | 20 ms | 58 ms |

Profile phase breakdown (post-optimization, 20k agents):

| Phase | ms/tick |
|---|---:|
| OD spawning | 0.0006 |
| Signal controllers | 0.0024 |
| Snapshot (`compute_world`) | 1.87 |
| Spatial grid rebuild | 0.85 |
| Agent update + leader query | 5.74 |
| Emissions | 0.18 |
| Metrics | 0.43 |

The pre-optimization profile (audit run) attributed 22.28 ms to the quadtree
rebuild and 35.12 ms to agent updates; the 64.53 ms total includes profiling
counter overhead and is higher than the earlier 49.18 ms baseline. Run-to-run
variance on this machine is ±10%, which is why both pre-optimization numbers are
recorded.

## Reproduce

```powershell
# From the repo root, with C:\msys64\mingw64\bin on PATH
cd engine\build
.\engine.exe --city piedmont --agents 20000 --duration 1 --fast --no-ws --profile --journey journey_p2.csv
```

The engine prints `[Profile] tick avg=... p95=...` lines and the per-phase
breakdown. `journey_p2.csv` should contain 20,001 data rows (header + one row
per agent).

## Sanity checks

- 20k run completes with 0 crashes and writes `journey_times.csv` (20,001 rows).
- 48 agents complete their trips within the 60 s simulated run, confirming
  agents are not deadlocked by the new leader-selection path.
- Behavioural note: lane-change sequences differ from pre-P2 runs because the
  per-agent RNG was replaced. Grid + capsule leader selection preserves the
  previous semantics (same leader candidate set, exact distance check retained).
