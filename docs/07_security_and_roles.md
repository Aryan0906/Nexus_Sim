# 07_security_and_roles.md — Role Authentication, Authorization Matrix & Audit Logging

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Authentication Architecture](#1-authentication-architecture)
2. [Role Definitions](#2-role-definitions)
3. [Authorization Matrix](#3-authorization-matrix)
4. [JWT Token Structure](#4-jwt-token-structure)
5. [Intent-Level Guardrails](#5-intent-level-guardrails)
6. [Audit Logging](#6-audit-logging)
7. [Session Management](#7-session-management)
8. [Rate Limiting](#8-rate-limiting)
9. [Security Considerations](#9-security-considerations)
10. [Implementation Checklist](#10-implementation-checklist)

---

## 1. Authentication Architecture

### 1.1 Current State (Gateway `gateway/auth.py`)

| Component | Implementation |
|-----------|----------------|
| **Auth Provider** | In-memory user store (dev) → replace with OIDC/OAuth2 in production |
| **Token Format** | JWT (HS256) |
| **Token Expiry** | 60 minutes (configurable via `NEXUSSIM_JWT_EXPIRE_MIN`) |
| **Secret** | `NEXUSSIM_JWT_SECRET` env var (dev default: "dev-secret-change-in-production") |
| **Algorithm** | HS256 (symmetric) — upgrade to RS256 with JWKS in production |
| **Password Storage** | Plaintext (dev only) — bcrypt/argon2 required for production |

### 1.2 Extended Architecture for Chatbot

```
┌─────────────┐     HTTPS      ┌─────────────┐     HTTPS      ┌─────────────┐
│  Browser    │ ─────────────► │   Gateway   │ ─────────────► │  NLP Sidecar │
│  (Dashboard)│  POST /api/chat│  :8000      │  POST /chat    │  :9004       │
└─────────────┘                └─────────────┘                └─────────────┘
       │                              │                              │
       │ JWT in Authorization         │ Validates JWT                │ Receives user
       │ header                       │ Extracts role                │ role + driver_id
       ▼                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTHORIZATION DECISION                              │
│  1. Gateway: workspace access (existing)                                    │
│  2. NLP: intent × role matrix (NEW)                                         │
│  3. Engine: driver session ownership (NEW)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Authentication Flow

```
1. User opens Dashboard → clicks Chatbot button
2. Dashboard checks localStorage for JWT
3. If no JWT → redirect to /login page
4. User submits credentials → POST /api/auth/login
5. Gateway validates → returns JWT + user {username, workspaces, role}
6. Dashboard stores JWT in memory (not localStorage for security)
7. All subsequent /api/chat requests include Authorization: Bearer <JWT>
8. Gateway validates JWT → forwards to NLP with user context headers
9. NLP extracts role → applies intent guardrails
```

---

## 2. Role Definitions

### 2.1 Role Hierarchy

```
admin (highest)
  └── editor
        └── viewer
              └── driver (new, isolated)
```

| Role | Description | Primary Use Case |
|------|-------------|------------------|
| **admin** | Full system access: simulations, scenarios, algorithms, users, workspaces | Platform operator, system administrator |
| **editor** | Create/modify simulations, scenarios, algorithms; read all metrics | Traffic engineer, policy analyst |
| **viewer** | Read-only access to simulations, metrics, dashboards | Stakeholder, executive, public |
| **driver** | **NEW** — Personal route requests only; cannot view system metrics or mutate scenarios | Individual simulated vehicle operator |

### 2.2 User Store Extension (`gateway/auth.py`)

```python
# Add to USERS dict
USERS = {
    "admin": { "password": "admin", "workspaces": ["ws_default", "ws_acme"], "role": "admin" },
    "viewer": { "password": "viewer", "workspaces": ["ws_default"], "role": "viewer" },
    # NEW: Driver users (can be auto-provisioned per simulation)
    "driver1": { "password": "driver1", "workspaces": ["ws_default"], "role": "driver" },
    "driver2": { "password": "driver2", "workspaces": ["ws_default"], "role": "driver" },
    # ... or dynamically created per simulation
}
```

### 2.3 Driver Provisioning Options

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **Pre-created pool** | `driver1`..`driverN` in auth.py | Simple, no dynamic auth | Fixed pool size |
| **Simulation-scoped** | Gateway creates driver users on `/api/simulations` POST | Tied to simulation lifecycle | Requires auth.py mutation |
| **Anonymous + driver_id** | No auth for driver; driver_id in request body | Simplest UX | No accountability |
| **OIDC integration** | Real identities via Keycloak/Auth0 | Production-ready | Out of scope for v1 |

> **Decision for v1:** Pre-created pool (`driver1`..`driver20`) + simulation-scoped assignment via Dashboard UI.

---

## 3. Authorization Matrix

### 3.1 REST Endpoint Authorization (Gateway)

| Endpoint | admin | editor | viewer | driver |
|----------|-------|--------|--------|--------|
| `POST /api/auth/login` | ✅ | ✅ | ✅ | ✅ |
| `GET /api/auth/me` | ✅ | ✅ | ✅ | ✅ |
| `GET /api/cities` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/cities/upload` | ✅ | ✅ | ❌ | ❌ |
| `POST /api/simulations` | ✅ | ✅ | ❌ | ❌ |
| `GET /api/simulations` | ✅ | ✅ | ✅ (own ws) | ❌ |
| `POST /api/scenarios` | ✅ | ✅ | ❌ | ❌ |
| `GET /api/scenarios` | ✅ | ✅ | ✅ (own ws) | ❌ |
| `POST /api/algo/register` | ✅ | ✅ | ❌ | ❌ |
| `POST /api/algo/validate` | ✅ | ❌ | ❌ | ❌ |
| `POST /api/ingest/*` | ✅ | ✅ | ❌ | ❌ |
| `POST /api/chat` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/incident` | ✅ | ✅ | ❌ | ❌ |
| `GET /api/platform/rate-limit` | ✅ | ❌ | ❌ | ❌ |

> **Note:** `/api/chat` allowed for all roles — intent-level guardrails applied in NLP service.

### 3.2 WebSocket Message Authorization (Engine)

| Message Type | admin | editor | viewer | driver |
|--------------|-------|--------|--------|--------|
| `bounds` | ✅ | ✅ | ✅ | ✅ |
| `city` | ✅ | ✅ | ❌ | ❌ |
| `pause`/`resume`/`restart`/`reset` | ✅ | ✅ | ❌ | ❌ |
| `policy_switch` | ✅ | ✅ | ❌ | ❌ |
| `incident` | ✅ | ✅ | ❌ | ❌ |
| `driver_register` | ❌ | ❌ | ❌ | ✅ |
| `route_request` | ❌ | ❌ | ❌ | ✅ |
| `driver_constraints` | ❌ | ❌ | ❌ | ✅ |
| `apply_scenario` | ✅ | ✅ | ❌ | ❌ |
| `remove_scenario` | ✅ | ✅ | ❌ | ❌ |

> **Engine enforcement:** Engine trusts Gateway-authenticated WS connections. Role passed via initial handshake or first message.

---

## 4. JWT Token Structure

### 4.1 Payload Claims

```json
{
  "sub": "driver1",           // username
  "role": "driver",           // admin | editor | viewer | driver
  "workspaces": ["ws_default"], // array of workspace_ids
  "driver_id": "drv_abc123",  // NEW: for driver role only
  "iat": 1708523400,          // issued at
  "exp": 1708527000           // expires at (60 min default)
}
```

### 4.2 Token Validation (Gateway → NLP)

Gateway validates JWT, then forwards to NLP with headers:
```
X-User: driver1
X-Role: driver
X-Workspaces: ws_default
X-Driver-ID: drv_abc123  (if role=driver)
```

NLP trusts these headers (internal network).

---

## 5. Intent-Level Guardrails

### 5.1 Guardrail Enforcement Points

| Layer | Check | Action on Deny |
|-------|-------|----------------|
| **Gateway** | Workspace access, role for endpoint | 403 Forbidden |
| **NLP Service** | Role × Intent matrix | 403 + audit log |
| **Engine** | Driver session ownership | 4002 WS error + audit log |

### 5.2 Intent × Role Matrix (Code)

**File:** `ml/nlp/chat_service.py` → `ROLE_INTENT_MATRIX`

```python
ROLE_INTENT_MATRIX = {
    "driver": {
        "route_request", "avoid_node", "via_node", 
        "clear_constraints", "query_my_route", "query_traffic", "help"
    },
    "admin": {
        "scenario_update", "query_efficiency", "query_incidents",
        "cancel_scenario", "query_zone", "broadcast_alert", "help",
        "query_traffic"
    },
    "editor": {
        "scenario_update", "query_efficiency", "query_incidents",
        "cancel_scenario", "query_zone", "help", "query_traffic"
    },
    "viewer": {
        "query_efficiency", "query_incidents", "query_zone", 
        "help", "query_traffic"
    }
}

def check_permission(role: str, intent: str) -> tuple[bool, str]:
    allowed = ROLE_INTENT_MATRIX.get(role, set())
    if intent in allowed:
        return True, ""
    return False, f"Role '{role}' cannot execute intent '{intent}'"
```

### 5.3 Engine-Level Driver Session Guard

```cpp
// In WebSocketServer::handle_route_request()
bool WebSocketServer::authorize_driver_request(
    const std::string& driver_id, 
    const std::string& requesting_user,
    const std::string& requesting_role
) {
    // Only driver role can send route_request
    if (requesting_role != "driver") return false;
    
    // Driver can only access their own session
    auto session = driver_manager_.get_session(driver_id);
    if (!session) return false;
    
    // In production: verify driver_id matches JWT sub
    // For v1: trust Gateway headers
    return true;
}
```

---

## 6. Audit Logging

### 6.1 Audit Log Requirements

| Requirement | Specification |
|-------------|---------------|
| **Format** | JSONL (one JSON object per line) |
| **Location** | `/var/log/nexussim/audit.log` |
| **Rotation** | Daily, compressed, retain 1 year |
| **Integrity** | SHA-256 hash chain (each entry includes hash of previous) |
| **Immutability** | Append-only; no modification/deletion via API |
| **Fields** | See §6.2 |

### 6.2 Audit Log Entry Schema

```json
{
  "timestamp": "2026-10-22T14:32:00.123Z",
  "log_id": "audit_20261022_143200_001",
  "version": 1,
  "event_type": "scenario_update",
  "user": {
    "username": "admin",
    "role": "admin",
    "workspace": "ws_default",
    "ip": "192.168.1.100"
  },
  "request": {
    "intent": "scenario_update",
    "raw_text": "The bridge at Junction A is under construction, so that route will experience heavy traffic",
    "parsed_spec": {
      "target": { "type": "junction", "junction_id": 12, "edges": [42, 43, 44] },
      "operation": "reduce_capacity",
      "severity": 0.7,
      "duration": { "type": "indefinite" }
    }
  },
  "effect": {
    "edge_deltas": [
      { "edge_id": 42, "old_multiplier": 1.0, "new_multiplier": 5.0 },
      { "edge_id": 43, "old_multiplier": 1.0, "new_multiplier": 5.0 },
      { "edge_id": 44, "old_multiplier": 1.0, "new_multiplier": 5.0 }
    ],
    "affected_drivers": ["drv_abc123", "drv_def456", "..."],
    "reroute_count": 12
  },
  "result": "success",
  "error": null,
  "integrity": {
    "prev_hash": "f0e1d2c3b4a5...",
    "hash": "a1b2c3d4e5f6..."  // SHA-256(prev_hash + current_entry_without_hash)
  }
}
```

### 6.3 Events Requiring Audit Log

| Event | Trigger | Logged By |
|-------|---------|-----------|
| Scenario applied | `apply_scenario` WS message | NLP (on behalf of admin) |
| Scenario removed | `remove_scenario` WS message | NLP |
| Scenario expired | Engine timer | Engine |
| Incident applied | `incident` WS message | NLP |
| Driver route request | `route_request` | NLP |
| Driver constraint change | `driver_constraints` | NLP |
| Guardrail denial | Any role × intent mismatch | NLP / Engine |
| Driver session created | `driver_register` | Engine |
| Policy switch | `policy_switch` | Engine |

### 6.4 Audit Log Implementation (NLP Side)

```python
# ml/nlp/audit_logger.py
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

AUDIT_LOG_PATH = os.environ.get("NEXUSSIM_AUDIT_LOG", "/var/log/nexussim/audit.log")
os.makedirs(os.path.dirname(AUDIT_LOG_PATH), exist_ok=True)

class AuditLogger:
    def __init__(self):
        self._last_hash = self._read_last_hash()
    
    def _read_last_hash(self) -> str:
        if not os.path.exists(AUDIT_LOG_PATH):
            return "0" * 64
        with open(AUDIT_LOG_PATH, "rb") as f:
            f.seek(0, 2)  # end of file
            size = f.tell()
            # Read last line efficiently
            f.seek(max(0, size - 4096), 0)
            lines = f.read().decode().strip().split('\n')
            if lines:
                last = json.loads(lines[-1])
                return last.get("integrity", {}).get("hash", "0" * 64)
        return "0" * 64
    
    def log(self, entry: Dict[str, Any]) -> str:
        entry["timestamp"] = datetime.utcnow().isoformat() + "Z"
        entry["log_id"] = f"audit_{entry['timestamp'].replace(':', '').replace('-', '')}_{os.urandom(4).hex()}"
        entry["version"] = 1
        entry["integrity"] = {
            "prev_hash": self._last_hash,
            "hash": ""
        }
        # Compute hash
        entry_copy = entry.copy()
        entry_copy["integrity"]["hash"] = ""
        entry_json = json.dumps(entry_copy, sort_keys=True, separators=(',', ':'))
        entry["integrity"]["hash"] = hashlib.sha256(
            (self._last_hash + entry_json).encode()
        ).hexdigest()
        
        # Append
        with open(AUDIT_LOG_PATH, "a") as f:
            f.write(json.dumps(entry, separators=(',', ':')) + "\n")
        
        self._last_hash = entry["integrity"]["hash"]
        return entry["log_id"]
    
    def log_scenario_update(self, user, parsed_spec, edge_deltas, affected_drivers):
        return self.log({
            "event_type": "scenario_update",
            "user": user,
            "request": { "intent": "scenario_update", "parsed_spec": parsed_spec },
            "effect": { "edge_deltas": edge_deltas, "affected_drivers": affected_drivers },
            "result": "success"
        })
    
    def log_guardrail_denial(self, user, intent, raw_text):
        return self.log({
            "event_type": "guardrail_denial",
            "user": user,
            "request": { "intent": intent, "raw_text": raw_text },
            "effect": {},
            "result": "denied",
            "error": f"Role '{user['role']}' cannot execute intent '{intent}'"
        })
```

---

## 7. Session Management

### 7.1 JWT Session

| Aspect | Value |
|--------|-------|
| Access Token Lifetime | 60 minutes (configurable) |
| Refresh Token | Not implemented v1 (re-login) |
| Storage | Memory only (not localStorage) |
| CSRF Protection | SameSite=Strict cookies for refresh (future) |

### 7.2 Driver Session (Engine)

| Aspect | Value |
|--------|-------|
| Session ID | `driver_id` (UUID v4) |
| Association | `driver_id` ↔ `agent_id` (1:1) |
| Creation | `driver_register` WS message |
| Expiry | 30 minutes idle (no route requests/constraints) |
| Cleanup | Background task every 5 minutes |
| Persistence | In-memory only (survives engine restart? No — re-register) |

### 7.3 Dashboard Session State

```typescript
// Stored in sessionStorage (per tab)
interface ChatbotSessionState {
  role: 'driver' | 'admin' | null;
  driverId: string | null;      // e.g., "drv_abc123"
  agentId: number | null;       // Selected agent on map
  constraints: DriverConstraints;
  chatHistory: ChatMessage[];
  lastClarificationId: string | null;
}
```

---

## 8. Rate Limiting

### 8.1 Limits

| Endpoint | Limit | Window | Scope |
|----------|-------|--------|-------|
| `POST /api/chat` | 30 req | 1 minute | Per user (JWT sub) |
| `POST /api/incident` | 10 req | 1 minute | Per user |
| `POST /api/auth/login` | 5 req | 1 minute | Per IP |
| WS `route_request` | 10 req | 1 minute | Per driver_id |
| WS `driver_constraints` | 20 req | 1 minute | Per driver_id |

### 8.2 Implementation

**Gateway** (`gateway/platform_services.py` → `rate_limiter`):
```python
# Already exists for platform services; extend for chatbot
rate_limiter = TokenBucketRateLimiter(
    capacity=30,
    refill_rate=0.5,  # per second
    key_func=lambda req: req.headers.get("X-User", req.client.host)
)
```

**Engine** (in `DriverSessionManager`):
```cpp
bool DriverSessionManager::check_rate_limit(const std::string& driver_id, const std::string& action) {
    auto now = std::chrono::steady_clock::now();
    auto& bucket = rate_buckets_[driver_id + ":" + action];
    // Token bucket: 10 tokens, refill 1/6 per second (10/min)
    if (bucket.try_consume(1)) return true;
    return false;
}
```

### 8.3 Exceeded Response

**HTTP 429:**
```json
{
  "error": "rate_limited",
  "message": "Too many requests. Limit: 30 per minute.",
  "retry_after": 45
}
```

**WS Error Frame:**
```json
{
  "type": "error",
  "code": 4002,
  "message": "Rate limit exceeded for route_request. Try again in 30s."
}
```

---

## 9. Security Considerations

### 9.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| **Privilege escalation** (driver → admin) | Intent guardrails at NLP + Engine; JWT role claim |
| **Session hijacking** | JWT short expiry (60 min); HTTPS only; SameSite cookies |
| **CSRF** | JWT in Authorization header (not cookie); CORS restricted |
| **Injection (NLP → Engine)** | Structured message types; no eval/exec; input validation |
| **Audit log tampering** | Hash chain; append-only file; file permissions 0600 |
| **DoS via route requests** | Rate limiting (10/min per driver); batch processing |
| **Information leakage** | Driver cannot query system metrics; viewer cannot mutate |

### 9.2 Production Hardening (Post-v1)

| Area | Action |
|------|--------|
| **Auth** | Replace in-memory with OIDC (Keycloak); RS256 JWT |
| **Secrets** | HashiCorp Vault / AWS Secrets Manager for JWT secret |
| **TLS** | mTLS between Gateway ↔ Sidecars ↔ Engine |
| **Audit** | Centralized log aggregation (ELK/Loki); SIEM integration |
| **RBAC** | Fine-grained permissions per workspace/resource |

---

## 10. Implementation Checklist

| Task | File | Status |
|------|------|--------|
| Add `driver` role to `gateway/auth.py` USERS | `gateway/auth.py` | ☐ |
| Add `require_role(["driver"])` dependency | `gateway/auth.py` | ☐ |
| Extend `/api/auth/login` to return `driver_id` for driver role | `gateway/server.py` | ☐ |
| Forward `X-Role`, `X-Driver-ID` headers to NLP | `gateway/server.py` proxy | ☐ |
| Implement `ROLE_INTENT_MATRIX` in NLP | `ml/nlp/chat_service.py` | ☐ |
| Add `check_permission()` call in `/chat` endpoint | `ml/nlp/chat_service.py` | ☐ |
| Implement `AuditLogger` class | `ml/nlp/audit_logger.py` (new) | ☐ |
| Integrate audit logging in all admin intents | `ml/nlp/chat_service.py` | ☐ |
| Add driver session guard in Engine WS handler | `engine/src/network/WebSocketServer.h` | ☐ |
| Add rate limiting for chat endpoints | `gateway/platform_services.py` | ☐ |
| Add rate limiting in Engine DriverSessionManager | `engine/src/agent/DriverSessionManager.h` | ☐ |
| Configure audit log path via env | `docker-compose.yml`, `.env` | ☐ |
| Write integration tests for guardrails | `ml/tests/test_nlp_guardrails.py` | ☐ |
| Write audit log verification test | `ml/tests/test_audit_log.py` | ☐ |