# NexusSim Documentation Index

Welcome to the comprehensive documentation suite for **NexusSim** — a high-performance urban traffic simulation and multi-agent AI research platform integrating C++ simulation, Multi-Agent Reinforcement Learning (MARL), Soft Computing, Computer Vision, and Natural Language Processing.

---

## 1. System Architecture & Requirements

- **[PRD — Product Requirements Document](PRD.md)**: Product vision, user goals, feature requirements, and success metrics.
- **[TRD — Technical Requirements Document](TRD.md)**: Technical specifications, interface contracts, performance bounds, and subsystem architecture.
- **[Team Implementation Plan](TEAM_IMPLEMENTATION_PLAN.md)**: Multi-phase engineering roadmap spanning foundation through the 48-algorithm (12 per subject) multi-subject tracks.
- **[Tech Stack Specification](TECH_STACK.md)**: Detailed breakdown of languages, frameworks, runtime libraries, and sidecar architecture.
- **[User Stories](USER_STORIES.md)**: Stakeholder user stories across city planners, traffic engineers, and academic researchers.
- **[End-to-End Smoke Checklist](e2e_checklist.md)**: Integration test checklist run across pipeline, engine, sidecars, and dashboard.

---

## 2. Four-Subject Academic & Algorithm Documentation

- **[Reinforcement Learning (RL) Documentation](RL_DOCUMENTATION.md)**: Decentralized MAPPO, observation/action formulations, reward engineering (pressure + Gini equity), and 12-algorithm RL inventory benchmarks.
- **[Soft Computing (SC) Documentation](SOFT_COMPUTING_DOCUMENTATION.md)**: GA automated calibration, Mamdani and Interval Type-2 fuzzy signal controllers, metaheuristics (PSO, SA, CMA-ES), swarm intelligence (ACO, ABC), ANFIS, GP, and NSGA-II Pareto optimization.
- **[Computer Vision (CV) Documentation](CV_DOCUMENTATION.md)**: Real-world congestion tile classification, synthetic virtual camera sidecar, DeepSORT tracking, U-Net road segmentation, Mask R-CNN, optical flow, and anomaly detection.
- **[Natural Language Processing (NLP) Documentation](NLP_DOCUMENTATION.md)**: Rule-based & LLM metrics chat service, RapidFuzz gazetteer incident parser, sentiment feed, NER extraction, coreference resolution, and RDF knowledge graph.

---

## 3. Results, Benchmarks & Operational Memory

- **[Master Results & Algorithm Matrix](results.md)**: Consolidated benchmarks, calibration ablations, multi-city MARL gains (+26.3% on Chicago), and the 48-algorithm portfolio matrix.
- **[AI-Mode Stress Test Report](AI_STRESS_REPORT.md)**: Phase 8.8 stress-test report evaluating ONNX inference latency (p95 = 0.04-0.13 ms measured by `bench_inference`) and tick throughput under 20,000 active agents (8.6-9.2 ms avg / 12-16 ms p95 after the P2 spatial-grid rewrite).
- **[Project Backlog & Technical Debt](BACKLOG.md)**: Phase completion statuses (Phases 0–36) and prioritized active backlogs.
- **[Future Planning Roadmap](futureplanning.md)**: Production roadmap — dynamic OSM city onboarding, multi-tenant workspaces, simulation-as-a-service, what-if scenarios, real-time ingestion, algorithm marketplace, federated learning, multi-modal, disaster response, emissions, and collaboration.
- **[Cross-Session Memory Log](SESSION_MEMORY.md)**: Historical session log preserving context, checkpoints, architectural decisions, and run records across sessions.
- **[Academic Synopsis Generation Context](SYNOPSIS_CONTEXT.md)**: Single source of truth containing verified system facts for project reports, DFDs, ER diagrams, and project guides.

---

## 5. Audit Evidence (2026-10)

Reproducible artifacts for the integrity/optimization pass. Each file contains
the commands, raw measurements, and explicit "not claimed" caveats.

- **[P2 — 20k tick performance](evidence/p2_performance.md)**: uniform-grid + capsule rewrite; measured 8.6–9.2 ms avg / 12–16 ms p95 at 20,000 agents.
- **[P3 — benchmark provenance](evidence/p3_benchmark_provenance.md)**: fabricated `mean_wait` values removed; catalog vs. measured labels added.
- **[P4 — fuzzy policy wiring](evidence/p4_fuzzy_wiring.md)**: Mamdani/Type-2 policies now genuinely extend green; regression tests + 20k mode comparison.
- **[P5 — dashboard & providers](evidence/p5_dashboard_and_providers.md)**: AlgoExplorer mounted, `tick` consumed, CUDA-training + provider selection verified.
- **[P8 — ONNX provider](evidence/p8_onnx_provider.md)**: provider plumbing complete on CPU; CUDA EP experiment time-boxed and documented as unfinished.

> Note: `docs/e2e_checklist.md` also carries an audit summary of the stale
> test-binary trap (`ENABLE_TESTING=OFF`) and the fixtures affected.

---

## 4. Data Schemas

- **[Graph Schema](graph_schema.md)**: JSON structure defining nodes, edges, lanes, and traffic signal controller definitions.
- **[OD Matrix Schema](od_matrix_schema.md)**: Origin-Destination matrix specification for real-world Socrata feeds and gravity-density proxy distributions.

---

## 6. API Verification (Postman + `api_check.py`)

- **[Postman Collection](postman/)**: `NexusSim API Tests` collection covering Gateway (`:8000`), Virtual Camera (`:9003`), NLP Chat (`:9004`), Event Bus (`:9005`), Algo Explorer (`:9006`), Dashboard (`:3000`), Engine direct (`:9001`), and edge cases — 27 requests (A1–H27) with Postman test scripts.
- **[API Verification Script](postman/api_check.py)**: standalone Python verifier (`requests` + raw-socket WS client) covering all 22 HTTP checks plus the 4 WebSocket cases Postman cannot run.
- **[Test Log](TEST_LOG.md)**: Run history — Run 1 (21/24), Run 2 post-fix (24/24), Run 3 live `api_check.py` verification (24/24, 0 failures). WebSocket cases (A7, A8, D18, G24) are skipped by Postman and verified by `api_check.py` instead.
