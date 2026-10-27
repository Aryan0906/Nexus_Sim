# 01_current_system_analysis.md — Existing Architecture Assessment & Gaps

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Architecture Summary](#1-architecture-summary)
2. [Component Inventory](#2-component-inventory)
3. [Data Flow](#3-data-flow)
4. [Existing NLP Capabilities](#4-existing-nlp-capabilities)
5. [Routing & Pathfinding](#5-routing--pathfinding)
6. [Simulation Mutation APIs](#6-simulation-mutation-apis)
7. [Dashboard & UI](#7-dashboard--ui)
8. [Authentication & Authorization](#8-authentication--authorization)
9. [Identified Gaps](#9-identified-gaps)
10. [Verification Checklist](#10-verification-checklist)

---

## 1. Architecture Summary

NexusSim follows a **sidecar architecture** with hard interface boundaries:

```
┌──────────────────┐     graph.json      ┌──────────────────┐
│  DATA PIPELINE   │ ─────────────────►  │   C++ ENGINE     │
│  (Python/osmnx)  │                     │  Simulation loop │
└──────────────────┘                     └────────┬─────────┘
                                                   │ binary delta
        ┌──────────────────┐     ONNX model       │ WebSocket
        │   ML PIPELINE    │ ──────────────────►  ┘
        │  (PyTorch/MAPPO) │       ring buffer
        └──────────────────┘
                       ┌──────────────────┐
                       │   DASHBOARD      │
                       │  React + Leaflet │
                       └──────────────────┘
```

**Key Ports:**
| Subsystem | Port | Protocol | Purpose |
|-----------|------|----------|---------|
| C++ Engine | 9001 | WebSocket | State frames, control messages |
| Dashboard | 3000 | HTTP/WS | React app, map, panels |
| Virtual Camera | 9003 | HTTP/WS | Annotated frames, blob counts |
| NLP Chat/Incident | 9004 | REST | `/chat`, `/incident`, `/feedback` |
| Event Bus | 9005 | WS/Async | Pub/Sub (`cv.anomaly`, `nlp.incident`, `sc.adaptation`) |
| Algo Explorer | 9006 | REST | Algorithm catalog (48 algorithms) |
| Gateway | 8000 | HTTPS/WS | Unified entry point, auth, SaaS APIs |

---

## 2. Component Inventory

### 2.1 C++ Engine (`engine/`)
| Module | File | Status | Notes |
|--------|------|--------|-------|
| Graph loading | `src/graph/GraphLoader.cpp` | DONE | Loads `graph.json`, adjacency list |
| Agents (IDM) | `src/agents/IDM.h` | DONE | Heterogeneous types, chaos coefficient |
| Spatial index | `src/spatial/UniformGrid.h` | DONE | Counting-sort O(N) proximity |
| Pathfinding | `src/agents/Pathfinder.h` | DONE | A* + stochastic diversity |
| Signal policies | `src/agent/SignalPolicy.h` | DONE | Pluggable: Webster, Fuzzy, RL, Type-2 |
| ONNX inference | `src/inference/InferenceEngine.h` | DONE | Batched, off hot path, p95 ≤ 8 ms |
| WebSocket server | `src/network/WebSocketServer.h` | DONE | uWebSockets, JSON frames |
| Incident apply | `src/agent/Simulation.h` | PLANNED | `apply_incident(edges, severity, duration_s)` |

### 2.2 Data Pipeline (`pipeline/`)
| Stage | Script | Output |
|-------|--------|--------|
| OSM download | `download.py` | Raw `.osm.pbf` |
| Clean + SCC | `clean.py` | Cleaned graph |
| Lane inference | `lanes.py` | Per-edge lanes + confidence |
| Zone tagging | `zones.py` | `zone_id` per node |
| Export | `export.py` | `graph.json` |
| OD matrix | `od_matrix.py` / `od_proxy.py` | `od_matrix.json` (real or proxy) |
| Validation | `validate.py` | MAPE checkpoint (≤ 25%) |
| GA calibration | `optimize_calibration.py` | `ga_calibration_report.json` |
| CV congestion | `cv_congestion.py` | `cv_congestion.json` (Mapbox/TomTom) |

### 2.3 ML Pipeline (`ml/`)
| Component | Path | Status |
|-----------|------|--------|
| Gym env | `ml/env/` | DONE |
| MAPPO trainer | `ml/train/train.py` | DONE |
| ONNX export | `ml/export/export_onnx.py` | DONE |
| Virtual camera | `ml/cv/virtual_camera.py` | DONE (port 9003) |
| NLP chat | `ml/nlp/chat_service.py` | DONE (port 9004) |
| Incident parser | `ml/nlp/incident_parser.py` | DONE |
| 12 NLP algos | `ml/nlp/*.py` | DONE (Phases 16, 17, 31–33) |

### 2.4 Dashboard (`dashboard/`)
| Panel | Component | Tab |
|-------|-----------|-----|
| Metrics | `MetricsPanel.tsx` | Metrics |
| Equity | `EquityOverlay.tsx` | Metrics / Equity view |
| CV Overlay | `CongestionCVOverlay.tsx` | Vision |
| Virtual Camera | `VirtualCameraPanel.tsx` | Vision |
| Chat | `ChatPanel.tsx` | Chat |
| Incident Report | `IncidentReportPanel.tsx` | Chat |
| Algo Explorer | `AlgoExplorerPanel.tsx` | Algos |
| Emissions | `EmissionsPanel.tsx` | Carbon |
| NLP Console | `NLPCommandConsole.tsx` | Top bar (always visible) |
| Policy Toggle | `PolicyComparisonPanel.tsx` | Metrics |

---

## 3. Data Flow

### 3.1 Simulation Tick (Engine → Dashboard)
```
Engine.tick() 
  → compute agent positions, signals, metrics
  → broadcast_state() JSON frame
  → WebSocket (port 9001)
  → Gateway proxies /ws
  → Dashboard useWebSocket hook parses
  → Zustand store updates
  → Map.tsx renders agents, routes, equity overlay
```

**Broadcast Frame (additive, per NFR-5):**
```json
{
  "tick": 1234,
  "agents": [{ "id": 0, "lat": 0.0, "lon": 0.0, "heading": 0.0, "type": 0, "speed": 12.5, "path": [1,5,9,14] }],
  "metrics": { "avg_speed": 32.4, "active_agents": 542, "avg_wait_time": 18.7, "gini_coefficient": 0.32 },
  "zone_metrics": [{ "zone_id": 0, "wait_time": 15.2 }, ...],
  "signals": [{ "id": 0, "phase": 2, "state": "green" }],
  "mode": "fuzzy",
  "incidents": [{ "edges": [42, 43], "severity": 0.7, "remaining_s": 45.0 }]
}
```

### 3.2 Control Messages (Dashboard → Engine)
| Message | Purpose | Handler |
|---------|---------|---------|
| `{"type":"bounds", ...}` | Viewport LOD culling | Engine |
| `{"type":"city", "city":"chicago"}` | Start simulation | Engine (single-sim lock) |
| `{"type":"pause"}` / `{"type":"resume"}` | Freeze/continue | Engine |
| `{"type":"restart"}` | Reload same city | Engine |
| `{"type":"reset"}` | Stop, unlock city select | Engine |
| `{"type":"policy_switch", "policy":"rl", "intersection_id":null}` | Hot-swap signal policy | Engine |
| `{"type":"incident", "edges":[42], "severity":0.5, "duration_s":30}` | Apply incident | Engine (`apply_incident`) |

### 3.3 NLP Sidecar Flow
```
Dashboard ChatPanel → POST /api/chat (gateway:8000) 
  → proxy to NLP:9004/chat
  → classify_intent_and_answer(query, city)
  → returns { intent, answer, confidence, handler }
  → Dashboard renders bot response

Dashboard IncidentReportPanel → POST /api/incident
  → proxy to NLP:9004/incident
  → IncidentParser.parse(text) → IncidentSpec { edges, severity, duration_s }
  → forwards {"type":"incident", ...} to Engine WS
  → Engine applies, broadcasts incidents[]
  → Dashboard updates active incidents list
```

---

## 4. Existing NLP Capabilities

### 4.1 Chat Service (`ml/nlp/chat_service.py`)
- **Rule-based intent classifier** (regex over fixed set): `worst_zone`, `avg_speed`, `active_agents`, `gini_explain`, `compare_policy`, `incident_status`
- **Optional LLM tool-calling fallback** (requires API key; graceful fallback to rule-based)
- **Endpoint:** `POST /chat` with `{ query, city }`
- **Response:** `{ intent, answer, confidence, handler }`
- **Accuracy:** 98.2% on held-out set (rule-based), ~850 ms LLM path

### 4.2 Incident Parser (`ml/nlp/incident_parser.py`)
- **Gazetteer** built from `graph.json` edge names at startup
- **Fuzzy matching** via `rapidfuzz` (Levenshtein) for misspellings
- **Vocabulary:** incident types (`accident`, `construction`, `closure`, `event`), severity keywords
- **Output:** `IncidentSpec { type, edges[], severity, duration_s }`
- **Endpoint:** `POST /incident` → forwards to engine WS

### 4.3 NLP Algorithm Inventory (12 algorithms)
| ID | Algorithm | Module | Capability |
|----|-----------|--------|------------|
| NLP-1 | Regex Intent Classifier | `chat_service.py` | Fast deterministic metrics Q&A |
| NLP-2 | LLM Tool-Calling Fallback | `chat_service.py` | Multi-turn reasoning |
| NLP-3 | RapidFuzz Gazetteer | `incident_parser.py` | Street name → edge resolution |
| NLP-4 | Sentiment Analyzer | `sentiment_analyzer.py` | Commuter polarity/subjectivity |
| NLP-5 | Naive Bayes Classifier | `naive_bayes_classifier.py` | Probabilistic intent |
| NLP-6 | NER Extractor | `ner_extractor.py` | Location/corridor/severity spans |
| NLP-7 | Coreference Resolver | `coref_resolver.py` | Pronoun/antecedent linking |
| NLP-8 | TextRank Summarizer | `summarizer.py` | Multi-incident executive summary |
| NLP-9 | Extractive QA Engine | `qa_engine.py` | Contextual passage search |
| NLP-10 | RDF Knowledge Graph | `knowledge_graph.py` | Semantic triple store |
| NLP-11 | Traffic Event Extractor | `event_extractor.py` | Structured event tuples |
| NLP-12 | Interactive Command Console | `NLPCommandConsole.tsx` | Real-time WS mutations |

---

## 5. Routing & Pathfinding

### 5.1 Current Engine Routing (`Pathfinder.h`)
- **Algorithm:** A* with precomputed Euclidean heuristic (node-to-node)
- **Stochastic variant:** `compute_path_stochastic()` adds noise to edge costs for route diversity
- **Edge cost model:** `length / (speed_limit * lanes)` + congestion penalty
- **Per-agent path:** Stored as `vector<int64_t> path` (node IDs) in `Agent` struct
- **Recomputation:** On incident application, affected agents recompute via stochastic pathfinder

### 5.2 Dashboard Route Rendering (`Map.tsx`)
- **Full planned route:** Dashed polyline (all nodes in `agent.path`)
- **Remaining route:** Solid cyan polyline (from current `edge_idx` to destination)
- **Origin/Destination pins:** Green/red circle markers with popups
- **Path modes:** All Routes / Selected / Trails / Off (segmented control)
- **LOD culling:** `ViewportBoundsSender` sends map bounds to engine

---

## 6. Simulation Mutation APIs

### 6.1 Engine `apply_incident()` (TR-ENG-13, Phase 17.3)
```cpp
void apply_incident(
    const std::vector<int64_t>& edges,
    float severity,           // 0.0–1.0
    float duration_s          // seconds of sim_time_
);
```
- Applies temporary per-edge multipliers: `speed *= (1.0 - severity)`, `capacity *= (1.0 - severity)`
- Expiry tracked via `sim_time_`; removed automatically after `duration_s`
- Reuses `Pathfinder`'s stochastic edge-cost mechanism
- Broadcasts `incidents[]` in state frame (additive field)

### 6.2 Gateway Scenario Fork (`/api/scenarios`)
- Creates new simulation process with mutated config
- Mutations: `signal_mode`, `demand_scale`, `incident_text`, `incident_edge_id`
- Comparison endpoint: `/api/simulations/{sim_id}/compare/{scenario_id}`

---

## 7. Dashboard & UI

### 7.1 Layout (`Map.tsx` + `RightDock.tsx`)
- **Left:** NLP Command Console (top bar, always visible when connected)
- **Right:** Collapsible Analytics Dock with 6 tabs: Metrics, Vision, Chat, Algos, Carbon, All
- **Map:** Leaflet + OSM tiles, GraphBoundsFitter auto-fits to city graph
- **Agent selection:** Click agent → inspector HUD with route highlights

### 7.2 Existing Chat Panel (`ChatPanel.tsx`)
- REST calls to `/api/chat` (gateway) with fallback to direct NLP
- Displays intent badge on bot responses
- Offline fallback mode when NLP service unreachable

### 7.3 NLP Command Console (`NLPCommandConsole.tsx`)
- **Purpose:** Direct engine mutations via structured commands (not chat)
- **Presets:** "set speed factor 0.8", "increase chaos 0.3", "set green time 45s"
- **Sends:** `{"type":"nlp_command", "command": "..."}` via engine WS
- **Note:** This is **not** the chatbot — it's a developer/admin console for simulation parameters

---

## 8. Authentication & Authorization

### 8.1 Current Auth (`gateway/auth.py`)
- **JWT** (HS256, 60-min expiry, secret via env)
- **Users (in-memory):**
  - `admin` — role `admin`, workspaces `ws_default`, `ws_acme`
  - `viewer` — role `viewer`, workspace `ws_default`
- **Roles:** `admin`, `editor`, `viewer`
- **Dependencies:**
  - `require_workspace_access(ws)` — workspace membership
  - `require_role([...])` — role check

### 8.2 Protected Endpoints
| Endpoint | Auth | Role Required |
|----------|------|---------------|
| `/api/simulations` POST | JWT + workspace | any authenticated |
| `/api/scenarios` POST | JWT + workspace | any authenticated |
| `/api/algo/register` | JWT | `admin` or `editor` |
| `/api/algo/validate` | JWT | `admin` |
| `/api/ingest/*` | JWT | `admin` or `editor` |
| `/api/platform/rate-limit` | JWT | `admin` |

### 8.3 Gap: No "Driver" Role
- Current roles are workspace-oriented (admin/editor/viewer)
- **Driver role does not exist** — must be added for chatbot role separation
- Driver should have: read own simulation, request routes, NO scenario mutation

---

## 9. Identified Gaps

| Gap ID | Area | Description | Priority |
|--------|------|-------------|----------|
| GAP-01 | Auth | No "driver" role; no per-agent/vehicle authorization | Critical |
| GAP-02 | NLP | Chat service only answers metrics queries; no route computation | Critical |
| GAP-03 | NLP | No intent taxonomy for driver constraints (`avoid_node`, `via_node`, `route_request`) | Critical |
| GAP-04 | Engine | No `apply_scenario()` for admin capacity/congestion mutations (only `incident`) | Critical |
| GAP-05 | Engine | No driver-specific route request API; routes computed internally on spawn | Critical |
| GAP-06 | Dashboard | No chatbot button/panel; NLPCommandConsole is dev-only | Critical |
| GAP-07 | Dashboard | No role selection modal on chatbot entry | Critical |
| GAP-08 | Routing | No constraint-aware pathfinding (must-visit/must-avoid nodes) | High |
| GAP-09 | Routing | No dynamic reroute push to specific driver agents | High |
| GAP-10 | Real-time | No WebSocket channel for driver-specific route updates | High |
| GAP-11 | Audit | No audit log for admin scenario commands | Medium |
| GAP-12 | NLP | No ambiguity clarification dialog (e.g., "Which Junction A?") | Medium |
| GAP-13 | Guardrails | No intent-level authorization (driver vs admin) | Critical |

---

## 10. Verification Checklist

> **Must be verified in codebase before implementation** (this planning session cannot read live code beyond provided files).

| # | Item | File/Location | Expected |
|---|------|---------------|----------|
| V1 | Agent struct has `path` field | `engine/src/agents/Agent.h` | `vector<int64_t> path` |
| V2 | Engine accepts `incident` WS message | `engine/src/network/WebSocketServer.h` | Dispatch to `Simulation::apply_incident` |
| V3 | `apply_incident` implementation | `engine/src/agent/Simulation.h` | Per-edge multipliers + expiry |
| V4 | Gateway proxies `/api/chat` → NLP:9004 | `gateway/server.py` | Lines 994–1003 |
| V5 | Gateway proxies `/api/incident` → NLP:9004 | `gateway/server.py` | Lines 1000–1003 |
| V6 | NLP gazetteer uses `graph.json` edge names | `ml/nlp/incident_parser.py` | `IncidentParser.__init__` loads graph |
| V7 | Dashboard `useWebSocket` parses `incidents[]` | `dashboard/src/hooks/useWebSocket.ts` | Line 139: `data.incidents` |
| V8 | Dashboard renders agent routes from `path` | `dashboard/src/components/Map.tsx` | Lines 473–496, 518–586 |
| V9 | Auth has `admin`/`viewer` roles only | `gateway/auth.py` | Lines 28–39 |
| V10 | Engine `compute_path_stochastic` exists | `engine/src/agents/Pathfinder.h` | Stochastic edge cost variant |
| V11 | City graph has edge names for gazetteer | `pipeline/src/clean.py` / `export.py` | `edges[].name` field |
| V12 | Gateway SIMULATIONS registry is per-process | `gateway/server.py` | Lines 123–125, 436–450 |

> **Action:** Development team must confirm V1–V12 before Sprint 1 kickoff.