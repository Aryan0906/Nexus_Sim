# NexusSim — Technology Stack

**Status:** Active  
**Owner:** Vyom & Vatsal  
**Last Updated:** 2026-10  
**Source of truth:** verified against the working tree (`engine/`, `pipeline/`, `ml/`, `dashboard/`, `gateway/`).

This document lists the languages, frameworks, runtime libraries, and sidecar
architecture used by NexusSim. It is referenced by `docs/PRD.md` §6 and
`docs/TRD.md` §2 as the authoritative stack specification.

---

## 1. Summary by Subsystem

| Subsystem | Path | Language | Primary responsibility |
|-----------|------|----------|------------------------|
| Data pipeline | `pipeline/` | Python 3.11 | Downloads, cleans, enriches OSM networks; infers lanes, tags zones, builds OD matrices; exports `graph.json` + `od_matrix.json` |
| Simulation engine | `engine/` | C++17 | IDM car-following, A* routing, counting-sort uniform-grid proximity, signal policies, parallel ticks, ONNX inference, WebSocket server |
| ML / MARL training | `ml/train/`, `ml/algo/`, `ml/env/` | Python 3.11 + PyTorch | Gymnasium env, MAPPO trainer, 12-algorithm RL inventory, ONNX export |
| Computer Vision | `ml/cv/`, `pipeline/src/cv_congestion.py` | Python 3.11 + OpenCV | Congestion classification, synthetic/virtual camera sidecar |
| NLP | `ml/nlp/` | Python 3.11 + FastAPI | Metrics chat service, incident parser (port 9004) |
| Dashboard | `dashboard/` | React 19 + TypeScript + Vite | Leaflet map, metrics panel, efficiency/equity views, side panels |
| Gateway / sidecars | `gateway/`, `ml/sidecars/` | Python 3.11 | Unified API gateway (:8000), event bus (:9005), algo explorer (:9006) |

---

## 2. Engine — `engine/` (C++17)

| Dependency | Version | Purpose |
|------------|---------|---------|
| C++ | C++17 | Implementation language (`engine/CMakeLists.txt`) |
| CMake | ≥ 3.25 | Build system |
| Ninja | — | Preferred generator (Makefile hardcodes `-G Ninja`) |
| GoogleTest | 1.15.2 | Unit tests + benchmarks (`ENABLE_TESTING=ON`) |
| nlohmann/json | 3.12.0 | `graph.json` parsing |
| FlatBuffers | 23.5.26 | Agent-delta serialisation (`agent_delta.fbs`) |
| uWebSockets | 20.46.0 | WebSocket server (port 9001) |
| uSockets | 0.8.6 | WebSocket event loop |
| libuv | 1.48.0 | Event loop (Windows) |
| ZLib | 1.3.1 | Compression |
| OpenSSL | — | uSockets TLS / `wss://` support |
| ONNX Runtime | 1.24.1 | AI signal inference (CPU default; CUDA EP experimental, unfinished) |

Build modes:
- `cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTING=ON` then `cmake --build .`
- `ENABLE_ONNX=ON` (default) links ONNX Runtime; `ENABLE_ONNX=OFF` builds a stub so the engine runs without AI inference.

---

## 3. Pipeline — `pipeline/` (Python 3.11)

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Implementation language |
| osmnx | ≥ 1.9.0 | Download OSM networks |
| PyYAML | ≥ 6.0 | `cities.yaml` parsing |
| pytest | ≥ 7.0 | Tests |
| pyyaml | — | City registry |

Key stages: `download.py` → `clean.py` → `lanes.py` → `zones.py` → `export.py`.
OD stages: `download_od.py` → `od_matrix.py` (Socrata) / `od_proxy.py` (density fallback).
Validation & calibration: `validate.py`, `optimize_calibration.py` (GA).
CV: `cv_congestion.py` (real Mapbox/TomTom tile fetch when `MAPBOX_ACCESS_TOKEN` / `TOMTOM_API_KEY` is set; synthetic fallback otherwise).

---

## 4. ML — `ml/` (Python 3.11)

| Dependency | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Implementation language |
| PyTorch | 2.12.0 | Neural networks (CUDA wheel optional via `requirements-cuda.txt`) |
| Gymnasium | ≥ 1.0 | RL environment interface |
| MLflow | 3.x | Experiment tracking (SQLite URI `sqlite:///ml/mlflow.db`) |
| ONNX / ONNX Runtime | ≥ 1.15 / ≥ 1.18 | Policy export + inference |
| numpy | ≥ 1.26 | Arrays |
| FastAPI / uvicorn | — | Sidecar services |
| OpenCV | — | Computer vision |
| rapidfuzz | — | Incident street gazetteer |
| Stable-Baselines3 | — | DDPG/TD3/SAC continuous-control showcase (Pendulum-v1) |

Training entry points: `ml/train/train.py` (MAPPO), `ml/train/transfer.py`, `ml/train/evaluate.py`.
RL inventory: `ml/algo/value_based.py`, `ml/algo/policy_based.py`, `ml/algo/continuous_control.py`, `ml/algo/base_trainer.py`.

Device resolution: `--device auto|cpu|cuda:N`; env `NEXUS_DEVICE`, `NEXUS_TORCH_THREADS`.

---

## 5. Dashboard — `dashboard/` (React 19 + TypeScript)

| Dependency | Version | Purpose |
|------------|---------|---------|
| React / React DOM | ^19.2.7 | UI framework |
| Vite | ^8.1.1 | Build / dev server |
| TypeScript | ~6.0.2 | Type checking |
| Leaflet / react-leaflet | ^1.9.4 / ^5.0.0 | Map rendering |
| Recharts | ^3.10.1 | Charts |
| vitest | ^5.0.2 | Component tests |
| oxlint | ^1.71.0 | Linting |

Dev server: `npm run dev` (port 5173); production: `npm run build` (served on port 3000).

---

## 6. Sidecars & Ports (TR-6: independent processes)

| Service | Port | Protocol | Notes |
|---------|------|----------|-------|
| C++ Simulation Engine | 9001 | WebSocket | Broadcasts per-tick JSON state frame; accepts `city`, `bounds`, `policy_switch`, `incident`, `pause/resume` |
| Virtual Camera | 9003 | HTTP / WS | Annotated frames + vehicle counts |
| NLP Chat / Incidents | 9004 | HTTP / WS | `POST /chat`, `POST /incident`; WS client to engine 9001 caches live metrics |
| Event Bus | 9005 | WS / Async | Pub/sub (`cv.anomaly`, `nlp.incident`, `sc.adaptation`) |
| Algo Explorer | 9006 | REST | Algorithm catalogue |
| Unified Gateway | 8000 | HTTP / WS | Auth, workspaces, cities, simulations, scenarios (futureplanning) |
| Dashboard | 3000 / 5173 | HTTP | React frontend |

All sidecars run out of the C++ hot path and out of the frontend bundle. Broadcast
fields grow by addition only (NFR-5).

---

## 7. Data Sources

| Data | Source | Notes |
|------|--------|-------|
| Road network | OpenStreetMap via osmnx | Cleaned, largest SCC, lane-confidence scores |
| OD demand | Chicago Socrata TNP (dataset `m6dm-c72p`); density proxy for Paris/Ahmedabad | Real feed for Chicago only; proxy flagged `validation_safe: false` |
| Traffic tiles | Mapbox Traffic Tiles / TomTom Traffic Flow API | ToS-compliant; API key via env var, never committed |
| Ground truth | Chicago TNP trips (Uber/Lyft TNP; Uber Movement decommissioned 2023) | Validation corridor comparison |

---

## 8. Environments

| Env | Stack | Notes |
|-----|-------|-------|
| Windows dev | MSYS2 MinGW-w64, CMake ≥ 3.25, Ninja, Python 3.11+, Node 20+ | `run_full_system.bat` |
| Linux/macOS dev | GCC 11+/Clang 14+, CMake, Ninja, Python 3.11+, Node 20+ | `make` targets |
| CI | GitHub Actions `ubuntu-latest` | Build + lint + test all subsystems |
| Sidecars | Python 3.11 + FastAPI/OpenCV | Ports 9003–9006; separate venv deps |

---

## 9. Deviations from Documentation

- `docs/README.md` and PRD §6 reference `TECH_STACK.md`; this file was missing from the tree and is now provided.
- The ONNX Runtime CUDA package download was time-boxed and never completed end-to-end (`docs/evidence/p8_onnx_provider.md`); GPU inference is not a verified capability.
- `docs/RL_DOCUMENTATION.md`, `docs/CV_DOCUMENTATION.md`, `docs/NLP_DOCUMENTATION.md`, and `docs/SOFT_COMPUTING_DOCUMENTATION.md` are referenced by `docs/README.md` but were absent from the tree; subject-specific documentation should be added under `docs/`.
