# P4 Evidence — Fuzzy / Type-2 Signal Policies Actually Wired

**Date:** 2026-10-19
**Machine:** Ryzen 5 3550H, Windows 11 x64, MinGW-w64 GCC 16.1 Release

## Problem found in the audit

`FuzzyPolicy::tick` and `Type2FuzzyPolicy::tick` only called
`controller_->tick(dt)` — the fuzzy inference engine existed and was unit-tested
on raw inputs, but its defuzzified output never reached the signal timing. The
only observable effect of selecting "fuzzy" was a broadcast label.

## Fix

1. `SignalPolicy` gained a demand-input hook:
   `virtual void set_inputs(double queue_len, double wait_time)`.
2. `FuzzyPolicy` / `Type2FuzzyPolicy` now perform genuine **adaptive green
   extension**: when the active green is about to expire they add the
   defuzzified extension (capped at a 15 s per-phase budget) to the controller
   timer. Budget resets when a new green phase begins.
3. `Simulation` installs a per-intersection policy map for `fuzzy` /
   `type2_fuzzy` modes, refreshes aggregate queue length + mean wait once per
   simulated second (single pass over active agents), and ticks each signal
   through its policy.
4. The ONNX (RL) policy application is gated to `signal_mode_ == "rl"` so it
   cannot fight fuzzy timing.
5. `--signal-mode` and `--onnx-provider` CLI flags, plus `type2_fuzzy` accepted
   in the WebSocket `policy_switch` command and NLP parser.

## Evidence A — timing actually changes (unit level)

`engine/tests/test_fuzzy.cpp` (`FuzzyPolicyWiringTest.*`):

| Test | Assertion | Result |
|---|---|---|
| `HighDemandExtendsGreenBeyondLowDemand` | fuzzy + (queue 40, wait 120) keeps green ≥ 10 s longer than fuzzy + (0, 0) | PASS |
| `ExtensionBudgetIsCappedAtFifteenSeconds` | repeated imminent expiry releases the phase, budget consumed in ≤ 4 extensions | PASS |
| `Type2HighDemandAlsoExtendsGreen` | interval type-2 policy also extends green ≥ 10 s under high demand | PASS |

Run:

```powershell
cd engine
.\build\engine_test.exe --gtest_filter=FuzzyPolicyWiringTest.*
```

Result: `3 tests from 1 test suite ran. [ PASSED ] 3 tests.`

## Evidence B — end-to-end at 20,000 agents (1-min `--fast` run, piedmont)

| Signal mode | Avg tick | p95 | p99 | `signals` phase (ms/tick) |
|---|---:|---:|---:|---:|
| `webster` (baseline) | 9.22 ms | 16 ms | 28 ms | 0.002 |
| `fuzzy` | 9.65 ms | 12 ms | 20 ms | 0.080 |
| `type2_fuzzy` | 11.50 ms | 16 ms | 28 ms | 0.082 |
| `rl` (fixture ONNX policy) | 12.26 ms | 20 ms | 32 ms | 0.024 |

All modes stay inside the P2 gate (avg ≤ 16.7 ms, p95 ≤ 25 ms). The `signals`
phase grows ~40× when a fuzzy policy is active, which is the measurable
footprint of the (now-executed) fuzzy inference.

```powershell
cd engine\build
.\engine.exe --city piedmont --agents 20000 --duration 1 --fast --no-ws --signal-mode fuzzy --profile
.\engine.exe --city piedmont --agents 20000 --duration 1 --fast --no-ws --signal-mode type2_fuzzy --profile
```

## Honest caveat

The catalog/README wait-time and Gini figures for these policies (e.g. "32.1 s
wait") were **not** re-measured here — they remain design-target values and are
labelled as such in `docs/results.md`. The claim evidenced in this file is
narrower and stronger: *the fuzzy policies genuinely modify signal timing and
their inference cost is visible and bounded.*
