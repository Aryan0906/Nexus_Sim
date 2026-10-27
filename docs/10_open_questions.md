# 10_open_questions.md — Decisions Required from Stakeholders

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Critical Decisions (Block Implementation)](#1-critical-decisions-block-implementation)
2. [Architecture Decisions](#2-architecture-decisions)
3. [Product/UX Decisions](#3-productux-decisions)
4. [Technical Decisions](#4-technical-decisions)
5. [Operational Decisions](#5-operational-decisions)
6. [Future Extensibility Decisions](#6-future-extensibility-decisions)
7. [Decision Log Template](#7-decision-log-template)

---

## 1. Critical Decisions (Block Implementation)

> **These must be resolved before Sprint 1 kickoff (Phase 0).**

### D1: NLP Engine Choice
**Question:** Which NLP backend for intent classification and entity extraction?

| Option | Pros | Cons | Recommendation |
|--------|------|------|----------------|
| **Rule-based + RapidFuzz (current)** | Zero cost, deterministic, <10ms, no external deps, already implemented | Limited flexibility; maintenance burden for new intents | ✅ **Recommended for v1** — extend existing `intents.yaml` |
| **Local quantized LLM (Llama-3-8B-Instruct via llama.cpp)** | Handles complex/ambiguous queries; no API cost; privacy | ~2-4GB VRAM/RAM; ~500-2000ms latency; model management | Phase 2+ |
| **Cloud LLM API (OpenAI/Anthropic)** | Best accuracy; handles multi-turn; low dev effort | Recurring cost; latency; privacy; requires API key mgmt | Fallback only |
| **Hybrid: Rule-based primary + LLM fallback** | Best of both; graceful degradation | Complexity; two code paths | Current architecture supports this |

**Decision Required:** Confirm rule-based + RapidFuzz as primary for v1, with LLM fallback stubbed (no API key required).

---

### D2: Driver Role Provisioning
**Question:** How are driver users created and authenticated?

| Option | Description | Pros | Cons |
|--------|-------------|--------|------|
| **Pre-created pool** | `driver1`..`driver20` in `gateway/auth.py` | Simple; no dynamic auth | Fixed pool; manual scaling |
| **Simulation-scoped auto-provision** | Gateway creates driver users on `/api/simulations` POST | Tied to simulation lifecycle | Requires auth.py mutation at runtime |
| **Anonymous sessions + driver_id** | No auth for driver role; driver_id in request body | Simplest UX; no credentials | No accountability; can't audit per-driver |
| **OIDC integration** | Real identities via Keycloak/Auth0 | Production-ready; SSO | Out of scope for v1 |

**Decision Required:** Choose provisioning model for v1. **Recommendation:** Pre-created pool (10-20 drivers) + Dashboard UI to assign driver to agent.

---

### D3: Map Data Source for Gazetteer
**Question:** Does `graph.json` contain edge/junction names suitable for gazetteer?

| Option | Description |
|--------|-------------|
| **OSM `name` tags** | Use existing OSM `name` on ways/nodes (may be sparse) |
| **Synthetic names** | Generate "Junction {node_id}" / "Road {edge_id}" fallbacks |
| **External gazetteer** | Import from GeoNames/OpenAddresses (extra pipeline step) |

**Decision Required:** Verify current `pipeline/src/clean.py` + `export.py` output. If names missing, synthetic fallback is acceptable for v1.

---

### D4: Real-Time Latency Targets
**Question:** What are acceptable latency budgets?

| Metric | Current Target | Stakeholder Confirmation Needed |
|--------|----------------|----------------------------------|
| Utterance → Route on map | p95 ≤ 2 s | ✅ Confirmed in requirements |
| Route computation (constrained) | p95 ≤ 100 ms | Need confirmation |
| Scenario apply → Reroute notify | p95 ≤ 500 ms | Need confirmation |
| 1000 drivers reroute batch | p95 ≤ 5 s | Need confirmation |
| NLP classification (rule-based) | p95 ≤ 10 ms | ✅ Based on current impl |
| NLP classification (LLM fallback) | p95 ≤ 2 s | Need confirmation |

**Decision Required:** Confirm or adjust latency targets before Phase 1 benchmarks.

---

## 2. Architecture Decisions

### D5: WebSocket vs. SSE for Real-Time Updates
**Current:** Engine uses WebSocket (port 9001) for all real-time.
**Question:** Should chatbot updates use same WS or separate SSE?

| Consideration | Recommendation |
|---------------|----------------|
| **Same WS** | Simpler; reuse existing `useWebSocket` hook; single connection |
| **Separate SSE** | HTTP/2 friendly; easier debugging; firewall-friendly |

**Decision:** **Same WebSocket** — additive message types (`route_update`, `scenario_changed`) follow NFR-5 (additive protocol).

---

### D6: Scenario Persistence
**Question:** Should scenarios survive engine restart?

| Option | Description |
|--------|-------------|
| **In-memory only (v1)** | Scenarios lost on restart; simple |
| **Persisted to disk** | JSON file per simulation; restored on restart |
| **Database** | PostgreSQL; multi-engine support |

**Decision:** **In-memory only for v1**. Persistence adds complexity; scenarios are "what-if" by nature. Document as known limitation.

---

### D7: Multi-Simulation Support
**Current:** Engine runs single simulation (single-sim lock).
**Question:** Should chatbot support multiple concurrent simulations?

| Option | Description |
|--------|-------------|
| **Single simulation (v1)** | Current architecture; simpler |
| **Multi-simulation** | Engine runs multiple; Gateway routes by `simulation_id` |

**Decision:** **Single simulation for v1**. Multi-sim requires engine redesign. Gateway `/api/simulations` SaaS already supports multi-sim at process level.

---

### D8: Driver-Agent Binding
**Question:** How does a driver map to a simulated agent?

| Option | Description |
|--------|-------------|
| **Manual selection** | Driver clicks agent on map → "Bind to this vehicle" |
| **Auto-assign nearest** | Driver registered → engine assigns closest agent |
| **Pre-spawned driver agents** | Special agent type `driver` spawned on demand |

**Decision Required:** **Recommend manual selection** — driver clicks agent on map, Dashboard sends `driver_register` with that `agent_id`. Most intuitive.

---

## 3. Product/UX Decisions

### D9: Chatbot Entry Point
**Question:** Where does the chatbot button live?

| Option | Location |
|--------|----------|
| **Toolbar (top-right)** | Next to NLPCommandConsole (current plan) |
| **RightDock Chat tab** | Inside existing Chat tab |
| **Floating action button** | Bottom-right, always visible |
| **Command palette (Cmd+K)** | Power-user shortcut |

**Decision:** **Toolbar button** — visible when engine connected; opens modal panel.

---

### D10: Role Selection Persistence
**Question:** How long does role selection persist?

| Option | Duration |
|--------|----------|
| **SessionStorage** | Per browser tab; cleared on close |
| **localStorage** | Persists across sessions |
| **Per simulation** | Reset when city changes |

**Decision:** **SessionStorage** — role is a session concept; user can switch by reopening chatbot.

---

### D11: Clarification Dialog UX
**Question:** How to present ambiguous options?

| Option | Description |
|--------|-------------|
| **Modal with radio list** | Simple; accessible; works on mobile |
| **Dropdown with search** | Better for >10 options |
| **Map preview** | Show mini-map for each option (nice-to-have) |

**Decision:** **Modal with radio list + optional mini-map** (if lat/lon available). Max 10 options; "None of these" triggers re-query.

---

### D12: Admin Quick-Action Chips
**Question:** What metric chips in admin view?

| Proposed Chips | Priority |
|----------------|----------|
| Citywide avg wait | High |
| Gini coefficient | High |
| Active agents | High |
| Top 5 congested corridors | Medium |
| Throughput (veh/hr) | Medium |
| Avg speed | Low |
| Emissions (CO2/hr) | Low |

**Decision Required:** Confirm default chips; make configurable later.

---

### D13: Audit Log Visibility
**Question:** Who can view audit log?

| Option | Access |
|--------|--------|
| **Admin only** | Current plan |
| **Admin + Editor** | Editors can see but not modify |
| **All authenticated** | Transparency |

**Decision:** **Admin only for v1**. Extend to editor in v2 if needed.

---

## 4. Technical Decisions

### D14: Constraint Persistence Across Reroutes
**Question:** When scenario forces reroute, are driver's avoid/via constraints reapplied?

| Option | Behavior |
|--------|----------|
| **Yes (persistent)** | Constraints stored in session; reapplied on every reroute |
| **No (one-shot)** | Constraints only for initial request; cleared on external reroute |

**Decision:** **Yes, persistent** — driver's intent (avoid Junction A) should survive external disruptions.

---

### D15: Via Node Ordering
**Question:** If driver says "go through A then B", is order enforced?

| Option | Behavior |
|--------|----------|
| **Strict order** | Path must visit A then B in that sequence |
| **Unordered set** | Path must visit both, any order |

**Decision:** **Strict order** — matches natural language semantics ("via A, then B").

---

### D16: Severity Granularity
**Question:** How many severity levels?

| Option | Levels |
|--------|--------|
| **3 levels** | Light (0.3), Moderate (0.5), Heavy (0.7), Closure (1.0) |
| **5 levels** | Light, Moderate, Heavy, Severe, Closure |
| **Continuous 0-1** | User says "30% capacity" → 0.3 |

**Decision:** **3 levels + closure** — maps to natural language; continuous via "X% capacity" parsing.

---

### D17: Incident vs. Scenario Distinction
**Current:** `incident` message exists (Phase 17). New: `apply_scenario`.
**Question:** Keep both or unify?

| Option | Description |
|--------|-------------|
| **Unify** | `apply_scenario` replaces `incident`; incident = scenario with source="incident" |
| **Separate** | Incident = short-term, auto-expiring; Scenario = admin, persistent |

**Decision:** **Unify internally, separate in API** — `incident` endpoint stays for backward compat; converts to `apply_scenario` with `source="incident"`.

---

### D18: Edge Weight Model for Routing
**Question:** Should routing use `effective_weight` (with congestion) or `base_weight`?

| Option | Behavior |
|--------|----------|
| **Effective (dynamic)** | Routes adapt to current congestion; realistic |
| **Base (static)** | Routes stable; predictable; ignores live conditions |

**Decision:** **Effective weight** — driver wants best route *now*. Congestion multiplier from RL signals included.

---

## 5. Operational Decisions

### D19: Audit Log Retention & Storage
**Question:** How long to keep audit logs?

| Option | Retention |
|--------|-----------|
| **1 year** | Compliance-friendly |
| **90 days** | Operational debugging |
| **Indefinite** | Full history |

**Decision:** **1 year, daily rotation, compressed**. Configurable via env.

---

### D20: Rate Limit Values
**Question:** Confirm rate limits for production.

| Endpoint | Proposed Limit | Confirmation |
|----------|----------------|--------------|
| `/api/chat` | 30 req/min/user | ☐ |
| `/api/incident` | 10 req/min/user | ☐ |
| `driver_register` | 1 per session | ☐ |
| `route_request` | 10 req/min/driver | ☐ |
| `driver_constraints` | 20 req/min/driver | ☐ |

**Decision Required:** Confirm or adjust before Phase 5.

---

### D21: Monitoring & Alerting
**Question:** What metrics to expose for chatbot health?

| Metric | Type |
|--------|------|
| NLP classification latency (p50/p95) | Histogram |
| Intent distribution (counter) | Counter |
| Guardrail denials (counter) | Counter |
| Clarification rate | Gauge |
| Active driver sessions | Gauge |
| Scenario apply rate | Counter |
| Reroute batch size/latency | Histogram |

**Decision Required:** Add to existing Prometheus/Grafana stack? Confirm metrics prefix.

---

## 6. Future Extensibility Decisions

### D22: Multi-Language Support
**Question:** Plan for non-English NLP?

| Approach | Effort |
|----------|--------|
| **Not in v1** | Defer |
| **Pattern translation** | Translate `intents.yaml` patterns per locale |
| **Multilingual LLM** | Use LLM fallback for all languages |

**Decision:** **Not in v1**. Design `intents.yaml` to be locale-aware (add `locale` field).

---

### D23: Voice Input
**Question:** Speech-to-text for driver hands-free?

| Option | Timeline |
|--------|----------|
| **Browser Web Speech API** | Easy integration; v2 |
| **Dedicated STT service** | Production; v3 |

**Decision:** **Defer to v2**. Browser Web Speech API can be added to ChatBotPanel input.

---

### D24: Route Sharing / Collaboration
**Question:** Can drivers share routes or see each other?

| Option | Description |
|--------|-------------|
| **Private only (v1)** | Each driver sees only own route |
| **Team view** | Drivers in same workspace see each other |
| **Public routes** | All drivers visible |

**Decision:** **Private only for v1**. Privacy by default.

---

### D25: Predictive Rerouting
**Question:** Proactive reroute before congestion hits?

| Option | Description |
|--------|-------------|
| **Reactive only (v1)** | Reroute after scenario/incident applied |
| **Predictive** | ML model predicts congestion; pre-reroute |

**Decision:** **Reactive for v1**. Predictive is RL/ML research area (Phase 18+).

---

## 7. Decision Log Template

Use this template for each decision:

```markdown
## DECISION: [Short Title]

**Date:** YYYY-MM-DD  
**Decision Maker:** [Name/Role]  
**Status:** Decided / Deferred / Needs Discussion

### Context
[Brief description of the problem]

### Options Considered
| Option | Pros | Cons |
|--------|------|------|
| A | ... | ... |
| B | ... | ... |

### Decision
[Chosen option with rationale]

### Consequences
- Positive: ...
- Negative: ...
- Risks: ...

### Related Documents
- [Link to affected docs]
```

---

## 8. Summary of Decisions Required Before Sprint 1

| # | Decision | Owner | Deadline |
|---|----------|-------|----------|
| D1 | NLP Engine Choice | Tech Lead | Week 0 |
| D2 | Driver Provisioning Model | Product + Tech | Week 0 |
| D3 | Gazetteer Data Source | Data Eng | Week 0 |
| D4 | Latency Targets Confirmation | Stakeholders | Week 0 |
| D8 | Driver-Agent Binding | UX + Tech | Week 1 |

> **Action:** Schedule 30-min decision meeting with stakeholders before Sprint 1 kickoff.