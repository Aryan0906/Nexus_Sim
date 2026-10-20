# NexusSim — Benchmark & Validation Results

This document consolidates empirical benchmarks, real-world validation findings, multi-agent reinforcement learning (MARL) signal control evaluation metrics, soft computing ablation studies, computer vision classification metrics, and 12-algorithm RL inventory benchmarks.

---

## 1. Engine Performance & Spatial Index Benchmarks

> **Measured 2026-10** (Ryzen 5 3550H, MinGW GCC 16 Release build). Figures marked
> *(catalog)* are design/spec values that were not re-measured in this audit.

### 1.1 Spatial Index & Tick-Latency Benchmark
The runtime spatial index is a counting-sort **uniform grid**
(`engine/src/spatial/SpatialGrid.h`); the historical Quadtree and its naive-scan
comparison remain available in `engine/bench/bench_quadtree.cpp` for reference.

| Metric | Value | Baseline / Notes |
| :--- | :--- | :--- |
| **Max Stress-Tested Capacity** | 20,000 concurrent agents | 0 crashes, 0 memory leaks *(measured 2026-10)* |
| **Tick latency @ 20k (avg / p50 / p95)** | **8.64 ms / 8.14 ms / 12 ms** | ~113 ticks/s, 1-min `--fast` run *(measured)* |
| — grid rebuild phase | 0.85 ms/tick | `engine --profile` breakdown *(measured)* |
| — agent update + leader query phase | 5.74 ms/tick | capsule query on the grid *(measured)* |
| — snapshot/serialize phase | 1.87 ms/tick | parallel `compute_world` *(measured)* |
| **Tick latency @ 500 agents** | 0.472 ms avg / 0.695 ms p95 | *(measured, pre-existing baseline)* |
| Historical quadtree vs naive scan | 21.6× @ 20k agents | `bench_quadtree` *(measured)* |

See `docs/evidence/p2_performance.md` for the reproduction commands.

---

## 2. Real-World Traffic Data Validation & Soft Computing GA Calibration (Chicago)

### 2.1 Calibration Method Comparison: Manual vs. Genetic Algorithm (Phase 13)
The genetic algorithm evolutionary search (`optimize_calibration.py`) evolved real-valued chromosomes `[speed_factor, route_spread, chaos, demand_scale]` over 15 generations to minimize Mean Absolute Percentage Error (MAPE).

| Calibration Method | Best Chromosome `[speed_factor, route_spread, chaos, demand_scale]` | MAPE (%) | Improvement vs. Manual |
| :--- | :--- | :---: | :---: |
| **Manual Sweep (Phase 6)** | `[0.55, 0.20, 0.10, 0.000388]` | 21.6% | Baseline |
| **GA Evolutionary Search (Phase 13)** | `[0.62, 0.25, 0.08, 0.000412]` | **18.3%** | **+15.3% reduction** |

---

## 3. Computer Vision & Natural Language Processing (Phases 14–17, 25)

### 3.1 Computer Vision Performance Metrics
| CV Subsystem | Method / Architecture | Metric / Accuracy | Latency |
| :--- | :--- | :---: | :---: |
| **Real-World Congestion (Phase 14)** | Classical OpenCV (HSV) vs CNN | **91.4% (Classical) / 94.8% (CNN)** | < 1.2 ms |
| **Synthetic Virtual Camera (Phase 15)** | Top-down canvas blob detection | **97.5% vehicle detection accuracy** | 12 ms |
| **CV Foundation (Phase 25)** | YOLO object detector & MOG2 subtractor | **95.2% YOLO count accuracy** | ~15 ms |

---

## 4. Complete 12-Algorithm RL Inventory Benchmark (Phases 19–24)

### 4.1 Value-Based, Policy-Based, and Continuous RL Comparison

> **Provenance:** *Mean Reward* values are `ml/algo` training-log outputs on the
> toy environment. *Avg Wait Time* values are **catalog figures** — the toy env
> exposes no real wait-time signal, so `evaluate()` now returns
> `mean_wait: None` rather than a fabricated constant.

| Family | Algorithm | Model Architecture | Mean Reward | Avg Wait Time (s) *(catalog)* | Training Time (50 eps) |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **Value-Based** | Q-Learning | Tabular Discretization | -48,768.5 | 38.2 s | 1.21 s |
| **Value-Based** | SARSA | Tabular On-Policy | -53,864.1 | 39.1 s | 1.18 s |
| **Value-Based** | DQN | 3-Layer Deep Q Network | -59,126.1 | 33.4 s | 8.40 s |
| **Value-Based** | DDQN | Double Deep Q Network | -48,768.5 | 31.8 s | 7.09 s |
| **Value-Based** | Dueling DQN | Value + Advantage Stream | -56,956.4 | 30.5 s | 10.43 s |
| **Policy-Based** | REINFORCE | Monte Carlo Policy Gradient | -47,700.1 | 35.8 s | 5.28 s |
| **Policy-Based** | A2C | Advantage Actor-Critic | -59,126.1 | 31.2 s | 11.79 s |
| **Policy-Based** | PPO (Single) | Single-Agent PPO | -59,126.1 | 28.4 s | 4.64 s |
| **Continuous** | DDPG | Continuous Actor-Critic | -59,126.1 | 29.8 s | 11.82 s |
| **Continuous** | TD3 | Twin Delayed DDPG | -59,126.1 | 28.9 s | 12.26 s |
| **Continuous** | SAC | Soft Actor-Critic (Entropy) | **-48,768.5** | **27.5 s** | 12.73 s |
| **Headline MARL**| MAPPO | Multi-Agent Decentralized PPO | **-11,122.6** | **28.4 s** | — |

---

## 5. Signal Control Policies: Webster, Fuzzy Logic, and MARL (Phase 13)

### 5.1 Policy Performance Comparison across Controller Types

> **Provenance:** the wait/Gini figures below are **catalog values** carried
> from the design spec — they were not re-measured in the 2026-10 audit. The
> fuzzy and type-2 policies are genuinely wired into the signal timing since
> P4 (per-intersection green extension driven by queue/wait demand), so these
> numbers can now be reproduced by running the engine with
> `--signal-mode fuzzy` / `--signal-mode type2_fuzzy`.

| Policy Type | Strategy Description | Avg Wait Time (s) | Gini Index (Equity) | Computational Overhead / Node |
| :--- | :--- | :---: | :---: | :---: |
| **Webster (Fixed-Cycle)** | Fixed Webster green allocations based on historical volumes | 42.5 s | 0.48 | < 0.01 ms |
| **Fuzzy Logic (Mamdani)** | Triangular MFs over queue & wait time with centroid defuzzification | **32.1 s** | **0.35** | ~0.05 ms |
| **MARL (MAPPO)** | Neural policy trained via PyTorch & ONNX inference engine | **28.4 s** | **0.29** | ~0.80 ms |

---

## 6. Complete 48-Algorithm Multi-Subject Portfolio (Phases 26–36)

The table below summarizes the comprehensive 48-algorithm inventory (12 per subject) fully implemented across Computer Vision, Soft Computing, Natural Language Processing, and Reinforcement Learning. The source file keeps its historical `36_algo_matrix.json` name; the metrics column values are catalog design targets unless labelled **measured**.

| Subsystem | Count | Key Headline Algorithms | Primary Achievement / Metric |
| :--- | :---: | :--- | :--- |
| **Computer Vision (CV)** | 12 | DeepSORT, U-Net, Mask R-CNN, Lucas-Kanade, Anomaly Detector, Crowd Density | 97.5% Blob count accuracy, 100% U-Net road IoU, real-time optical flow |
| **Soft Computing (SC)** | 12 | GA, PSO, SA, CMA-ES, Ant Colony (ACS), Bee Colony (ABC), ANFIS, Type-2 Fuzzy, GP, NSGA-II | CMA-ES (16.2% MAPE), NSGA-II Pareto trade-off, ACS adaptive routing |
| **NLP** | 12 | Intent Classifier, Sentiment Analyzer, Naive Bayes, NER, Coreference, TextRank, Knowledge Graph | 96.4% Intent accuracy, multi-entity span extraction, RDF semantic graph |
| **Reinforcement Learning** | 12 | MAPPO, DQN, DDQN, Dueling DQN, REINFORCE, A2C, PPO, SAC, TD3, DDPG | MAPPO (+26.3% reward gain on 3,709 Chicago nodes, training log), p95 inference latency 0.04-0.13 ms *(measured range)* |
| **TOTAL** | **48** | **48 algorithms across 4 subjects** | **End-to-End Interoperability via Event Bus & Algo Explorer** |
