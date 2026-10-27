# NexusSim

A real-time, multi-agent urban traffic simulation and AI research sandbox. Rebuilds real city road networks from OpenStreetMap, drives them with origin–destination (OD) demand, simulates traffic in a C++17 engine, and streams live state to a React dashboard over WebSocket.

NexusSim covers four academic subjects — Reinforcement Learning, Computer Vision, NLP, and Soft Computing — in one integrated simulation (not four isolated demos). It is a planner's sandbox for stress-testing signal policies, bus lanes, and congestion pricing on a copy of a city before changing a real street; equity (Gini coefficient of wait times) is a first-class metric alongside efficiency.

## Repository layout

| Path | Purpose |
|------|---------|
| `engine/` | C++17 simulation engine (IDM car-following, A* routing, uniform-grid proximity, signal policies, ONNX inference, WebSocket server) |
| `pipeline/` | Python 3.11 data pipeline (OSM download/clean/export, OD matrix, validation, GA calibration, CV congestion) |
| `ml/` | Python ML: MARL env, MAPPO trainer, 12-algorithm RL inventory, CV and NLP sidecars, ONNX export |
| `dashboard/` | React 19 + TypeScript + Vite + Leaflet dashboard |
| `gateway/` | Python FastAPI gateway (:8000) |
| `data/` | Per-city graph.json, od_matrix.json, validation and calibration reports |
| `docs/` | Documentation (PRD, TRD, tech stack, subject docs, schemas, checklist, evidence) |
| `docker/` | Multi-stage Dockerfiles and docker-compose.yml (present, unbuilt in this environment) |

## What is verified (working tree)

- **Engine performance**: 20,000 agents at 8.64 ms avg / 12 ms p95 (~113 ticks/s headless); ONNX inference p95 0.0179 ms (batch 64) / 0.0265 ms (batch 256), well under the 8 ms budget (`docs/evidence/p2_performance.md`, `docs/AI_STRESS_REPORT.md`).
- **Tests measured in this environment**: pipeline pytest 39 passed; ml pytest 80 passed, 1 skipped; dashboard vitest 8 passed; gateway pytest 38 collected.
- **MARL**: MAPPO checkpoint `ml/checkpoints/chicago/199.pt` loads into the engine via ONNX (`policy.onnx`). `ml/results/comparison.json`: chicago MARL −10,298.50 vs Webster −13,973.97 reward (+26.30%); toy +52.35%; piedmont −14.86%.
- **Sidecars**: virtual camera (:9003), NLP chat/incidents (:9004) run as independent processes.

## What is not yet verified / flagged

- Chicago validation checkpoint not met: MAPE 21.6% but only 63.6% of corridors within 25% (target ≥ 75%) — `data/chicago/validation_report.json`.
- PRD "≥ 15% wait reduction" metric not published (per-agent wait accounting now implemented in `ml/env/traffic_sim.py`; results pending).
- CV accuracy figures (91.4%/94.8%/97.5% in `docs/results.md`) are unverified; YOLO/DeepSORT/U-Net/Mask R-CNN weights not in the repo.
- CUDA ONNX execution provider unfinished; GPU inference not verified end-to-end.
- RL benchmark harness (`benchmark.py`, `configs.yaml`, `eval/report.py`) referenced by `docs/TRD.md` does not exist.
- Intersection counts disagree between `docs/TRD.md` and `docs/NEXUS-SIM-DOCUMENTATION.md` (Chicago 3,709 vs 5,217; Ahmedabad 25 vs 15,724) — TBD.

No metrics were fabricated; unknown values are marked TBD.

## Build & setup

Prerequisites: GCC 11+/MinGW-w64 (C++17), CMake ≥ 3.25, Ninja, Python 3.11+, Node.js 20+.

```bash
# C++ engine (Unix example; Windows uses run.bat)
cd engine && mkdir -p build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTING=ON
cmake --build .
cd ../..
./engine/build/engine --city piedmont --agents 500 --duration 5 --fast

# ML (from repo root)
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r ml/requirements.txt
python -m train.train --city toy --episodes 500

# Dashboard
cd dashboard && npm install && npm run dev
```

Windows one-click: `run.bat` (builds engine, starts engine + dashboard). Full stack: `run_full_system.bat` (gateway :8000 + sidecars).

> Build notes for this environment: `make` and `ninja` are not installed, and OpenSSL is not present, so `make build` (which hardcodes `-G Ninja` and requires OpenSSL) cannot run as documented. Use `cmake -G "MinGW Makefiles"` instead; a full `FetchContent` configure may take several minutes on the first run. Prebuilt `build/engine.exe` exists from a prior build.

## Documentation

See `docs/` for the full specification:
- `docs/README.md` — documentation index
- `docs/PRD.md` — product requirements (source of record)
- `docs/TRD.md` — technical requirements (source of record)
- `docs/TECH_STACK.md` — technology stack
- `docs/NEXUS-SIM-DOCUMENTATION.md` — consolidated master document
- `docs/RL_DOCUMENTATION.md`, `docs/CV_DOCUMENTATION.md`, `docs/NLP_DOCUMENTATION.md`, `docs/SOFT_COMPUTING_DOCUMENTATION.md` — per-subject documentation
- `docs/graph_schema.md`, `docs/od_matrix_schema.md` — data schemas
- `docs/e2e_checklist.md` — end-to-end verification checklist
- `docs/BACKLOG.md` — phase progress
- `docs/evidence/` — verification measurements

## Non-goals

NexusSim does not control real traffic signal hardware, provide live city monitoring, require proprietary data, work as an end-user navigation app, or scrape the Google Maps traffic layer (ToS-violating).
