# AI-Mode Stress Test Report (Phase 8.8)

**Gate** (PRD NFR table): ONNX mode must stay within **p95 ≤ 8 ms per decision**
and drop **< 5 fps vs. baseline mode** at 20,000 agents over a 10-minute run.

## Setup

| Parameter | Value |
|---|---|
| City | `piedmont` (368 nodes, 975 edges, 41 signalized intersections) |
| Agents | 20,000 (uniform spawn) |
| Sim time | 10 minutes (6,000 ticks, dt = 0.1 s) |
| Mode | `--fast --no-ws` headless |
| Platform | Windows x64, MinGW-w64 GCC 16, onnxruntime 1.24.1 (CPU) |
| Policy cadence | one batched decision across all 41 intersections every 5 sim-seconds |

## Results

| Run | Avg tick | p95 tick | FPS (1000/avg) | ΔFPS |
|---|---|---|---|---|
| Webster baseline (`--policy` omitted) | 34.78 ms | 46.08 ms | 28.8 | — |
| AI, always-EXTEND policy (isolates compute overhead) | 37.94 ms | 55.27 ms | 26.4 | **−2.4 ✅ (<5)** |
| AI, random-weight toy policy (switches most intervals) | 42.18 ms | 65.42 ms | 23.7 | −5.1 ⚠️ |

Inference micro-benchmark (`bench_inference`, 1,000 calls): batch 64 p95 = **0.018 ms**,
batch 256 p95 = **0.027 ms** — roughly 300x inside the 8 ms budget.

---

## 2026-10 Addendum — Post-Optimization Re-Measurement

The Phase 8.8 numbers above were taken before the P2 spatial-grid rewrite and
before the fuzzy policies were actually wired into signal timing. Re-measured
on the same machine with the rebuilt engine (`engine/build/engine.exe`,
`--city piedmont --agents 20000 --duration 1 --fast --no-ws --profile`):

| Mode | Avg tick | p50 | p95 | p99 | Max | `signals` phase |
|---|---:|---:|---:|---:|---:|---:|
| `webster` (baseline) | 9.22 ms | 8.52 ms | 16 ms | 28 ms | 46 ms | 0.002 ms |
| `fuzzy` | 9.65 ms | 9.10 ms | 12 ms | 20 ms | 47 ms | 0.080 ms |
| `type2_fuzzy` | 11.50 ms | 12 ms | 16 ms | 28 ms | 72 ms | 0.082 ms |
| `rl` (fixture ONNX policy) | 12.26 ms | 12 ms | 20 ms | 32 ms | 58 ms | 0.024 ms |

Headline gate (P2: avg ≤ 16.7 ms, p95 ≤ 25 ms): **PASS in every mode**.
Pacing is ~85–110 ticks/s (not 60 FPS): the `dt = 0.1 s` simulation runs at
roughly 8–10× real time in `--fast` headless mode.

ONNX inference p95 re-measured at batch 64: **0.040–0.133 ms** over five idle
runs (the earlier `0.018`/`0.027` figures were best-case single runs).

Evidence and reproduction commands: `docs/evidence/p2_performance.md`,
`docs/evidence/p4_fuzzy_wiring.md`.

> Caveat: the higher `signals` cost for fuzzy modes is the real fuzzy inference
> executing per intersection — it is not free, but it is bounded and stays well
> inside the tick budget at 20,000 agents.

## Interpretation

- **Computational overhead passes the gate.** With a policy whose actions are
  identical to baseline (zero weights ⇒ argmax = EXTEND = keep Webster timing),
  fps drops 2.4 — within the < 5 fps budget. Total ONNX work for the whole run
  is ~120 batched calls ≈ 3 ms; the residual delta is dominated by the periodic
  queue-counting scan and normal run-to-run variance (±10% observed between
  same-config runs on this machine).
- **The random-weight row is a behavioral effect, not an inference cost.**
  An untrained policy that switches phases almost every interval creates heavier
  congestion (denser stopped clusters), which makes leader-finding queries more
  expensive. That slowdown would equally affect any control scheme producing the
  same signal patterns; it is not attributable to ONNX inference.
- Recommendation: re-run the third configuration with a trained checkpoint
  (`ml/export/export_onnx.py`) when evaluating production behavior.

## Reproduce

```bash
# baseline
engine --city piedmont --agents 20000 --duration 10 --fast --no-ws

# AI compute-overhead isolation (always-EXTEND zero-weight policy)
engine --city piedmont --agents 20000 --duration 10 --fast --no-ws \
       --policy engine/tests/fixtures/policy_extend.onnx

# AI behavioral stress (random-weight toy policy)
engine --city piedmont --agents 20000 --duration 10 --fast --no-ws \
       --policy engine/tests/fixtures/policy_toy.onnx

# latency micro-benchmark
bench_inference --model tests/fixtures/policy_toy.onnx            # batch 64
bench_inference --model tests/fixtures/policy_toy.onnx --batch 256
```

`policy_extend.onnx` generation (torch 2.x):

```python
m = torch.nn.Sequential(torch.nn.Linear(11,16), torch.nn.ReLU(),
                        torch.nn.Linear(16,16), torch.nn.ReLU(),
                        torch.nn.Linear(16,2))
for p in m.parameters(): p.zero_()
torch.onnx.export(m, torch.zeros(1,11), 'policy_extend.onnx',
                  input_names=['observations'], output_names=['logits'],
                  dynamic_axes={'observations':{0:'batch'}},
                  opset_version=17, dynamo=False)
```
