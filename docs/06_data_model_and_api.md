# 06_data_model_and_api.md — Entities, Schemas, REST/WebSocket Endpoints

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Core Entities](#1-core-entities)
2. [Database/Storage Schemas](#2-databasestorage-schemas)
3. [REST API Endpoints](#3-rest-api-endpoints)
4. [WebSocket API](#4-websocket-api)
5. [Request/Response Examples](#5-requestresponse-examples)
6. [Error Codes](#6-error-codes)
7. [API Versioning](#7-api-versioning)

---

## 1. Core Entities

### 1.1 Driver Session

```json
{
  "driver_id": "drv_abc123def456",
  "agent_id": 42,
  "status": "active",
  "created_at": "2026-10-22T14:30:00Z",
  "last_active": "2026-10-22T14:35:12Z",
  "origin_node": 10,
  "destination_node": 78,
  "current_path": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 78],
  "current_edge_index": 3,
  "eta_seconds": 420,
  "distance_meters": 8200,
  "constraints": {
    "avoid_nodes": [5, 12],
    "via_nodes": [45],
    "preference": "fastest"
  },
  "subscribed_edges": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 78]
}
```

### 1.2 Scenario / Incident Overlay

```json
{
  "scenario_id": "scn_xyz789",
  "source": "admin",
  "created_by": "admin",
  "created_at": "2026-10-22T14:32:00Z",
  "target": {
    "type": "junction",
    "junction_id": 12,
    "edges": [42, 43, 44],
    "description": "Bridge at Junction A (Main St)"
  },
  "operation": "reduce_capacity",
  "severity": 0.7,
  "multiplier": 5.0,
  "duration": {
    "type": "indefinite"
  },
  "status": "active",
  "expires_at": null,
  "affected_driver_count": 12
}
```

### 1.3 Route Computation Result

```json
{
  "route_id": "rte_abc123",
  "driver_id": "drv_abc123def456",
  "origin": 10,
  "destination": 78,
  "path": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 78],
  "path_edges": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114],
  "eta_seconds": 420,
  "distance_meters": 8200,
  "constraints_applied": {
    "avoid_nodes": [5, 12],
    "via_nodes": [45]
  },
  "computation_time_ms": 23,
  "status": "success",
  "reroute_reason": "initial"
}
```

### 1.4 Audit Log Entry

```json
{
  "timestamp": "2026-10-22T14:32:00.123Z",
  "log_id": "audit_20261022_143200_001",
  "user": "admin",
  "role": "admin",
  "intent": "scenario_update",
  "raw_text": "The bridge at Junction A is under construction, so that route will experience heavy traffic",
  "parsed_spec": {
    "target": { "type": "junction", "junction_id": 12, "edges": [42, 43, 44] },
    "operation": "reduce_capacity",
    "severity": 0.7,
    "duration": { "type": "indefinite" }
  },
  "edge_deltas": [
    { "edge_id": 42, "old_multiplier": 1.0, "new_multiplier": 5.0 },
    { "edge_id": 43, "old_multiplier": 1.0, "new_multiplier": 5.0 },
    { "edge_id": 44, "old_multiplier": 1.0, "new_multiplier": 5.0 }
  ],
  "hash": "a1b2c3d4e5f6..."  // SHA-256 of previous entry + this entry
}
```

### 1.5 NLP Clarification

```json
{
  "clarification_id": "clar_7x9k2m4n",
  "original_intent": "avoid_node",
  "entity": "nodes",
  "query": "Junction A",
  "options": [
    {
      "id": 12,
      "description": "Junction A (Main St / 1st Ave)",
      "lat": 41.8800,
      "lon": -87.6300,
      "zone": 3
    },
    {
      "id": 45,
      "description": "Junction A (Elm St / 5th Ave)",
      "lat": 41.8900,
      "lon": -87.6200,
      "zone": 5
    },
    {
      "id": 78,
      "description": "Junction A (Oak St / 10th Ave)",
      "lat": 41.9000,
      "lon": -87.6100,
      "zone": 7
    }
  ],
  "expires_at": "2026-10-22T14:33:00Z"
}
```

---

## 2. Database/Storage Schemas

### 2.1 In-Memory Stores (Engine)

| Store | Key | Value | TTL / Cleanup |
|-------|-----|-------|---------------|
| `driver_sessions` | `driver_id` (string) | `DriverSession` | 30 min idle |
| `edge_subscribers` | `edge_id` (int64) | `driver_id[]` | On reroute/session end |
| `active_scenarios` | `scenario_id` (string) | `Scenario` | On expiry/removal |
| `edge_multipliers` | `edge_id` (int64) | `MultiplierSet` | Recomputed on change |

### 2.2 Persistent Stores

| Store | Format | Location | Retention |
|-------|--------|----------|-----------|
| Audit Log | JSONL (append-only) | `/var/log/nexussim/audit.log` | 1 year / rotate daily |
| NLP Gazetteer Cache | JSON | `/tmp/nexussim/gazetteer_<city>.json` | Rebuild on city change |
| Driver Preferences | localStorage (browser) | `nexussim.driver.prefs` | Session + 30 days |

### 2.3 Schema Definitions (TypeScript / Pydantic)

#### DriverSession (TypeScript)
```typescript
interface DriverSession {
  driver_id: string;
  agent_id: number;
  status: 'active' | 'inactive' | 'disconnected';
  created_at: string;  // ISO 8601
  last_active: string;
  origin_node: number;
  destination_node: number;
  current_path: number[];
  current_edge_index: number;
  eta_seconds: number;
  distance_meters: number;
  constraints: DriverConstraints;
  subscribed_edges: number[];
}

interface DriverConstraints {
  avoid_nodes: number[];
  via_nodes: number[];
  preference: 'fastest' | 'shortest' | 'eco';
}
```

#### Scenario (Pydantic)
```python
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime

class TargetRef(BaseModel):
    type: Literal["junction", "road", "zone", "edge_set"]
    junction_id: Optional[int] = None
    road_name: Optional[str] = None
    zone_id: Optional[int] = None
    edges: List[int]
    description: str

class DurationSpec(BaseModel):
    type: Literal["relative", "absolute", "indefinite"]
    seconds: Optional[int] = None
    end_time: Optional[datetime] = None
    original: str

class Scenario(BaseModel):
    scenario_id: str
    source: Literal["admin", "incident", "nlp"]
    created_by: str
    created_at: datetime
    target: TargetRef
    operation: Literal["reduce_capacity", "add_congestion", "close", "restore"]
    severity: float  # 0.0 - 1.0
    multiplier: float  # computed from severity
    duration: DurationSpec
    status: Literal["active", "expired", "removed"]
    expires_at: Optional[datetime]
    affected_driver_count: int = 0
```

---

## 3. REST API Endpoints

### 3.1 Gateway (Port 8000) — Existing + Extended

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/login` | None | Login → JWT (roles: admin, editor, viewer, **driver**) |
| GET | `/api/auth/me` | JWT | Current user info |
| GET | `/api/cities` | None | List available cities |
| POST | `/api/cities/upload` | JWT (admin/editor) | Upload OSM → new city |
| POST | `/api/simulations` | JWT | Start simulation |
| GET | `/api/simulations` | JWT | List simulations |
| POST | `/api/scenarios` | JWT | Fork scenario (existing) |
| GET | `/api/scenarios` | JWT | List scenarios |
| POST | `/api/chat` | JWT | **NLP chat (proxied to NLP:9004)** |
| POST | `/api/incident` | JWT | **NLP incident (proxied to NLP:9004)** |
| GET | `/api/algo/registry` | JWT | Algorithm catalog |
| POST | `/api/emissions/estimate` | None | Public emissions estimate |
| GET | `/health` | None | Gateway health |

### 3.2 NLP Sidecar (Port 9004) — Internal (Proxied via Gateway)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | **Main NLP endpoint** — intent classification + entity extraction |
| POST | `/incident` | Incident parsing (existing) |
| POST | `/feedback` | Sentiment + classification (existing) |

> **Note:** All external access via Gateway `/api/chat`, `/api/incident`. Direct port 9004 not exposed externally.

---

## 4. WebSocket API

### 4.1 Engine WebSocket (Port 9001) — Proxied via Gateway `/ws`

#### Connection
```
WS wss://localhost:8000/ws
```
- Proxied by Gateway to Engine:9001
- Binary frames supported (FlatBuffers) but JSON used for control messages

#### Inbound Messages (Client → Engine)

| Type | Payload | Description |
|------|---------|-------------|
| `bounds` | `{ min_lat, min_lon, max_lat, max_lon }` \| `{ clear: true }` | Viewport LOD |
| `city` | `{ city: "chicago" }` | Start simulation (single-sim lock) |
| `pause` | `{}` | Freeze simulation |
| `resume` | `{}` | Continue simulation |
| `restart` | `{}` | Reload same city |
| `reset` | `{}` | Stop simulation, unlock city select |
| `policy_switch` | `{ policy: "webster\|rl\|fuzzy\|type2_fuzzy", intersection_id?: number }` | Hot-swap signal policy |
| `incident` | `{ edges: number[], severity: number, duration_s: number }` | Apply incident |
| **`driver_register`** | `{ driver_id: string, agent_id: number }` | **Register driver session** |
| **`route_request`** | `{ driver_id: string, origin: number, destination: number, avoid?: number[], via?: number[], preference?: "fastest"\|"shortest"\|"eco" }` | **Request constrained route** |
| **`driver_constraints`** | `{ driver_id: string, avoid?: number[], via?: number[] }` | **Update constraints** |
| **`apply_scenario`** | `{ edges: number[], severity: number, duration_s: number, source: "admin"\|"incident"\|"nlp" }` | **Admin scenario mutation** |
| **`remove_scenario`** | `{ edges: number[], source: "admin"\|"incident"\|"nlp" }` | **Remove scenario** |

#### Outbound Messages (Engine → Client)

| Type | Payload | Description |
|------|---------|-------------|
| `state_frame` | `{ tick, agents[], metrics, zone_metrics[], signals[], mode, incidents[] }` | Per-tick broadcast |
| `city_loaded` | `{ city: string \| null }` | Simulation started/stopped |
| `paused` | `{}` | Simulation paused |
| `resumed` | `{}` | Simulation resumed |
| `stopped` | `{}` | Simulation stopped |
| `policy_switched` | `{ ok: boolean, mode?: string, error?: string }` | Policy switch result |
| `error` | `{ message: string }` | Error notification |
| **`route_update`** | `{ driver_id: string, path: number[], eta_s: number, distance_m: number, reason: "initial"\|"constraint"\|"scenario"\|"incident"\|"congestion", error?: string }` | **Driver route update** |
| **`scenario_changed`** | `{ edges: number[], new_multiplier: number, source: "admin"\|"incident"\|"expiry", active_scenarios: ScenarioSummary[] }` | **Edge weight change** |
| **`driver_registered`** | `{ driver_id: string, agent_id: number, status: "ok"\|"error", error?: string }` | **Registration result** |

#### ScenarioSummary (in scenario_changed)
```json
{
  "scenario_id": "scn_xyz789",
  "source": "admin",
  "severity": 0.7,
  "multiplier": 5.0,
  "remaining_s": 3600
}
```

### 4.2 NLP WebSocket (Port 9004) — Internal Only

NLP sidecar is **WS client** of Engine (port 9001), not a WS server.
- Consumes `state_frame` for metrics cache
- Sends `apply_scenario` / `route_request` on behalf of users

---

## 5. Request/Response Examples

### 5.1 Driver Route Request

**Request (Dashboard → Gateway → NLP):**
```http
POST /api/chat HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "query": "best route to Junction 42 avoiding Junction 5",
  "city": "chicago",
  "role": "driver",
  "driver_id": "drv_abc123def456"
}
```

**Response (NLP → Gateway → Dashboard):**
```json
{
  "intent": "route_request",
  "answer": "Route computed: 8.2 km, 7 min via nodes [10, 15, 20, 25, 30, 35, 40, 42]",
  "confidence": 0.94,
  "handler": "rule_based_regex",
  "route_spec": {
    "path": [10, 15, 20, 25, 30, 35, 40, 42],
    "path_edges": [101, 102, 103, 104, 105, 106, 107, 108],
    "eta_s": 420,
    "distance_m": 8200,
    "constraints": { "avoid": [5], "via": [] }
  },
  "ws_message_sent": true
}
```

**Engine WS `route_update` (Engine → Dashboard):**
```json
{
  "type": "route_update",
  "driver_id": "drv_abc123def456",
  "path": [10, 15, 20, 25, 30, 35, 40, 42],
  "eta_s": 420,
  "distance_m": 8200,
  "reason": "initial"
}
```

### 5.2 Admin Scenario Update

**Request:**
```http
POST /api/chat HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
Content-Type: application/json

{
  "query": "bridge at Junction A under construction, heavy traffic for 2 hours",
  "city": "chicago",
  "role": "admin"
}
```

**Response:**
```json
{
  "intent": "scenario_update",
  "answer": "Construction scenario applied to 3 edges at Junction A (Main St). Severity: heavy (5.0x). Duration: 2 hours. 12 drivers rerouted.",
  "confidence": 0.92,
  "handler": "rule_based_regex",
  "scenario_spec": {
    "scenario_id": "scn_7x9k2m4n",
    "target": { "type": "junction", "junction_id": 12, "edges": [42, 43, 44] },
    "operation": "reduce_capacity",
    "severity": 0.7,
    "multiplier": 5.0,
    "duration": { "type": "relative", "seconds": 7200 }
  },
  "ws_message_sent": true
}
```

**Engine WS `scenario_changed` (Engine → Dashboard):**
```json
{
  "type": "scenario_changed",
  "edges": [42, 43, 44],
  "new_multiplier": 5.0,
  "source": "admin",
  "active_scenarios": [
    { "scenario_id": "scn_7x9k2m4n", "source": "admin", "severity": 0.7, "multiplier": 5.0, "remaining_s": 7200 }
  ]
}
```

**Engine WS `route_update` for affected drivers:**
```json
{
  "type": "route_update",
  "driver_id": "drv_abc123def456",
  "path": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 78],
  "eta_s": 580,
  "distance_m": 9100,
  "reason": "scenario"
}
```

### 5.3 Clarification Flow

**Request 1 (Ambiguous):**
```http
POST /api/chat
{
  "query": "avoid Junction A",
  "city": "chicago",
  "role": "driver",
  "driver_id": "drv_abc123def456"
}
```

**Response 1 (Clarification):**
```json
{
  "clarification": true,
  "clarification_id": "clar_7x9k2m4n",
  "original_intent": "avoid_node",
  "entity": "nodes",
  "query": "Junction A",
  "options": [
    { "id": 12, "description": "Junction A (Main St / 1st Ave)", "lat": 41.88, "lon": -87.63 },
    { "id": 45, "description": "Junction A (Elm St / 5th Ave)", "lat": 41.89, "lon": -87.62 },
    { "id": 78, "description": "Junction A (Oak St / 10th Ave)", "lat": 41.90, "lon": -87.61 }
  ]
}
```

**Request 2 (User Selection):**
```http
POST /api/chat
{
  "clarification_id": "clar_7x9k2m4n",
  "selected": 12,
  "role": "driver",
  "driver_id": "drv_abc123def456"
}
```

**Response 2 (Resolved):**
```json
{
  "intent": "avoid_node",
  "answer": "Now avoiding Junction A (Main St / 1st Ave). Route updated.",
  "confidence": 1.0,
  "handler": "clarification_resolved",
  "route_spec": {
    "path": [10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 78],
    "eta_s": 580,
    "distance_m": 9100
  }
}
```

### 5.4 Guardrail Denial

**Request (Driver tries admin intent):**
```http
POST /api/chat
{
  "query": "close the bridge at Junction A",
  "city": "chicago",
  "role": "driver",
  "driver_id": "drv_abc123def456"
}
```

**Response:**
```json
{
  "error": "forbidden",
  "message": "Driver role cannot execute scenario_update intent",
  "intent": "scenario_update",
  "required_role": "admin",
  "user_role": "driver"
}
```

---

## 6. Error Codes

### 6.1 HTTP Error Codes (REST)

| Code | Error Type | Description |
|------|------------|-------------|
| 400 | `invalid_request` | Malformed JSON, missing required fields |
| 401 | `unauthorized` | Missing/invalid JWT |
| 403 | `forbidden` | Role not authorized for intent (guardrail) |
| 404 | `not_found` | City, simulation, scenario not found |
| 409 | `conflict` | Duplicate city_id, scenario_id |
| 422 | `validation_failed` | Entity resolution failed, constraint conflict |
| 429 | `rate_limited` | Too many requests (10/min per user) |
| 500 | `internal_error` | Engine/NLP unavailable, computation failed |
| 503 | `service_unavailable` | Upstream sidecar down |

### 6.2 NLP-Specific Error Codes (in response body)

| Code | HTTP | Description |
|------|------|-------------|
| `clarification_required` | 422 | Ambiguous entity — clarification dialog needed |
| `entity_not_found` | 422 | Gazetteer/ner found no matches |
| `constraint_conflict` | 422 | Avoid + via same node, or avoid origin/dest |
| `no_path_found` | 422 | Routing failed with given constraints |
| `forbidden_intent` | 403 | Role guardrail denial |
| `nlp_offline` | 503 | NLP sidecar not responding |

### 6.3 WebSocket Error Codes

| Code | Reason | Action |
|------|--------|--------|
| 1000 | Normal closure | Reconnect |
| 1001 | Endpoint going away | Reconnect |
| 1008 | Policy violation (guardrail) | Log, show error to user |
| 1011 | Internal error (engine crash) | Reconnect with backoff |
| 4000 | Invalid message format | Fix client |
| 4001 | Unknown message type | Fix client |
| 4002 | Driver session not found | Re-register |
| 4003 | Route computation failed | Show error, allow retry |

---

## 7. API Versioning

### 7.1 Version Strategy

- **URL versioning:** `/api/v1/` prefix (future-proof)
- **Current:** v1 implicit (no prefix)
- **Breaking changes:** New version `/api/v2/`
- **Additive changes:** Same version (NFR-5: additive broadcast fields)

### 7.2 Current Version Headers

```
Accept: application/vnd.nexussim.v1+json
Content-Type: application/vnd.nexussim.v1+json
```

### 7.3 Deprecation Policy

- 3-month notice for deprecated endpoints
- `Deprecation: true` header + `Link: <new_url>; rel="successor-version"`
- Old versions supported in parallel during transition