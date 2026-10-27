# NexusSim — Reinforcement Learning Documentation

**Status:** Active  
**Phase coverage:** 7 (environment), 8 (ONNX export/inference), 9 (multi-city), 19–24 (algorithm inventory)  
**Source of truth:** `ml/train/`, `ml/env/`, `ml/algo/`, `ml/export/`, `engine/src/ai/`, `engine/src/agent/RLPolicy.h`

---

## 1. Overview

NexusSim trains decentralised signal-control policies with reinforcement learning and deploys them into the C++17 engine via ONNX. The headline algorithm is **MAPPO** (Multi-Agent Proximal Policy Optimization): one independent agent per signalised intersection, coupled only through a shared network-wide equity reward. This is an explicit product constraint (PRD BR-5): the system is **not** a single centralised controller and does **not** use cooperative message-passing MARL.

## 2. Problem Framing

Each signalised intersection is an independent MDP:

- **State (observation):** per-approach queue length (4 approaches), current phase, time in phase, time of day, neighbour pressures — 11 dimensions, normalised to `[0, 1]` (`ml/env/observation.py`).
- **Action:** `{EXTEND current phase, SWITCH to next phase}` (discrete, 2 actions) at phase boundaries (`ml/env/controller.py`).
- **Transition:** the offline `TrafficSim` / `VectorizedTrafficSim` micro-simulator steps the network; no live C++ engine call during training (`ml/env/traffic_sim.py`).
- **Termination:** episode truncates after `episode_steps` decisions (default 100); no terminal state.

Reward (per agent `i`):

```
reward_i = alpha * pressure_i + beta * equity_global
```

- `pressure_i = -sum(queue lengths at intersection i)` (local, `ml/env/reward.py`)
- `equity_global = -weighted mean of per-zone wait times`; default equal weights, or inverse baseline service level so under-served zones penalise more (`ml/env/reward.py`)

Alpha/beta default to `1.0`. Gini coefficient of zone waits is logged per checkpoint.

## 3. Environment Design

`ml/env/NexusSimEnv` is a Gymnasium-compatible `gym.Env` wrapping the offline Python simulator:

- `reset()` / `step(actions)` / `observation_space` (`Box(0,1,11)`) / `action_space` (`Discrete(2)`).
- One agent per signalised intersection (`num_agents` = intersection count).
- `TrafficSim` (dict-based, < 100 intersections) and `VectorizedTrafficSim` (numpy, ≥ 100 intersections) — selected automatically at `reset()`.
- Deterministic seeding; per-agent wait-time accounting added so average wait time is computable (`total_wait_seconds / completed`).
- `step()` returns `info` with `mean_pressure`, `equity`, `gini`, `zone_wait`, `completed`, `avg_wait`.

## 4. Algorithms & Frameworks

| Family | Algorithms | Location | Deployed to engine |
|--------|-----------|----------|--------------------|
| Headline MARL | MAPPO | `ml/train/ppo.py`, `ml/train/train.py` | Yes (via ONNX) |
| Value-based (tabular) | Q-Learning, SARSA | `ml/algo/value_based.py` | No |
| Value-based (deep) | DQN, DDQN, Dueling DQN | `ml/algo/value_based.py` | No |
| Policy-based | REINFORCE, A2C, PPO (single-agent) | `ml/algo/policy_based.py` | No |
| Continuous showcase | DDPG, TD3, SAC (Pendulum-v1 only) | `ml/algo/continuous_control.py` | No |

Frameworks: PyTorch 2.12, Gymnasium, MLflow 3.x (SQLite backend). Stable-Baselines3 for the continuous-control showcase.

Shared harness: `ml/algo/base_trainer.py` (`BaseTrainer`, `SingleAgentNexusSimEnv`, `run_benchmark`). Each suite exposes `train()` and `evaluate()` returning `mean_reward` and `mean_wait` (actual wait from the simulator, not a constant).

## 5. Training Pipeline

Entry: `ml/train/train.py --city <city> --episodes N`

- Builds/loads the city graph (`ml/env/graph_loader.py` parses `data/<city>/graph.json`; toy graph via `ml/env/toy_graph.py`).
- Runs a fixed-cycle Webster baseline (`ml/train/rollout.py`, `FixedCycleBaseline`) for reward scaling and comparison.
- Collects rollouts via `collect_episode` (agent-major tensors `[num_agents, horizon]`).
- Computes GAE (`compute_gae_batched`, vectorised across agents) and runs clipped PPO updates (`ppo_update`, shared policy/value networks, 4 epochs, entropy bonus).
- Logs `episode_reward`, `pressure`, `equity`, `gini`, `policy_loss`, `value_loss` to MLflow (`sqlite:///ml/mlflow.db`).
- Checkpoints every `--checkpoint-interval` (default 500) to `ml/checkpoints/<city>/<episode>.pt` (gitignored).
- `--episodes` is cumulative; `--resume latest|<path>` continues from a checkpoint.
- `--reward-scale` auto-scales from the baseline episode reward.

Key hyperparameters (`train.py`): `lr=5e-4`, `gamma=0.95`, `lam=0.95`, `clip_eps=0.2`, `entropy_coef=0.003`, `hidden=64`, `decision_interval=5.0`, `episode_steps=100`, `episodes_per_update=4`, `batch_size=0` (auto-scales).

Transfer: `ml/train/transfer.py --source <city|ckpt> --target <city>` fine-tunes with a lower LR (`1e-4`); reinitialises networks if obs_dim differs. Sensitivity sweep: `ml/train/sensitivity_sweep.py` over chaos × demand scale.

## 6. Deployment to the C++ Engine

`ml/export/export_onnx.py` traces `PolicyNetwork` to `policy.onnx` (opset 17, dynamic batch axis, inputs `observations`, outputs `logits`). Parity vs PyTorch checked on 10 inputs (`atol=1e-4`).

The engine (`engine/src/ai/InferenceEngine.{h,cpp}`) loads the ONNX graph via ONNX Runtime C++, batches all intersection observations into one tensor call per decision tick, runs off the hot path on a background thread + SPSC ring buffer, with CPU execution provider (CUDA EP plumbing present; GPU package download unfinished). `engine/src/agent/RLPolicy.h` adapts ONNX output to the `SignalPolicy` interface (`policy_name == "rl"`), selectable via `--signal-mode rl` or runtime `policy_switch` WebSocket message. Absent/failed model → Webster fallback.

Measured ONNX p95: 0.0179 ms (batch 64), 0.0265 ms (batch 256); re-measured 0.040–0.133 ms — all ≪ 8 ms budget (NFR-4).

## 7. Evaluation

`ml/train/evaluate.py --cities <cities> --checkpoint <ckpt>` writes `ml/results/comparison.json` with Webster vs MARL rows per city (reward, pressure, equity, gini, improvement_pct).

Measured results (`ml/results/comparison.json`):
| City | Intersections | Webster reward | MARL reward | Improvement | Webster Gini | MARL Gini |
|------|--------------|----------------|-------------|-------------|--------------|-----------|
| toy | 4 | −11,269.82 | −5,370.25 | +52.35% | 0.106 | 0.184 |
| piedmont | 4 | −26,606.20 | −30,560.61 | −14.86% | 0.192 | 0.167 |
| chicago | 3,709 | −13,973.97 | −10,298.50 | +26.30% | 0.286 | 0.331 |

> Caveat: MARL improves the scalar reward on Chicago (+26.3%) but Gini rises (0.286 → 0.331), so the equity-aware reward did not improve equity on this run. The PRD "≥ 15% wait reduction" metric is not computable from reward alone; per-agent wait accounting now exists in `traffic_sim.py` but wait-time reduction has not been published.

## 8. Known Gaps

- `ml/algo/benchmark.py`, `ml/algo/configs.yaml`, `ml/eval/report.py`, and the `--algos all` command referenced by `docs/TRD.md` and `docs/USER_STORIES.md` do not exist.
- Value-based and single-agent policy-based algorithms are evaluated only on the toy grid; no city-scale results for those families.
- DDPG/TD3/SAC evaluated on Pendulum-v1 only, never on signal control.
- CUDA ONNX execution provider not exercised end-to-end.
- Intersection counts disagree between `docs/TRD.md` (Chicago 3,709 / Ahmedabad 25) and `docs/NEXUS-SIM-DOCUMENTATION.md` (Chicago 5,217 / Ahmedabad 15,724); treat as TBD.

## 9. Artifacts

| File | Purpose |
|------|---------|
| `ml/checkpoints/<city>/<episode>.pt` | Train/transfer checkpoints (gitignored) |
| `ml/results/comparison.json` | MARL vs Webster comparison table |
| `ml/policy.onnx` | Exported engine policy |
| `ml/mlflow.db` | MLflow tracking (SQLite) |
| `engine/build/bench_inference` | ONNX latency benchmark |
