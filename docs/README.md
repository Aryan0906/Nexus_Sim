# NexusSim Documentation Index

Welcome to the documentation suite for **NexusSim** — a high-performance urban traffic simulation and multi-agent AI research platform integrating C++ simulation, Multi-Agent Reinforcement Learning (MARL), Soft Computing, Computer Vision, and Natural Language Processing.

---

## 1. System Architecture & Requirements

- **[PRD — Product Requirements Document](PRD.md)**: Product vision, user goals, feature requirements, and success metrics. Source of record.
- **[TRD — Technical Requirements Document](TRD.md)**: Technical specifications, interface contracts, performance bounds, and subsystem architecture. Source of record.
- **[Tech Stack Specification](TECH_STACK.md)**: Languages, frameworks, runtime libraries, and sidecar architecture.
- **[Team Implementation Plan](TEAM_IMPLEMENTATION_PLAN.md)**: Multi-phase engineering roadmap (Phases 0–36) and integration checkpoints.
- **[End-to-End Smoke Checklist](e2e_checklist.md)**: Integration test checklist run across pipeline, engine, sidecars, and dashboard.

---

## 2. Four-Subject Academic & Algorithm Documentation

- **[Reinforcement Learning (RL)](RL_DOCUMENTATION.md)**: Decentralized MAPPO, observation/action/reward formulation, training pipeline, 12-algorithm inventory, ONNX deployment, evaluation results and gaps.
- **[Soft Computing (SC)](SOFT_COMPUTING_DOCUMENTATION.md)**: GA calibration, Mamdani/Type-2 fuzzy signal controllers, metaheuristics, swarm, ANFIS, GP, NSGA-II.
- **[Computer Vision (CV)](CV_DOCUMENTATION.md)**: Congestion tile classification, synthetic virtual camera, tracking/segmentation inventory, integration and limitations.
- **[Natural Language Processing (NLP)](NLP_DOCUMENTATION.md)**: Rule-based metrics chat, incident parser (RapidFuzz gazetteer), sentiment/feedback, engine WebSocket client, integration and limitations.

---

## 3. Results, Benchmarks & Operational Memory

- **[Master Results & Algorithm Matrix](results.md)**: Consolidated benchmarks, calibration ablations, multi-city MARL gains, and the algorithm portfolio matrix. Contains both measured and catalog/unverified values — flagged per row.
- **[AI-Mode Stress Test Report](AI_STRESS_REPORT.md)**: ONNX inference latency and tick-throughput measurements under 20,000 agents.
- **[Project Backlog & Technical Debt](BACKLOG.md)**: Phase completion statuses (Phases 0–36) and prioritized open items.
- **[Future Planning Roadmap](futureplanning.md)**: Production roadmap — dynamic city onboarding, multi-tenancy, simulation-as-a-service, what-if scenarios, federated learning, emissions, collaborative planning. Planning-stage, not committed scope.
- **[Master Documentation](NEXUS-SIM-DOCUMENTATION.md)**: Consolidated master document (verified against the working tree 2026-10-24).

---

## 4. Data Schemas

- **[Graph Schema](graph_schema.md)**: JSON structure for `data/<city>/graph.json` (nodes, edges, zones).
- **[OD Matrix Schema](od_matrix_schema.md)**: Specification for `data/<city>/od_matrix.json` (origin–destination demand).

---

## 5. API Verification (Postman + `api_check.py`)

- **[Postman Collection](postman/)**: `NexusSim API Tests` collection covering Gateway (:8000), Virtual Camera (:9003), NLP Chat (:9004), Event Bus (:9005), Algo Explorer (:9006), Dashboard (:3000), and edge cases.
- **[API Verification Script](postman/api_check.py)**: Standalone Python verifier (`requests` + raw-socket WS client) covering HTTP checks plus the WebSocket cases Postman cannot run.

---

> **Note on deleted/superseded docs:** `USER_STORIES.md` (users are covered in `PRD.md §4`), `TEST_LOG.md` (historical API run log), `SESSION_MEMORY.md` (historical session log), and the HTML/PDF audit artifacts were removed as redundant with the source-of-record documents above. Subject documentation that was previously referenced but missing (`RL_DOCUMENTATION.md`, `CV_DOCUMENTATION.md`, `NLP_DOCUMENTATION.md`, `SOFT_COMPUTING_DOCUMENTATION.md`) and `TECH_STACK.md` have been added.
