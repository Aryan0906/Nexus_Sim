# 02_requirements.md — Functional & Non-Functional Requirements

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Requirement Format](#1-requirement-format)
2. [Driver Role Requirements](#2-driver-role-requirements)
3. [Administrator Role Requirements](#3-administrator-role-requirements)
4. [Chatbot/NLP Requirements](#4-chatbotnlp-requirements)
5. [Routing Engine Requirements](#5-routing-engine-requirements)
6. [Simulation Engine Requirements](#6-simulation-engine-requirements)
7. [Dashboard Requirements](#7-dashboard-requirements)
8. [Real-Time Communication Requirements](#8-real-time-communication-requirements)
9. [Security & Authorization Requirements](#9-security--authorization-requirements)
10. [Non-Functional Requirements](#10-non-functional-requirements)

---

## 1. Requirement Format

| Field | Description |
|-------|-------------|
| **ID** | Unique identifier: `FR-<domain>-<nn>` (functional) or `NFR-<domain>-<nn>` (non-functional) |
| **Description** | Testable statement of required behavior |
| **Priority** | Critical / High / Medium / Low |
| **Acceptance Criteria** | Verifiable conditions for Done |
| **Dependencies** | Other requirements or external systems |
| **Traceability** | Maps to PRD goals, TRD requirements, gaps |

---

## 2. Driver Role Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-DRV-01** | Driver can open chatbot and select "Driver" role | Critical | Role selection modal appears on first chatbot open; persists in session storage | FR-CHT-01, FR-SEC-01 | G1, GAP-06, GAP-07 |
| **FR-DRV-02** | Driver can request "best route" from current location to destination | Critical | Utterance "best route to downtown" → route computed and displayed on map within 2 s | FR-ROU-01, FR-CHT-02 | G1, GAP-02 |
| **FR-DRV-03** | Driver can specify destination by junction name, landmark, or node ID | Critical | "route to Junction 42", "route to City Hall" both resolve to node ID | FR-NLP-03, FR-NLP-04 | G1, GAP-03 |
| **FR-DRV-04** | Driver can add `avoid` constraint: "avoid Junction A" | Critical | Route recomputes excluding specified node(s); map updates < 1 s | FR-ROU-02, FR-ROU-03 | G2, GAP-03, GAP-08 |
| **FR-DRV-05** | Driver can add `via` constraint: "go through Junction B" | Critical | Route recomputes forcing passage through specified node(s); map updates < 1 s | FR-ROU-02, FR-ROU-03 | G2, GAP-03, GAP-08 |
| **FR-DRV-06** | Driver can combine constraints: "avoid A, via B, avoid C" | High | Multiple avoid/via nodes handled in single request; order preserved for via | FR-ROU-02, FR-ROU-03 | G2, GAP-08 |
| **FR-DRV-07** | Driver sees current route highlighted on map with ETA | Critical | Selected agent's remaining path rendered as solid polyline; ETA displayed | FR-DSH-01, FR-ROU-04 | G1 |
| **FR-DRV-08** | Driver receives reroute notification when scenario changes affect their route | High | Toast/message "Route updated due to construction at Junction A" + new polyline | FR-SIM-03, FR-RT-02 | G2, GAP-09, GAP-10 |
| **FR-DRV-09** | Driver can clear constraints and request fresh route | Medium | "clear constraints" or new route request resets avoid/via lists | FR-ROU-02 | G1 |
| **FR-DRV-10** | Driver cannot access admin intents (scenario mutation, system metrics) | Critical | Guardrail rejects `scenario_update`, `query_efficiency` with 403; logs attempt | FR-SEC-03, FR-NLP-06 | G4, GAP-13 |

---

## 3. Administrator Role Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-ADM-01** | Admin can open chatbot and select "Administrator" role | Critical | Role selection modal; persists in session storage | FR-CHT-01, FR-SEC-01 | G4, GAP-07 |
| **FR-ADM-02** | Admin sees all existing dashboard metrics (Gini, wait time, throughput, zone heatmap) | Critical | No regression in Metrics, Equity, Vision, Algos, Carbon tabs | FR-DSH-02 | G5 |
| **FR-ADM-03** | Admin can issue scenario modulation: "bridge at Junction A under construction, heavy traffic" | Critical | Parsed → capacity reduction on edges; severity 0.7; duration 3600 s; all affected drivers reroute | FR-NLP-05, FR-SIM-01, FR-ROU-05 | G3, GAP-04 |
| **FR-ADM-04** | Admin can specify severity: "light congestion", "heavy traffic", "full closure" | High | Maps to severity multipliers: 0.3, 0.7, 1.0 respectively | FR-NLP-04, FR-SIM-01 | G3 |
| **FR-ADM-05** | Admin can specify duration: "for 2 hours", "until 6 PM", "indefinite" | High | Parsed to `duration_s`; indefinite = no expiry | FR-NLP-04, FR-SIM-01 | G3 |
| **FR-ADM-06** | Admin can target corridor/road: "Main St between 1st and 5th Ave" | High | Gazetteer resolves to edge set; applied to all edges in corridor | FR-NLP-03, FR-SIM-01 | G3, GAP-04 |
| **FR-ADM-07** | Admin can query system efficiency: "what's the citywide average wait time?" | Medium | Returns current metrics from engine broadcast | FR-NLP-02, FR-RT-01 | G5 |
| **FR-ADM-08** | Admin can list active scenarios/incidents | Medium | "show active incidents" → reads `incidents[]` from broadcast | FR-NLP-02, FR-RT-01 | G3 |
| **FR-ADM-09** | Admin can cancel a scenario: "clear construction at Junction A" | Medium | Removes capacity multiplier; affected drivers reroute | FR-SIM-02, FR-ROU-05 | G3 |
| **FR-ADM-10** | All admin scenario commands are audit-logged | Critical | Log entry: timestamp, user, raw utterance, parsed spec, before/after edge weights | FR-SEC-04, FR-AUD-01 | G6, GAP-11 |
| **FR-ADM-11** | Admin cannot request personal routes for specific drivers | Critical | Guardrail rejects `route_request` with 403; logs attempt | FR-SEC-03, FR-NLP-06 | G4, GAP-13 |

---

## 4. Chatbot/NLP Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-CHT-01** | Chatbot accessible via button in dashboard toolbar | Critical | Button visible when engine connected; opens panel/modal | FR-DSH-03 | G1, GAP-06 |
| **FR-CHT-02** | Chat panel supports streaming/typing indicator for responses | High | Bot response appears incrementally or with "thinking" indicator | FR-DSH-04 | G1 |
| **FR-CHT-03** | Chat history persists for session duration | Medium | Refresh preserves last 50 messages | FR-DSH-04 | — |
| **FR-NLP-01** | Intent taxonomy covers all driver + admin intents (see §4.1) | Critical | 100% of example utterances in 04_nlp_design.md classify correctly | GAP-03 | G1, G3 |
| **FR-NLP-02** | Metrics query intents (`query_efficiency`, `query_zone`, `query_gini`) return live data | Critical | Response includes current values from engine broadcast cache | FR-RT-01 | G5 |
| **FR-NLP-03** | Entity extraction: junction/node IDs, road/edge IDs, zone IDs | Critical | "Junction 42" → node_id=42; "Main St" → edge set via gazetteer | FR-NLP-05 | G1, G3, GAP-12 |
| **FR-NLP-04** | Entity extraction: severity (low/medium/high → 0.3/0.7/1.0), duration (relative/absolute), time windows | Critical | "heavy traffic for 2 hours" → severity=0.7, duration_s=7200 | FR-NLP-05 | G3 |
| **FR-NLP-05** | Scenario modulation intent (`scenario_update`) parses: target (node/edge/zone), operation (reduce_capacity, add_congestion, close), severity, duration | Critical | Structured `ScenarioSpec` emitted for engine consumption | FR-SIM-01 | G3, GAP-04 |
| **FR-NLP-06** | Role guardrail: intent classified → role checked → execution allowed/denied | Critical | Driver `scenario_update` → 403; Admin `route_request` → 403 | FR-SEC-03 | G4, GAP-13 |
| **FR-NLP-07** | Ambiguity detection: multiple gazetteer matches → clarification dialog | High | "Junction A" matches 3 nodes → "Did you mean Junction A (node 12), Junction A (node 45), or Junction A (node 78)?" | GAP-12 | G1, G3 |
| **FR-NLP-08** | Clarification dialog: user selects option → original intent re-executes with resolved entity | High | Single-turn resolution; no context loss | FR-NLP-07 | GAP-12 |
| **FR-NLP-09** | Fallback: unrecognized intent → "I didn't understand. Try: 'best route to...', 'avoid Junction...', 'construction at...'" | Medium | Helpful error with examples per role | — | — |
| **FR-NLP-10** | NLP service caches engine metrics (WebSocket client) for sub-100ms query response | High | `chat_service.py` maintains latest `metrics`, `zone_metrics`, `signals` | FR-RT-01 | TR-ML-09 |

### 4.1 Intent Taxonomy

| Intent | Role | Entities | Example Utterances |
|--------|------|----------|-------------------|
| `route_request` | Driver | destination (node/landmark), avoid[], via[] | "best route to downtown", "fastest way to Junction 42" |
| `avoid_node` | Driver | node_id[] | "avoid Junction A", "don't go through node 12" |
| `via_node` | Driver | node_id[] | "go through Junction B", "must pass node 45" |
| `clear_constraints` | Driver | — | "clear my constraints", "reset route" |
| `scenario_update` | Admin | target (node/edge/zone), operation, severity, duration | "bridge at Junction A under construction", "heavy traffic on Main St for 2 hours" |
| `query_efficiency` | Admin | metric (avg_wait, throughput, gini, zone_wait) | "what's the citywide average wait time?", "show Gini coefficient" |
| `query_incidents` | Admin | — | "list active incidents", "any construction right now?" |
| `cancel_scenario` | Admin | target (node/edge/incident_id) | "clear construction at Junction A", "remove incident 3" |

---

## 5. Routing Engine Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-ROU-01** | Compute shortest-time path (A*) from origin to destination | Critical | Uses current dynamic edge weights (length, lanes, congestion, incidents) | FR-SIM-01 | G1, TR-ENG-04 |
| **FR-ROU-02** | Support must-visit (via) nodes: path must pass through specified nodes in order | Critical | Via nodes inserted as waypoints; sub-paths concatenated | FR-ROU-01 | G2, GAP-08 |
| **FR-ROU-03** | Support must-avoid nodes: path must not traverse specified nodes | Critical | Avoided nodes removed from graph for this query; fallback if no path | FR-ROU-01 | G2, GAP-08 |
| **FR-ROU-04** | Return route as node ID array + computed ETA + distance | Critical | Format: `{ path: [n1,n2,...], eta_s: 342, distance_m: 8500 }` | FR-DSH-01 | G1 |
| **FR-ROU-05** | Dynamic reroute: when edge weights change (scenario/incident), recompute affected drivers' routes | Critical | Triggered by `scenario_update` or `incident` broadcast; pushes new path to driver agents | FR-SIM-03, FR-RT-02 | G2, GAP-09 |
| **FR-ROU-06** | Reroute respects driver's active avoid/via constraints | High | Constraints persisted per driver session; reapplied on reroute | FR-DRV-04, FR-DRV-05 | G2 |
| **FR-ROU-07** | Batch reroute for many drivers: prioritize by impact (delay delta) | Medium | Top 20% most-affected drivers rerouted first; others within 5 s | FR-ROU-05 | GAP-09 |
| **FR-ROU-08** | Route computation latency p95 ≤ 50 ms for single query | High | Measured on Chicago graph (29k nodes, 54k edges) | NFR-PERF-01 | — |

---

## 6. Simulation Engine Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-SIM-01** | `apply_scenario(scenario_spec)`: mutate edge capacity/speed multipliers for target edges | Critical | Accepts `ScenarioSpec { target_edges[], operation, severity, duration_s }`; applies multipliers | FR-NLP-05, GAP-04 | G3 |
| **FR-SIM-02** | `remove_scenario(target_edges[])`: revert multipliers to 1.0 | High | Removes specific scenario overlay; composites with other active scenarios | FR-ADM-09 | G3 |
| **FR-SIM-03** | On scenario apply/remove, broadcast `scenario_changed` with affected edges + new weights | Critical | Dashboard + drivers receive update; triggers reroute | FR-RT-02, FR-ROU-05 | G2, G3 |
| **FR-SIM-04** | Scenario expiry: automatic reversion after `duration_s` (sim time) | High | Uses existing `sim_time_` expiry mechanism from `apply_incident` | TR-ENG-13 | G3 |
| **FR-SIM-05** | Composite scenarios: multiple overlapping scenarios on same edge multiply | Medium | `effective_multiplier = Π(1 - severity_i)` for all active scenarios | FR-SIM-01 | G3 |
| **FR-SIM-06** | Driver-specific route request API: `request_route(driver_id, origin, destination, constraints)` | Critical | Returns computed path; registers driver for reroute notifications | FR-ROU-01, FR-ROU-02, FR-ROU-03 | G1, GAP-05 |
| **FR-SIM-07** | Engine tracks driver sessions: `driver_id → { current_path, constraints, agent_id }` | High | In-memory map; cleaned on disconnect | FR-SIM-06 | G1 |

---

## 7. Dashboard Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-DSH-01** | Chatbot button in toolbar (top-right, next to NLP Command Console) | Critical | Visible when `isConnected`; opens chat panel/modal | FR-CHT-01 | G1, GAP-06 |
| **FR-DSH-02** | Role selection modal on first chatbot open per session | Critical | Radio: Driver / Administrator; persists in `sessionStorage` | FR-CHT-01, FR-SEC-01 | G1, G4, GAP-07 |
| **FR-DSH-03** | Chat panel: message history, input box, send button, typing indicator | Critical | Matches `ChatPanel.tsx` style; integrated in RightDock or new modal | FR-CHT-02 | G1 |
| **FR-DSH-04** | Driver view: shows own route polyline, ETA, avoid/via chips, "clear constraints" button | Critical | Updates on reroute; chips removable individually | FR-DRV-07, FR-DRV-09 | G1, G2 |
| **FR-DSH-05** | Admin view: shows active scenarios list, system metrics quick-access buttons | High | "Citywide wait", "Gini", "Top 5 congested" as quick chips | FR-ADM-07, FR-ADM-08 | G3, G5 |
| **FR-DSH-06** | Clarification dialog component: radio list of matched entities + "None of these" | High | Accessible; keyboard navigable; submits resolved entity | FR-NLP-07, FR-NLP-08 | GAP-12 |
| **FR-DSH-07** | Audit log viewer (admin only): table with timestamp, user, action, before/after | Medium | Links from chat message "View audit log" | FR-ADM-10 | G6, GAP-11 |
| **FR-DSH-08** | All existing tabs (Metrics, Vision, Chat, Algos, Carbon, All) remain functional | Critical | No regression in RightDock tab content | FR-ADM-02 | G5 |

---

## 8. Real-Time Communication Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-RT-01** | NLP service maintains live cache of engine broadcast (metrics, zone_metrics, signals, incidents) | Critical | Sub-100ms read for metrics queries | FR-NLP-10 | TR-ML-09 |
| **FR-RT-02** | Engine broadcasts `scenario_changed` on apply/remove/expiry | Critical | Frame: `{ type: "scenario_changed", edges[], new_multiplier, source: "admin|incident|expiry" }` | FR-SIM-03 | G2, G3 |
| **FR-RT-03** | Engine sends driver-specific `route_update` via WebSocket | Critical | Frame: `{ type: "route_update", driver_id, path[], eta_s, reason: "scenario|incident|constraint" }` | FR-ROU-05, FR-SIM-06 | G2, GAP-10 |
| **FR-RT-04** | Dashboard subscribes to `route_update` for current driver session | Critical | Updates map polyline + ETA without full state refresh | FR-DSH-04 | G1, G2 |
| **FR-RT-05** | Gateway proxies engine WS (/ws) unchanged; no new ports | High | Existing `useWebSocket` hook handles new message types additively | NFR-5 | TRD §5.1 |

---

## 9. Security & Authorization Requirements

| ID | Description | Priority | Acceptance Criteria | Dependencies | Traceability |
|----|-------------|----------|---------------------|--------------|--------------|
| **FR-SEC-01** | Add "driver" role to JWT claims and gateway auth | Critical | `role: "driver"` in token; `require_role(["driver"])` works | FR-SEC-02 | GAP-01 |
| **FR-SEC-02** | Driver login: username/password → JWT with driver role | Critical | Separate driver credentials or self-registration flow | FR-SEC-01 | GAP-01 |
| **FR-SEC-03** | Intent-level authorization middleware in NLP service | Critical | Checks `user.role` vs `intent.allowed_roles` before execution | FR-NLP-06 | G4, GAP-13 |
| **FR-SEC-04** | Audit log: append-only JSONL file `/var/log/nexussim/audit.log` | Critical | Each admin scenario command: `{ ts, user, role, intent, raw_text, parsed_spec, edge_deltas }` | FR-ADM-10 | G6, GAP-11 |
| **FR-SEC-05** | Rate limiting on chatbot endpoints (10 req/min per user) | Medium | 429 response with retry-after header | FR-CHT-01 | — |

---

## 10. Non-Functional Requirements

| ID | Description | Target | Measurement | Traceability |
|----|-------------|--------|-------------|--------------|
| **NFR-PERF-01** | Route computation latency (single query) | p95 ≤ 50 ms | `bench_routing.cpp` on Chicago graph | FR-ROU-08 |
| **NFR-PERF-02** | End-to-end utterance → route on map | p95 ≤ 2 s | Stopwatch test: user send → polyline render | FR-DRV-02 |
| **NFR-PERF-03** | Scenario apply → all affected drivers rerouted | p95 ≤ 5 s | 1000 drivers, 10% edges affected | FR-ROU-05, FR-ROU-07 |
| **NFR-PERF-04** | NLP intent classification latency (rule-based) | p95 ≤ 10 ms | `chat_service.py` benchmark | FR-NLP-01 |
| **NFR-PERF-05** | NLP intent classification latency (LLM fallback) | p95 ≤ 2 s | With API key configured | FR-NLP-01 |
| **NFR-AVAIL-01** | Chatbot available when engine connected | 99.9% | Dashboard shows "NLP offline" only if sidecar down | FR-CHT-01 |
| **NFR-SEC-01** | No privilege escalation via NLP | 0 critical findings | Pen-test: driver cannot mutate scenario | FR-SEC-03 |
| **NFR-SEC-02** | Audit log tamper-evident | Append-only; hash chain | SHA-256 chain per entry | FR-SEC-04 |
| **NFR-MAINT-01** | Intent taxonomy extensible without code changes | Config-driven | New intents added to `nlp/intents.yaml` | FR-NLP-01 |
| **NFR-MAINT-02** | Gazetteer auto-rebuilds on city change | < 5 s | `IncidentParser` reloads on `city` message | FR-NLP-03 |

---

## 11. Requirement Traceability Matrix (Summary)

| PRD Goal | Key Requirements |
|----------|------------------|
| G1: Driver route request + display | FR-DRV-01…09, FR-ROU-01…04, FR-DSH-01…04, FR-CHT-01…03 |
| G2: Dynamic constraints + reroute | FR-DRV-04…06, FR-DRV-08, FR-ROU-02…03, FR-ROU-05…07, FR-SIM-03, FR-RT-02…04 |
| G3: Admin scenario modulation | FR-ADM-03…06, FR-ADM-09, FR-NLP-05, FR-SIM-01…05 |
| G4: Role guardrails | FR-DRV-10, FR-ADM-11, FR-SEC-01…03, FR-NLP-06 |
| G5: Dashboard metrics retention | FR-ADM-02, FR-ADM-07, FR-DSH-08 |
| G6: Audit logging | FR-ADM-10, FR-SEC-04 |