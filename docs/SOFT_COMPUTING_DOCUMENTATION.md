# NexusSim — Soft Computing Documentation

**Status:** Active (partial)  
**Phase coverage:** 13 (GA calibration + Mamdani fuzzy), 28–30 (metaheuristics / swarm / Pareto — planned, out of current scope)  
**Source of truth:** `pipeline/src/optimize_calibration.py`, `pipeline/src/optimizers/`, `engine/src/agent/FuzzyPolicy.h`, `engine/src/agent/Type2FuzzyPolicy.h`

---

## 1. Overview

Soft Computing in NexusSim addresses calibration and signal control under uncertainty:

- **GA calibration** (`optimize_calibration.py`): real-valued genetic algorithm over `[speed_factor, route_spread, chaos, demand_scale]` using the validation checkpoint as fitness; parallel evaluation via `multiprocessing.Pool`; output `ga_calibration_report.json` (PRD G7 / Phase 13).
- **Fuzzy signal controller** (`FuzzyPolicy.h`, `Type2FuzzyPolicy.h`): Mamdani inference over queue length + wait time with centroid defuzzification → green-time extension; runs via `--signal-mode fuzzy`/`type2_fuzzy` (PRD G6/G7 / Phases 12–13).

Depth is "medium" (PRD BR-2). Planned expansion (phases 28–30: PSO, SA, CMA-ES, ACO, ABC, ANFIS, GP, rough sets, NSGA-II) is out of current scope and marked PENDING in `docs/BACKLOG.md`.

## 2. GA Calibration (`pipeline/src/optimize_calibration.py`)

- Chromosome: `[speed_factor, route_spread, chaos, demand_scale]` (real-valued).
- Selection: tournament; crossover: blend; mutation: Gaussian.
- Fitness: each chromosome runs one `--fast --no-ws` engine subprocess (independent `multiprocessing.Pool` workers) against the validation checkpoint.
- Output: `data/<city>/ga_calibration_report.json` with convergence curve and before/after MAPE.

Measured (Chicago): manual sweep MAPE 21.6% → GA MAPE reported 15.4% vs manual 22.8% in the newer artifact (`docs/results.md` reports 18.3% vs 21.6% — conflicting figures, see `docs/NEXUS-SIM-DOCUMENTATION.md §5.2`).

## 3. Fuzzy Controller (`engine/src/agent/FuzzyPolicy.h`)

Implements the `SignalPolicy` interface:
- Inputs: queue length, wait time (set via `set_inputs`).
- Mamdani inference with triangular membership functions.
- Centroid defuzzification → green-time extension (bounded 15 s budget).
- `tick(dt)`, `is_green()`, `current_phase_index()`, `policy_name() == "fuzzy"`.

`Type2FuzzyPolicy.h` provides Interval Type-2 fuzzy variant (`policy_name() == "type2_fuzzy"`).

## 4. Optimizer Inventory (`pipeline/src/optimizers/`, `ml/sc/`)

| Module | Algorithm | Status |
|--------|-----------|--------|
| `optimize_calibration.py` | Real-valued Genetic Algorithm | Executable |
| `optimizers/pso.py` | Particle Swarm Optimization | Module present |
| `optimizers/sa.py` | Simulated Annealing | Module present |
| `optimizers/es.py` | CMA-ES | Module present |
| `ml/sc/ant_colony.py` | Ant Colony System (ACS) | Module present |
| `ml/sc/bee_colony.py` | Artificial Bee Colony (ABC) | Module present |
| `ml/sc/anfis.py` | ANFIS neuro-fuzzy | Module present |
| `ml/sc/genetic_programming.py` | Genetic Programming | Module present |
| `ml/sc/rough_sets.py` | Rough Set attribute reducer | Module present |
| `ml/sc/nsga2.py` | NSGA-II multi-objective | Module present |

Soft-computing modules beyond GA/fuzzy are present but not wired into the live signal-control loop; catalog metrics (e.g. CMA-ES 16.2% MAPE) are unverified.

## 5. Integration

- GA output feeds simulation IDM parameters (`--speed-factor`, `--route-spread`, `--chaos`, `--demand-scale`).
- Fuzzy/Type-2 policies hot-swap at runtime via `--signal-mode` and `policy_switch`; dashboard `PolicyComparisonPanel.tsx`.
- CV congestion output (`cv_congestion.json`) is documented as a blended GA fitness term; consumption not confirmed in code.

## 6. Known Gaps

- Phases 28–30 expansion (PSO, SA, CMA-ES, ACS, ABC, ANFIS, GP, rough sets, NSGA-II) not implemented in the working tree.
- Fuzzy controller genuinely wired (P4 audit) but wait/Gini performance figures in `docs/results.md §5.1` are unverified.
- `docs/SOFT_COMPUTING_DOCUMENTATION.md` was missing from the tree; this file is provided.
