## Slide 1: Title — NexusSim RL Component: Decentralized MARL Signal Control
- Scope: train per-intersection signal policies with reinforcement learning and deploy them into the C++ engine via ONNX
- Headline algorithm: MAPPO (Multi-Agent Proximal Policy Optimization), one independent agent per signalized intersection, shared network-wide reward (PRD BR-5)
- RL algorithm inventory: 12 algorithms total — MAPPO plus Q-Learning, SARSA, DQN, DDQN, Dueling DQN, REINFORCE, A2C, single-agent PPO, and Stable-Baselines3 DDPG/TD3/SAC (Pendulum-v1 showcase)
- Verified artifacts: ml/train/train.py, transfer.py, evaluate.py, ppo.py, rollout.py, device.py; ml/env/{NexusSimEnv,reward,observation,traffic_sim}.py; ml/algo/{base_trainer,value_based,policy_based,continuous_control}.py; ml/export/export_onnx.py; engine/src/ai/InferenceEngine.{h,cpp}; engine/src/agent/RLPolicy.h
- Not implemented despite docs: ml/algo/benchmark.py, ml/algo/configs.yaml, ml/eval/report.py, and the US-D09 `--algos all` benchmark command
**Speaker notes:** The RL component is real code, not a plan. The architectural constraint worth stating up front: BR-5 explicitly forbids both centralized control and cooperative message-passing MARL — agents are independent per-intersection learners coupled only through a shared global reward term.

## Slide 2: RL Fundamentals Relevant to This Project
- MDP framing per intersection: state = local observation, action = {EXTEND current phase, SWITCH to next phase}, reward = scalar feedback signal; decisions occur at phase boundaries, matching SignalController granularity
- Decentralized execution: each intersection runs its own policy; no agent-to-agent message passing; no single centralized controller (explicit non-goal in PRD §3)
- Coupling mechanism: a shared network-wide equity term (weighted zone wait times) enters every agent's reward, so local actions are evaluated against network-level fairness
- Observation normalized to unit range; discrete action space of size 2; reward is negative (lower queue/wait = higher reward)
- Credit assignment is local (pressure at intersection i) plus global (equity), avoiding the exponential joint-action space of full joint MARL
**Speaker notes:** These fundamentals explain why the design is "decentralized agents, shared reward" rather than a joint-action Q-table or a centralized critic: 3,709 Chicago intersections make any joint state-action space intractable, and BR-5 rules out centralized control by requirement.

## Slide 3: Environment Design (NexusSimEnv)
- Gymnasium-compatible env wrapping engine state snapshots — no live C++ calls during training (ml/env/NexusSimEnv.py)
- Observation per intersection: per-approach queue length (from spatial index), current phase, time in phase, time of day, neighbor pressures
- Action space: {EXTEND, SWITCH} (discrete, 2 actions) at phase boundaries
- VectorizedTrafficSim used above 100 intersections (dict-based simulator below); O(n log n) Gini via numpy sort
- Two simulators: dict-based for small graphs, vectorized for Chicago-scale networks
- Tests verify observation bounds, reward sign, phase cycling, and deterministic seeding (ml/tests/test_env.py, test_reward.py)
**Speaker notes:** The environment is a snapshot-based wrapper, not a live co-simulation: training reads recorded engine states, which keeps training off the simulation hot path and makes it reproducible. The 100-intersection vectorization threshold is a real performance boundary documented in ml/env/nexus_sim_env.py.

## Slide 4: Reward Design (Pressure + Equity)
- reward_i = α × pressure_i + β × equity_global, α = β = 1.0 by default (ml/env/reward.py)
- pressure_i = −Σ queue length across intersection i's approaches (local, computed in isolation)
- equity_global = −weighted mean of per-zone wait times; weights default equal, or inverse baseline service level so under-served zones penalize more
- Gini coefficient of zone waits logged per checkpoint (MLflow: episode_reward, mean_pressure, equity, gini)
- Unit tests in ml/tests/test_reward.py verify pressure scaling, equity weighting, empty input, and Gini extremes independently (US-E03)
- Tradeoff curve: varying β traces efficiency vs equity — a Phase 9/US-D06 deliverable; interactive dashboard chart planned
**Speaker notes:** The reward is deliberately simple and auditable: two separately testable functions. The equity term is what makes this an equity-aware controller rather than a pure throughput optimizer — but note Slide 10 results show Gini can worsen while reward improves, which is an open multi-objective tension.

## Slide 5: Algorithms & Frameworks Used
- Framework: PyTorch 2.12, Gymnasium, MLflow 3.x with SQLite tracking URI (file store removed in MLflow 3.x)
- ml/algo/base_trainer.py: BaseTrainer + SingleAgentNexusSimEnv wrapper + run_benchmark (device handling, reporting)
- Value-based: Q-Learning, SARSA (tabular, ε-greedy, state discretization); DQN, DDQN, Dueling DQN (replay buffer, target network, double estimator, dueling head)
- Policy-based: REINFORCE with baseline, A2C, single-agent PPO (GAE, clipped surrogate)
- Continuous showcase (Pendulum-v1 only, not signal control): DDPG, TD3, SAC via Stable-Baselines3, logged to MLflow
- Headline multi-agent: MAPPO (3-layer MLP policy + value network, shared initial weights, batched PPO updates, ml/train/ppo.py)
- ONNX export: export_onnx.py with parity check vs PyTorch (10 inputs, atol=1e-4)
**Speaker notes:** The inventory deliberately spans algorithm families (tabular → deep value → policy gradient → continuous) to satisfy BR-2 "medium depth" breadth. The Stable-Baselines3 algorithms run on Pendulum-v1 as a breadth showcase and are reported separately from signal-control results — they are not deployed to the engine.

## Slide 6: Training Pipeline
- Entry: ml/train/train.py --city <city> --episodes N --checkpoint-interval 500 (episodes cumulative; --resume latest continues from checkpoint)
- Cities: toy (4 intersections), piedmont (4), paris (16 per NEXUS-SIM-DOCUMENTATION / 30 per TRD — source discrepancy), chicago (5,217 per doc / 3,709 per TRD — discrepancy), ahmedabad (15,724 per doc / 25 per TRD)
- Checkpoints: ml/checkpoints/<city>/<episode>.pt (gitignored); chicago run has 0, 4, 52, 104, 152, 199.pt — 200-episode run completed per session log (final reward −10,298.50)
- Transfer: ml/train/transfer.py fine-tunes chicago → paris / ahmedabad (checkpoints chicago_to_paris/, chicago_to_ahmedabad/); ml/train/sensitivity_sweep.py sweeps chaos × demand scale
- Evaluation: ml/train/evaluate.py writes ml/results/comparison.json with Webster + MARL rows per city (reward, pressure, equity, gini)
- Device: --device auto/cpu/cuda:N; NEXUS_DEVICE and NEXUS_TORCH_THREADS env vars; MLflow runs in sqlite:///ml/mlflow.db
**Speaker notes:** Two numeric discrepancies between TRD and NEXUS-SIM-DOCUMENTATION.md on intersection counts (Chicago 3,709 vs 5,217; Ahmedabad 25 vs 15,724) appear in this deck because both documents are "sources of record" and disagree — treat intersection counts as TBD until one source is corrected. The chicago checkpoint chain (199.pt) is the strongest RL artifact in the repo.

## Slide 7: Deployment into the C++ Engine
- Model file: policy.onnx (or any exported ONNX graph) passed via engine --policy PATH; absent → Webster timing; load failure → warning + Webster fallback
- InferenceEngine (engine/src/ai/InferenceEngine.cpp): ONNX Runtime C++ session, batches ALL intersection observations into one tensor call per decision tick, CPU execution provider (CUDA provider plumbing present; GPU package download unfinished — docs/evidence/p8_onnx_provider.md)
- Runs off the hot path: background thread + SpscRingBuffer; engine consumes actions via shared-memory ring buffer; no live Python process in the simulation loop
- RLPolicy adapter implements SignalPolicy (policy_name "rl"), wired through --signal-mode rl or runtime policy_switch WebSocket message
- Measured latency: p95 0.0179 ms (batch 64), 0.0265 ms (batch 256); re-measured 0.040–0.133 ms over five idle runs — all ≪ 8 ms budget (NFR-4)
- AI stress test at 20k agents: −2.4 FPS vs < 5 FPS budget (docs/AI_STRESS_REPORT.md)
**Speaker notes:** Deployment is the part that is genuinely integrated: ONNX models load into the C++ engine and drive signal phases live. The latency measurements come from bench_inference.cpp (engine/build/) and the stress report; the CUDA execution-provider path is explicitly documented as unfinished, so GPU inference is not a verified capability.

## Slide 8: Use Case 1 — Adaptive Signal Control (Why RL Fits)
- Problem: fixed-cycle Webster timing cannot adapt to real-time queue buildup; demand is non-stationary across the day
- RL fit: sequential decision-making under uncertainty with delayed, sparse reward; no closed-form optimum for coupled intersections; pressure-based local reward directly targets queue reduction
- Policy: per-intersection agent extends or switches phases based on local queues + global equity term
- Result (comparison.json): chicago MARL −10,298.50 vs Webster −13,973.97 reward (+26.3%); piedmont −14.9%; toy +52.3%
- Caveat: reward improvement ≠ proven wait-time reduction — ml/env/traffic_sim.py lacks per-agent wait accounting, so the PRD "≥ 15% wait reduction" metric is uncomputable today (TBD)
**Speaker notes:** This is the central RL use case and the best-evidenced one: a trained checkpoint exists and runs in the engine via ONNX. The caveat is important — reward is the optimization target, but the PRD's headline efficacy metric (wait time) is not instrumented, so claims of faster trips rest on the training log only.

## Slide 9: Use Case 2 — Multi-City Transfer (Why RL Fits)
- Problem: training a signal policy from scratch per city is expensive; raw OD trip data is city-sensitive and should not leave the workspace
- RL fit: a policy trained on Chicago transfers as a weight initialization to Paris/Ahmedabad; only model checkpoints cross city boundaries (federated-friendly by design)
- Pipeline: train.py on chicago → transfer.py --source chicago/199.pt --target paris|ahmedabad → sensitivity_sweep.py over chaos/demand scale
- Status: transfer checkpoints exist (chicago_to_paris/19.pt, chicago_to_ahmedabad/19.pt); short 20-episode evals show Paris −0.7% and Ahmedabad −9.2% vs baseline — below baseline, motivating the pending re-seed from the real Chicago model (task 9.5)
- Evaluation: ml/train/evaluate.py --cities paris ahmedabad --checkpoint <ckpt> writes comparison rows
**Speaker notes:** Transfer learning is the RL use case that justifies the multi-city design: one trained model seeds others, keeping raw demand data local. The current transfer results are negative (below baseline), which the session log treats as an open issue — honest reporting rather than claiming success.

## Slide 10: Use Case 3 — Continuous-Control Showcase (Why RL Fits)
- SAC, TD3, DDPG trained on Pendulum-v1 (continuous torque control) via Stable-Baselines3
- RL fit: Pendulum-v1 is a canonical continuous-action benchmark where actor-critic methods (policy gradients over continuous torques) are the appropriate tool family — tabular/discrete methods cannot apply
- Purpose: breadth showcase demonstrating the 12-algorithm inventory spans continuous control, satisfying BR-2 without pretending the traffic task needs continuous actions
- Results logged to MLflow separately; return curves TBD (not re-measured in this audit)
- Not deployed to the engine; not part of the signal-control comparison
**Speaker notes:** This showcase exists to demonstrate algorithm-family breadth, not to control traffic. The signal task uses discrete {EXTEND, SWITCH} actions, so continuous algorithms are intentionally out of the hot path and out of the engine deployment scope.

## Slide 11: Results (Verified; Nothing Fabricated)
- ml/results/comparison.json: toy webster −11,269.82 vs MARL −5,370.25 → +52.35% (gini 0.106 → 0.184); piedmont −26,606.20 vs −30,560.61 → −14.86% (gini 0.192 → 0.167, improved); chicago −13,973.97 vs −10,298.50 → +26.30% (gini 0.286 → 0.331, worsened)
- MAPPO chicago: +26.3% reward gain over Webster on 3,709 intersections (TRD count; doc says 5,217 — TBD)
- Onnx parity validated against PyTorch on 10 test inputs (atol=1e-4)
- mean_wait: not reported by any suite — evaluate() intentionally returns None rather than fabricating wait times (ml/algo/value_based.py comment)
- PRD success metrics (≥ 15% wait reduction, ≥ 10% Gini improvement): not measured anywhere
**Speaker notes:** The chicago row reveals an important nuance: MARL improves the scalar reward by 26.3% but the Gini coefficient rises from 0.286 to 0.331 — the equity-aware reward did not produce better equity on this run. That is a real, reproduction-quality result from the artifact, not a claim.

## Slide 12: Limitations
- No per-agent wait-time accounting in ml/env/traffic_sim.py → PRD efficacy metrics uncomputable (docs/NEXUS-SIM-DOCUMENTATION.md §5.3 #3)
- Missing harness components claimed in TRD §4.3 and docs/USER_STORIES.md US-D09: ml/algo/benchmark.py, ml/algo/configs.yaml, ml/eval/report.py, `--algos all` command
- Tabular Q-Learning/SARSA and deep-value DQN/DDQN/Dueling evaluated only on the toy grid; no city-scale value-based results
- SAC/TD3/DDPG evaluated on Pendulum-v1 only, never on signal control
- CUDA ONNX execution provider unfinished; GPU inference not verified end-to-end
- Reward values from training logs, not independently re-run in the 2026-10 audit
**Speaker notes:** The limitations are structural, not minor: without wait-time accounting, the headline MARL claim ("outperforms fixed-cycle") can only be supported by reward curves, not journey times. The missing benchmark harness means the "12 algorithms each produce an eval report vs. Webster" requirement (TR-ML-13) is documented but not implemented.

## Slide 13: Next Steps
- Add per-agent wait-time accounting to ml/env/traffic_sim.py; re-run evaluation reporting wait-time reduction and Gini delta per city
- Implement the shared benchmark harness (benchmark.py, configs.yaml, per-algorithm eval_report.json → ml/results/<algo>/)
- Confirm the chicago run reached 200 cumulative episodes and republish comparison.json with full Webster/MARL rows for all 3 cities
- Re-seed Paris/Ahmedabad transfers from the real chicago model; run the sensitivity sweep; publish transfer_sensitivity.json
- Exercise the CUDA execution provider end-to-end; complete p95 inference validation with the real chicago checkpoint
**Speaker notes:** These are the concrete, sequenced steps that close the gap between the documented RL inventory (TRD §4.3, phases 19–24) and what is currently runnable. All entries are unstarted unless noted above.

## Slide 14: Q&A
- Trace artifacts: ml/checkpoints/chicago/199.pt, ml/results/comparison.json, ml/train/ppo.py, engine/src/ai/InferenceEngine.cpp, docs/AI_STRESS_REPORT.md
- Discrepancies flagged in this deck: intersection counts (TRD vs NEXUS-SIM-DOCUMENTATION.md), missing benchmark harness, uncomputed wait-reduction metric
**Speaker notes:** Close on the verification stance: every number in this deck either comes from a committed artifact or is marked TBD. The RL component is implemented and engine-integrated; its measured efficacy beyond reward curves is the main open item.
