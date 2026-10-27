# 00_overview.md — Vision, Scope, Goals, Non-Goals, Glossary, Assumptions

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Vision](#1-vision)
2. [Scope](#2-scope)
3. [Goals](#3-goals)
4. [Non-Goals](#4-non-goals)
5. [Glossary](#5-glossary)
6. [Assumptions](#6-assumptions)

---

## 1. Vision

NexusSim currently simulates urban traffic with a high-performance C++17 engine, a React dashboard, and a 48-algorithm portfolio across RL, CV, NLP, and Soft Computing. This revamp introduces an **NLP-driven chatbot interface** as a first-class interaction layer on the dashboard, enabling two distinct roles:

- **Driver** — requests personalized routes with natural-language constraints (avoid/via junctions); route updates dynamically on the map.
- **Administrator** — views system-wide efficiency metrics and issues scenario modulation commands (construction, congestion, capacity changes) that propagate to the simulation and all affected drivers' routes.

The chatbot is accessible via a dedicated button on the existing dashboard, preserving all current metrics panels while adding conversational control.

---

## 2. Scope

### In Scope
| Area | Description |
|------|-------------|
| **Dashboard Integration** | New chatbot button/toolbar entry; role selection modal on first open; chat panel with streaming responses |
| **Driver Role** | Route requests (best/fastest/shortest); `avoid` and `via` node constraints; dynamic reroute display on map |
| **Administrator Role** | Dashboard metrics retention; scenario commands (capacity reduction, congestion weights, incidents); audit log |
| **NLP Layer** | Intent taxonomy per role; entity extraction (junctions, roads, severity, time); ambiguity clarification dialogs; role guardrails |
| **Routing Engine** | A*/Dijkstra with dynamic edge weights; constraint handling (must-visit, must-avoid); reroute triggers |
| **Simulation Engine** | `apply_scenario()` mutation API; capacity/congestion parameter updates; incident expiry; WebSocket propagation |
| **Real-Time Channel** | WebSocket (port 9001) for route updates, scenario broadcasts, agent positions |
| **Auth & Roles** | JWT-based auth (existing gateway); role matrix (driver vs. admin); per-route authorization |

### Out of Scope (Non-Goals)
| Item | Reason |
|------|--------|
| Turn-by-turn voice navigation | Driver role is route visualization only |
| Multi-vehicle fleet management | Single-vehicle driver scope |
| Real-world map tile providers (Mapbox/TomTom) | Existing OSM/Leaflet stack retained |
| Mobile app / native clients | Dashboard is web-only |
| Historical replay / time-travel | Current simulation is forward-only |
| Multi-language NLP | English only for v1 |
| Edge/cloud deployment | Local/docker-compose only |

---

## 3. Goals

| ID | Goal | Success Criterion |
|----|------|-------------------|
| G1 | Driver can request a route via chat and see it on the map within 2 s | p95 ≤ 2 s from utterance to route polyline render |
| G2 | Driver can say "avoid Junction A, go through Junction B" and route recalculates | Constraint satisfaction verified on graph; map updates in < 1 s |
| G3 | Admin can say "bridge at Junction A under construction, heavy traffic" and simulation mutates | Edge capacity reduced by configurable severity; all affected drivers reroute |
| G4 | Role guardrails prevent privilege escalation | Driver cannot invoke scenario mutations; admin cannot request personal routes |
| G5 | Existing dashboard metrics (Gini, wait time, throughput) remain accessible and accurate | No regression in TRD §4.4 metrics panels |
| G6 | All NLP interactions are auditable | Admin scenario commands logged with user, timestamp, parsed spec, before/after state |

---

## 4. Non-Goals

See [Scope](#2-scope) "Out of Scope" table. Additionally:
- **No changes** to the C++ engine's core tick loop, spatial index, or IDM car-following.
- **No changes** to the 48-algorithm portfolio, RL training pipeline, or CV virtual camera.
- **No new data stores** beyond in-memory state + optional audit log append-only file.

---

## 5. Glossary

| Term | Definition |
|------|------------|
| **Agent** | A simulated vehicle/pedestrian in the C++ engine (SoA layout, IDM dynamics) |
| **Junction / Node** | Graph vertex (`graph.json` nodes) representing an intersection |
| **Road / Edge** | Graph edge (`graph.json` edges) with length, lanes, capacity |
| **Zone** | Equity zone (census/building-density proxy) for Gini calculation |
| **OD Matrix** | Origin-Destination demand matrix (`od_matrix.json`) driving spawn rates |
| **Scenario** | A mutable overlay on the base simulation: capacity multipliers, congestion weights, incidents |
| **Intent** | Classified user goal (e.g., `route_request`, `avoid_node`, `scenario_update`) |
| **Entity** | Extracted parameter (junction_id, road_id, severity, duration, time_window) |
| **Reroute Trigger** | Event causing path recomputation: scenario change, incident expiry, driver constraint |
| **Guardrail** | Authorization check blocking cross-role intent execution |

---

## 6. Assumptions

| # | Assumption | Verification Needed |
|---|------------|---------------------|
| A1 | Current engine WebSocket (port 9001) broadcasts `agents[]` with `path` (node ID array) per agent | Confirm `Agent` struct in `useWebSocket.ts` includes `path` |
| A2 | Engine accepts inbound `incident` messages (TR-ENG-13) and applies per-edge speed/capacity multipliers | Verify `apply_incident()` in `Simulation.h` |
| A3 | Gateway (port 8000) proxies `/api/chat` and `/api/incident` to NLP sidecar (port 9004) | Confirm `gateway/server.py` routes |
| A4 | Dashboard already has JWT auth via gateway (`/api/auth/login`) | Verify `gateway/auth.py` roles: `admin`, `viewer` |
| A5 | Graph (`graph.json`) includes edge names for gazetteer lookup | Check `pipeline/src/clean.py` output |
| A6 | Routing in engine uses A* with stochastic diversity (`compute_path_stochastic`) | Verify `Pathfinder.h` |
| A7 | Dashboard map (Leaflet) can render per-agent route polylines dynamically | Confirm `Map.tsx` path rendering logic |
| A8 | NLP sidecar (`chat_service.py`) already has rule-based intent classifier + gazetteer parser | Confirm `ml/nlp/incident_parser.py` |
| A9 | No existing role concept for "driver" — must be added to auth | Check `gateway/auth.py` USERS table |
| A10 | Simulation runs single-city, single-instance per engine process | Confirm `gateway/server.py` SIMULATIONS registry |

> **Note:** Assumptions A1–A10 must be verified in the codebase before implementation begins. This planning session cannot read live code beyond what was provided.