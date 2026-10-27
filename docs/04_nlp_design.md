# 04_nlp_design.md — NLP Intent Taxonomy, Entity Schema & Guardrails

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Intent Taxonomy](#1-intent-taxonomy)
2. [Entity Schema](#2-entity-schema)
3. [Example Utterances with Parsed Output](#3-example-utterances-with-parsed-output)
4. [Ambiguity Handling & Clarification Dialogs](#4-ambiguity-handling--clarification-dialogs)
5. [Role Guardrails](#5-role-guardrails)
6. [Intent Patterns (Configuration)](#6-intent-patterns-configuration)
7. [Fallback & Error Handling](#7-fallback--error-handling)

---

## 1. Intent Taxonomy

### 1.1 Driver Intents

| Intent | Description | Required Entities | Optional Entities | Allowed Roles |
|--------|-------------|-------------------|-------------------|---------------|
| `route_request` | Compute best route from current location to destination | `destination` | `avoid[]`, `via[]`, `preference` (fastest/shortest/eco) | `driver` |
| `avoid_node` | Add junction(s) to avoid list for current route | `nodes[]` | — | `driver` |
| `via_node` | Add junction(s) that route must pass through | `nodes[]` | — | `driver` |
| `clear_constraints` | Reset all avoid/via constraints | — | — | `driver` |
| `query_my_route` | Ask for current route status/ETA | — | — | `driver` |
| `query_traffic` | Ask about traffic on specific road/area | `location` (road/zone) | — | `driver` |

### 1.2 Administrator Intents

| Intent | Description | Required Entities | Optional Entities | Allowed Roles |
|--------|-------------|-------------------|-------------------|---------------|
| `scenario_update` | Apply capacity/congestion change to road network | `target`, `operation`, `severity` | `duration`, `time_window` | `admin` |
| `query_efficiency` | Request system-wide or zone-level metrics | `metric` (avg_wait, throughput, gini, zone_wait, speed) | `zone` | `admin` |
| `query_incidents` | List active scenarios/incidents | — | `status` (active/expired) | `admin` |
| `cancel_scenario` | Remove a specific scenario/incident | `target` (edges or incident_id) | — | `admin` |
| `query_zone` | Get details for specific equity zone | `zone_id` | — | `admin` |
| `broadcast_alert` | Send notification to all drivers in area | `message`, `area` (zone/road) | `severity` | `admin` |

### 1.3 Shared/Utility Intents

| Intent | Description | Allowed Roles |
|--------|-------------|---------------|
| `help` | Show available commands per role | `driver`, `admin` |
| `unknown` | Fallback for unrecognized input | `driver`, `admin` |

---

## 2. Entity Schema

### 2.1 Core Entities

| Entity | Type | Description | Extraction Method | Examples |
|--------|------|-------------|-------------------|----------|
| `destination` | `NodeRef` | Target junction for route | Gazetteer + NER | "Junction 42", "downtown", "City Hall" |
| `nodes[]` | `NodeRef[]` | Junction node IDs for avoid/via | Gazetteer + NER | "Junction A", "nodes 5, 12, 45" |
| `target` | `TargetRef` | Road/edge/zone for scenario | Gazetteer + NER + pattern | "bridge at Junction A", "Main St", "Zone 3" |
| `operation` | `Enum` | Scenario operation type | Keyword matching | `reduce_capacity`, `add_congestion`, `close`, `restore` |
| `severity` | `Float` | Impact magnitude 0.0–1.0 | Keyword → value mapping | "light"→0.3, "moderate"→0.5, "heavy"→0.7, "full closure"→1.0 |
| `duration` | `DurationSpec` | How long scenario lasts | Relative/absolute time parsing | "2 hours", "until 6 PM", "indefinite" |
| `metric` | `Enum` | Metric to query | Keyword matching | "average wait", "Gini", "throughput" |
| `zone` | `ZoneRef` | Equity zone identifier | Gazetteer (zone names) | "Zone 3", "downtown zone" |
| `preference` | `Enum` | Route optimization criterion | Keyword matching | `fastest`, `shortest`, `eco` |

### 2.2 Complex Entity Types

#### `NodeRef`
```json
{
  "type": "node",
  "id": 42,
  "name": "Junction 42 (Main/5th)",
  "lat": 41.8781,
  "lon": -87.6298,
  "resolved": true
}
```

#### `TargetRef`
```json
{
  "type": "edge_set",
  "source": "junction",
  "junction_id": 12,
  "edges": [42, 43, 44],
  "description": "Bridge at Junction A (Main St)",
  "resolved": true
}
```

#### `DurationSpec`
```json
{
  "type": "relative",
  "seconds": 7200,
  "original": "2 hours"
}
```
```json
{
  "type": "absolute",
  "end_time": "2026-10-22T18:00:00Z",
  "original": "until 6 PM"
}
```
```json
{
  "type": "indefinite",
  "original": "indefinite"
}
```

#### `ZoneRef`
```json
{
  "type": "zone",
  "id": 3,
  "name": "Downtown Core",
  "resolved": true
}
```

---

## 3. Example Utterances with Parsed Output

### 3.1 Driver Examples

#### Example 1: Basic Route Request
**Utterance:** `"best route to Junction 42"`

**Parsed Output:**
```json
{
  "intent": "route_request",
  "confidence": 0.96,
  "entities": {
    "destination": {
      "type": "node",
      "id": 42,
      "name": "Junction 42",
      "resolved": true
    },
    "avoid": [],
    "via": [],
    "preference": "fastest"
  },
  "role": "driver",
  "driver_id": "drv_abc123"
}
```

#### Example 2: Route with Avoid Constraint
**Utterance:** `"I want the best route avoiding Junction A, going through Junction B"`

**Parsed Output:**
```json
{
  "intent": "route_request",
  "confidence": 0.92,
  "entities": {
    "destination": {
      "type": "node",
      "id": 78,
      "name": "Junction 78 (implied current destination)",
      "resolved": true
    },
    "avoid": [
      { "type": "node", "id": 12, "name": "Junction A (Main/1st)", "resolved": true }
    ],
    "via": [
      { "type": "node", "id": 45, "name": "Junction B (Elm/5th)", "resolved": true }
    ],
    "preference": "fastest"
  },
  "role": "driver",
  "driver_id": "drv_abc123"
}
```

#### Example 3: Add Avoid Constraint (Follow-up)
**Utterance:** `"also avoid Junction 5"`

**Parsed Output:**
```json
{
  "intent": "avoid_node",
  "confidence": 0.98,
  "entities": {
    "nodes": [
      { "type": "node", "id": 5, "name": "Junction 5", "resolved": true }
    ]
  },
  "role": "driver",
  "driver_id": "drv_abc123"
}
```

#### Example 4: Query Current Route
**Utterance:** `"what's my ETA?"`

**Parsed Output:**
```json
{
  "intent": "query_my_route",
  "confidence": 0.95,
  "entities": {},
  "role": "driver",
  "driver_id": "drv_abc123"
}
```

### 3.2 Administrator Examples

#### Example 5: Construction Scenario
**Utterance:** `"The bridge at Junction A is under construction, so that route will experience heavy traffic"`

**Parsed Output:**
```json
{
  "intent": "scenario_update",
  "confidence": 0.94,
  "entities": {
    "target": {
      "type": "edge_set",
      "source": "junction",
      "junction_id": 12,
      "edges": [42, 43, 44],
      "description": "Bridge at Junction A (Main St)",
      "resolved": true
    },
    "operation": "reduce_capacity",
    "severity": 0.7,
    "duration": {
      "type": "indefinite",
      "original": "under construction"
    }
  },
  "role": "admin",
  "user": "admin"
}
```

#### Example 6: Time-Bounded Congestion
**Utterance:** `"Heavy traffic on Main St between 1st and 5th for 2 hours"`

**Parsed Output:**
```json
{
  "intent": "scenario_update",
  "confidence": 0.91,
  "entities": {
    "target": {
      "type": "edge_set",
      "source": "road",
      "road_name": "Main St",
      "edges": [101, 102, 103, 104],
      "description": "Main St (1st Ave to 5th Ave)",
      "resolved": true
    },
    "operation": "add_congestion",
    "severity": 0.7,
    "duration": {
      "type": "relative",
      "seconds": 7200,
      "original": "2 hours"
    }
  },
  "role": "admin",
  "user": "admin"
}
```

#### Example 7: Query System Efficiency
**Utterance:** `"What's the citywide average wait time right now?"`

**Parsed Output:**
```json
{
  "intent": "query_efficiency",
  "confidence": 0.97,
  "entities": {
    "metric": "avg_wait"
  },
  "role": "admin",
  "user": "admin"
}
```

#### Example 8: Cancel Scenario
**Utterance:** `"Clear the construction at Junction A"`

**Parsed Output:**
```json
{
  "intent": "cancel_scenario",
  "confidence": 0.93,
  "entities": {
    "target": {
      "type": "edge_set",
      "source": "junction",
      "junction_id": 12,
      "edges": [42, 43, 44],
      "description": "Construction at Junction A",
      "resolved": true
    }
  },
  "role": "admin",
  "user": "admin"
}
```

### 3.3 Ambiguous Examples (Trigger Clarification)

#### Example 9: Ambiguous Junction Name
**Utterance:** `"avoid Junction A"`

**Gazetteer Matches:** 3 nodes named "Junction A" (IDs: 12, 45, 78)

**NLP Response (Clarification):**
```json
{
  "clarification": true,
  "clarification_id": "clar_7x9k2",
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

#### Example 10: Ambiguous Road Reference
**Utterance:** `"construction on Main St"`

**Gazetteer Matches:** 2 road segments named "Main St" (different edge sets)

**NLP Response (Clarification):**
```json
{
  "clarification": true,
  "clarification_id": "clar_3m8n1",
  "original_intent": "scenario_update",
  "entity": "target",
  "query": "Main St",
  "options": [
    { "id": "main_st_downtown", "description": "Main St (Downtown: 1st Ave to 10th Ave)", "edges": [101,102,103,104,105,106,107,108,109] },
    { "id": "main_st_uptown", "description": "Main St (Uptown: 11th Ave to 20th Ave)", "edges": [201,202,203,204,205,206,207,208,209] }
  ]
}
```

---

## 4. Ambiguity Handling & Clarification Dialogs

### 4.1 Detection Rules

| Condition | Trigger |
|-----------|---------|
| Gazetteer returns >1 match for entity | `avoid_node`, `via_node`, `scenario_update` target |
| NER extracts entity but gazetteer finds 0 matches | Low confidence → ask for clarification |
| Entity type mismatch (e.g., zone name used as junction) | Cross-reference entity types |

### 4.2 Clarification Flow

```
1. NLP detects ambiguity → returns clarification response (not final answer)
2. Dashboard receives clarification_id + options
3. Dashboard renders ClarificationDialog modal:
   - Title: "Which Junction A did you mean?"
   - Radio list: each option with description + mini-map preview (optional)
   - "None of these" → free-text re-entry
4. User selects option → clicks Confirm
5. Dashboard sends POST /chat with { clarification_id, selected: <id> }
6. NLP re-executes original intent with resolved entity
7. Normal response returned
```

### 4.3 Clarification Dialog UX

```typescript
interface ClarificationDialogProps {
  clarificationId: string;
  entityType: 'junction' | 'road' | 'zone';
  query: string;
  options: Array<{
    id: string | number;
    description: string;
    lat?: number;
    lon?: number;
    edges?: number[];
  }>;
  onConfirm: (selectedId: string | number) => void;
  onCancel: () => void;
}
```

- **Accessibility:** Keyboard navigation, ARIA labels, screen-reader friendly
- **Mini-map preview:** Optional Leaflet map showing option location (if lat/lon provided)
- **Timeout:** 60 s auto-dismiss → "clarification_expired" intent

---

## 5. Role Guardrails

### 5.1 Authorization Matrix

| Intent | Driver | Admin | Editor | Viewer |
|--------|--------|-------|--------|--------|
| `route_request` | ✅ | ❌ | ❌ | ❌ |
| `avoid_node` | ✅ | ❌ | ❌ | ❌ |
| `via_node` | ✅ | ❌ | ❌ | ❌ |
| `clear_constraints` | ✅ | ❌ | ❌ | ❌ |
| `query_my_route` | ✅ | ❌ | ❌ | ❌ |
| `query_traffic` | ✅ | ✅ | ✅ | ✅ |
| `scenario_update` | ❌ | ✅ | ✅ | ❌ |
| `query_efficiency` | ❌ | ✅ | ✅ | ✅ |
| `query_incidents` | ❌ | ✅ | ✅ | ✅ |
| `cancel_scenario` | ❌ | ✅ | ✅ | ❌ |
| `query_zone` | ❌ | ✅ | ✅ | ✅ |
| `broadcast_alert` | ❌ | ✅ | ❌ | ❌ |
| `help` | ✅ | ✅ | ✅ | ✅ |

### 5.2 Guardrail Implementation

**Location:** `ml/nlp/chat_service.py` → `check_permission(role: str, intent: str) -> bool`

```python
ROLE_INTENT_MATRIX = {
    "driver": {
        "route_request", "avoid_node", "via_node", 
        "clear_constraints", "query_my_route", "query_traffic", "help"
    },
    "admin": {
        "scenario_update", "query_efficiency", "query_incidents",
        "cancel_scenario", "query_zone", "broadcast_alert", "help",
        "query_traffic"  # admin can also query traffic
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

### 5.3 Audit Logging on Guardrail Denial

Every denied request logs:
```json
{
  "timestamp": "2026-10-22T14:30:00Z",
  "user": "driver1",
  "role": "driver",
  "intent": "scenario_update",
  "raw_text": "close the bridge at Junction A",
  "action": "denied",
  "reason": "Role 'driver' cannot execute intent 'scenario_update'"
}
```

---

## 6. Intent Patterns (Configuration)

### 6.1 File: `ml/nlp/intents.yaml` (New)

```yaml
# Intent patterns for rule-based classifier
# Extensible without code changes

intents:
  # Driver intents
  route_request:
    patterns:
      - "best route to {destination}"
      - "fastest way to {destination}"
      - "shortest path to {destination}"
      - "route to {destination} avoiding {avoid}"
      - "go to {destination} via {via}"
      - "navigate to {destination}"
    entities: [destination, avoid, via, preference]
    allowed_roles: [driver]
  
  avoid_node:
    patterns:
      - "avoid {nodes}"
      - "don't go through {nodes}"
      - "skip {nodes}"
      - "bypass {nodes}"
    entities: [nodes]
    allowed_roles: [driver]
  
  via_node:
    patterns:
      - "go through {nodes}"
      - "pass through {nodes}"
      - "via {nodes}"
      - "must visit {nodes}"
    entities: [nodes]
    allowed_roles: [driver]
  
  clear_constraints:
    patterns:
      - "clear constraints"
      - "reset route"
      - "remove avoid"
      - "remove via"
    entities: []
    allowed_roles: [driver]
  
  query_my_route:
    patterns:
      - "my route"
      - "my ETA"
      - "where am I going"
      - "current route"
    entities: []
    allowed_roles: [driver]
  
  query_traffic:
    patterns:
      - "traffic on {location}"
      - "congestion on {location}"
      - "how is {location}"
    entities: [location]
    allowed_roles: [driver, admin, editor, viewer]
  
  # Admin intents
  scenario_update:
    patterns:
      - "{target} under construction"
      - "{target} closed"
      - "heavy traffic on {target}"
      - "congestion on {target}"
      - "reduce capacity on {target}"
      - "close {target} for {duration}"
      - "{target} will have {severity} traffic"
    entities: [target, operation, severity, duration]
    allowed_roles: [admin, editor]
  
  query_efficiency:
    patterns:
      - "citywide {metric}"
      - "average {metric}"
      - "what is the {metric}"
      - "system {metric}"
      - "overall {metric}"
    entities: [metric]
    allowed_roles: [admin, editor, viewer]
  
  query_incidents:
    patterns:
      - "active incidents"
      - "current incidents"
      - "any construction"
      - "show incidents"
      - "list scenarios"
    entities: []
    allowed_roles: [admin, editor, viewer]
  
  cancel_scenario:
    patterns:
      - "clear {target}"
      - "remove {target}"
      - "cancel {target}"
      - "open {target}"
      - "end construction at {target}"
    entities: [target]
    allowed_roles: [admin, editor]
  
  query_zone:
    patterns:
      - "zone {zone}"
      - "equity zone {zone}"
      - "wait time in {zone}"
    entities: [zone]
    allowed_roles: [admin, editor, viewer]
  
  broadcast_alert:
    patterns:
      - "alert {area}: {message}"
      - "notify drivers in {area}: {message}"
    entities: [area, message, severity]
    allowed_roles: [admin]

# Entity extraction patterns
entities:
  destination:
    type: "node_ref"
    gazetteer: true
    ner_labels: ["LOCATION", "JUNCTION"]
  
  nodes:
    type: "node_ref_list"
    gazetteer: true
    ner_labels: ["LOCATION", "JUNCTION"]
    separator: ["and", ",", "or"]
  
  target:
    type: "target_ref"
    gazetteer: true
    ner_labels: ["LOCATION", "ROAD", "ZONE"]
    patterns:
      junction: "junction|intersection|node"
      road: "street|road|ave|ave.|avenue|blvd|drive|highway"
      zone: "zone|district|area"
  
  operation:
    type: "enum"
    values:
      reduce_capacity: ["construction", "under construction", "reduce capacity", "capacity reduction"]
      add_congestion: ["heavy traffic", "congestion", "congested", "traffic jam"]
      close: ["closed", "closure", "shut down", "blocked"]
      restore: ["open", "reopen", "clear", "restore", "remove"]
  
  severity:
    type: "float"
    mapping:
      light: 0.3
      moderate: 0.5
      medium: 0.5
      heavy: 0.7
      severe: 0.8
      "full closure": 1.0
      closed: 1.0
    default: 0.5
  
  duration:
    type: "duration_spec"
    patterns:
      relative: "(\\d+)\\s*(minute|hour|day)s?"
      absolute: "until\\s+(\\d{1,2}):?(\\d{2})?\\s*(am|pm)"
      indefinite: "indefinite|permanent|forever"
  
  metric:
    type: "enum"
    values:
      avg_wait: ["average wait", "avg wait", "wait time", "delay"]
      throughput: ["throughput", "flow", "vehicles per hour"]
      gini: ["gini", "equity", "inequality", "fairness"]
      zone_wait: ["zone wait", "zone delay"]
      speed: ["speed", "average speed", "velocity"]
  
  zone:
    type: "zone_ref"
    gazetteer: true
    patterns: ["zone \\d+", "district \\d+"]
```

---

## 7. Fallback & Error Handling

### 7.1 Classification Fallback Chain

```
1. Rule-based regex (intents.yaml patterns) → 98%+ accuracy, <10ms
   ↓ no match
2. Naive Bayes classifier (NLP-5) → 93.8% accuracy, <1ms
   ↓ no match / low confidence (<0.7)
3. LLM tool-calling (if API key configured) → ~850ms
   ↓ no API key / timeout
4. Fallback response: "I didn't understand. Try: 'best route to...', 'avoid Junction...', 'construction at...'"
```

### 7.2 Entity Resolution Fallback

| Failure | Fallback |
|---------|----------|
| Gazetteer 0 matches | NER + fuzzy search (rapidfuzz) with threshold 0.7 |
| Gazetteer >1 matches | Clarification dialog |
| NER extracts but no gazetteer entry | "Unknown location: {text}. Try a known junction/road name." |
| Duration parse fails | Default: indefinite (admin) / not applied (driver) |

### 7.3 Error Response Format

```json
{
  "error": "entity_resolution_failed",
  "message": "Could not resolve 'Junction XYZ'. Did you mean Junction 12 (Main/1st)?",
  "suggestions": [
    { "id": 12, "description": "Junction 12 (Main/1st)" },
    { "id": 45, "description": "Junction 45 (Elm/5th)" }
  ],
  "original_query": "avoid Junction XYZ"
}
```