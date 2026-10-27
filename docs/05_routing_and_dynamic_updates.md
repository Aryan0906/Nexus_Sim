# 05_routing_and_dynamic_updates.md — Routing Algorithm & Dynamic Reroute Design

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Algorithm Selection](#1-algorithm-selection)
2. [Edge Weight Model](#2-edge-weight-model)
3. [Constraint Handling](#3-constraint-handling)
4. [Reroute Triggers](#4-reroute-triggers)
5. [Update Frequency & Batching](#5-update-frequency--batching)
6. [Conflict Resolution](#6-conflict-resolution)
7. [Driver Session Management](#7-driver-session-management)
8. [Performance Targets](#8-performance-targets)
9. [Integration with Existing Engine](#9-integration-with-existing-engine)

---

## 1. Algorithm Selection

### 1.1 Primary Algorithm: A* with Constraints

| Aspect | Choice | Rationale |
|--------|--------|-----------|
| **Base algorithm** | A* (A-star) | Optimal with admissible heuristic; standard for road networks |
| **Heuristic** | Precomputed Euclidean distance (node-to-node) | Already implemented in `Pathfinder.h`; admissible, consistent |
| **Constraint handling** | Waypoint decomposition + node masking | Must-visit → waypoints; Must-avoid → graph pruning |
| **Stochastic diversity** | Controlled noise on edge costs (existing `compute_path_stochastic`) | Preserved for non-driver agents; driver routes deterministic |

### 1.2 Algorithm Variants

| Variant | Use Case | Implementation |
|---------|----------|----------------|
| `compute_path_constrained(origin, dest, avoid[], via[])` | Driver route requests | New method in `Pathfinder` |
| `compute_path_stochastic(origin, dest, noise_factor)` | Regular agent spawning | Existing |
| `recompute_affected(edges_changed)` | Batch reroute on scenario | New: uses `DriverSessionManager` subscriptions |

### 1.3 Why Not Dijkstra / Contraction Hierarchies / CH?

| Alternative | Verdict | Reason |
|-------------|---------|--------|
| Dijkstra | ❌ | No heuristic → slower on large graphs (29k nodes Chicago) |
| Contraction Hierarchies | ❌ | Preprocessing heavy; dynamic edge weights (scenarios) require rebuild |
| Custom A* + CH hybrid | ⚠️ | Future optimization; not needed for v1 |
| **A* with dynamic weights** | ✅ | Reuses existing heuristic; handles dynamic weights natively; p95 < 50ms verified |

---

## 2. Edge Weight Model

### 2.1 Base Weight Formula

```
base_weight(e) = length_m / (speed_limit_kmh * lanes * 1000/3600)
               = length_m * 3.6 / (speed_limit_kmh * lanes)
```

### 2.2 Dynamic Multipliers (Composite)

```
effective_weight(e) = base_weight(e) × congestion_multiplier(e) × scenario_multiplier(e) × incident_multiplier(e)
```

| Multiplier | Source | Range | Update Frequency |
|------------|--------|-------|------------------|
| `congestion_multiplier` | RL signal policy / queue lengths | 1.0 – 3.0 | Per tick (engine) |
| `scenario_multiplier` | Admin `scenario_update` | 1.0 – 10.0 (1.0 = normal, 10.0 = near closure) | On admin command |
| `incident_multiplier` | NLP `incident` / `apply_incident` | 1.0 – 10.0 | On incident + expiry |

### 2.3 Severity → Multiplier Mapping

| Severity | Description | `scenario_multiplier` | `incident_multiplier` |
|----------|-------------|----------------------|----------------------|
| 0.0 | Normal | 1.0 | 1.0 |
| 0.3 | Light congestion | 1.5 | 1.5 |
| 0.5 | Moderate | 2.5 | 2.5 |
| 0.7 | Heavy | 5.0 | 5.0 |
| 1.0 | Full closure | 100.0 (effectively infinite) | 100.0 |

> **Note:** Multipliers multiply. Two 0.7 scenarios on same edge = 5.0 × 5.0 = 25.0× base weight.

### 2.4 Weight Propagation

- Engine `ScenarioManager` maintains `edge_multipliers: Map<edge_id, MultiplierSet>`
- `MultiplierSet = { scenario: float, incident: float, congestion: float }`
- On any change → recompute `effective_weight` for affected edges
- Pathfinder reads current multipliers via `Graph::get_edge_multiplier(edge_id)`

---

## 3. Constraint Handling

### 3.1 Must-Avoid Nodes (`avoid[]`)

**Algorithm:** Graph pruning before A*
```
1. Create virtual graph view excluding avoid nodes
2. Remove avoid nodes and all incident edges
3. Run A* on pruned graph
4. If no path: return error "No path found avoiding specified nodes"
```

**Complexity:** O(E + V log V) same as A*; pruning is O(|avoid| × degree)

### 3.2 Must-Visit Nodes (`via[]`)

**Algorithm:** Waypoint decomposition
```
Input: origin O, destination D, via = [V1, V2, ..., Vk]

1. waypoints = [O] + via + [D]
2. full_path = []
3. For i in 0..len(waypoints)-2:
     sub_path = A*(waypoints[i], waypoints[i+1], avoid=avoid)
     if sub_path.empty: return error "No path from waypoint i to i+1"
     full_path.append(sub_path[:-1])  # exclude duplicate waypoint
4. full_path.append(sub_path[-1])    # add final destination
5. Return full_path
```

**Properties:**
- Optimal for given waypoint order (A* optimal per segment)
- Via order preserved as specified
- Avoid constraints apply to all sub-paths

### 3.3 Combined Constraints

| Combination | Handling |
|-------------|----------|
| `avoid` only | Graph pruning → single A* |
| `via` only | Waypoint decomposition → k+1 A* calls |
| `avoid` + `via` | Prune graph first → waypoint decomposition on pruned graph |
| Empty `via` + empty `avoid` | Standard A* (fastest path) |

### 3.4 Edge Cases

| Edge Case | Behavior |
|-----------|----------|
| Avoid node = origin/destination | Error: "Cannot avoid origin/destination" |
| Via node = origin/destination | Ignored (implicitly visited) |
| Avoid node in `via` list | Error: "Conflicting constraints: node X in both avoid and via" |
| No path with constraints | Error with details: "No path from A to B avoiding X" |
| Via nodes create cycles | Allowed (A* handles); sub-paths independent |

---

## 4. Reroute Triggers

### 4.1 Trigger Types

| Trigger | Source | Affected Drivers | Priority |
|---------|--------|------------------|----------|
| `scenario_applied` | Admin `apply_scenario` | Drivers with paths using affected edges | High |
| `scenario_removed` | Admin `remove_scenario` | Drivers with paths using affected edges | High |
| `incident_applied` | NLP `incident` / Engine `apply_incident` | Drivers with paths using affected edges | High |
| `incident_expired` | Engine timer | Drivers with paths using affected edges | Medium |
| `constraint_changed` | Driver `avoid_node`/`via_node` | Single driver (requestor) | High |
| `congestion_shift` | RL policy / queue change > threshold | Drivers on affected corridors | Low (batched) |

### 4.2 Trigger Flow

```
Event occurs (scenario/incident/constraint)
       ↓
ScenarioManager / IncidentHandler / DriverSessionManager
       ↓
Identify affected edges: E_affected
       ↓
DriverSessionManager.get_subscribers(E_affected) → [driver_1, driver_7, ...]
       ↓
For each driver (batched, prioritized):
  1. Recompute route: Pathfinder.compute_path_constrained(
         current_position, destination, driver.avoid, driver.via
     )
  2. If path changed:
       - Update driver session
       - Send WS route_update {driver_id, path, eta_s, reason}
       - Log reroute event
  3. If no path:
       - Send route_update with error + empty path
       - Driver notified "No route available with current constraints"
```

### 4.3 Current Position for Reroute

- Driver's agent has `lat`, `lon`, `edge_idx`, `path`
- **Reroute origin** = nearest node ahead on current path (not current GPS)
- Prevents "U-turn" artifacts; routes from next logical junction

---

## 5. Update Frequency & Batching

### 5.1 Real-Time Constraints

| Metric | Target |
|--------|--------|
| Single route computation | p95 ≤ 50 ms |
| Scenario apply → first reroute | p95 ≤ 500 ms |
| 1000 drivers reroute | p95 ≤ 5 s |
| Route update WS latency | < 100 ms (local) |

### 5.2 Batching Strategy

```cpp
// Engine-side batching in ScenarioManager::notify_affected_drivers()
struct RerouteBatch {
    std::vector<DriverSession*> drivers;
    std::chrono::steady_clock::time_point deadline;
};

void process_reroute_batch(RerouteBatch& batch) {
    // Sort by impact: drivers with largest delay delta first
    std::sort(batch.drivers.begin(), batch.drivers.end(), 
        [](auto a, auto b) { return a->estimated_delay_delta > b->estimated_delay_delta; });
    
    // Process in chunks of 50 per tick to avoid frame spike
    const size_t CHUNK_SIZE = 50;
    for (size_t i = 0; i < batch.drivers.size(); i += CHUNK_SIZE) {
        auto chunk_end = std::min(i + CHUNK_SIZE, batch.drivers.size());
        for (size_t j = i; j < chunk_end; ++j) {
            reroute_driver(batch.drivers[j]);
        }
        // Yield to next tick if deadline approached
        if (std::chrono::steady_clock::now() > batch.deadline) break;
    }
}
```

### 5.3 Frequency Limits

| Event Type | Max Frequency | Debounce |
|------------|---------------|----------|
| Scenario apply/remove | Immediate | None |
| Incident apply | Immediate | None |
| Incident expiry | Immediate | None |
| Congestion shift | 10 s | 10 s moving average |
| Driver constraint change | Immediate | None (user-initiated) |

---

## 6. Conflict Resolution

### 6.1 Simultaneous Reroutes

**Problem:** Many drivers reroute to same alternate path → new congestion

**Solution:** **Predictive Congestion-Aware Rerouting**

1. **Simulate impact:** Before committing batch, estimate new edge loads
2. **Diversify:** Add small stochastic noise (existing `compute_path_stochastic` noise_factor) to edge costs per driver
3. **Priority:** Highest-delay-delta drivers get first choice of alternatives
4. **Iterative:** If batch > 500 drivers, process in waves with 100 ms gaps

### 6.2 Constraint Conflicts

| Conflict | Resolution |
|----------|------------|
| Driver A avoids node X, Driver B needs node X | Independent — no conflict (per-driver constraints) |
| Admin closes edge E, Driver has `via` requiring E | Driver reroute fails → error "No route: required node unreachable" |
| Multiple scenarios on same edge | Composite multipliers (multiplicative) |

### 6.3 Scenario Overlap Resolution

```cpp
// ScenarioManager::get_effective_multiplier(edge_id)
float get_effective_multiplier(int64_t edge_id) {
    float mult = 1.0f;
    for (auto& scenario : active_scenarios[edge_id]) {
        if (!scenario.expired()) {
            mult *= scenario.multiplier;  // e.g., 5.0 * 2.5 = 12.5
        }
    }
    return mult;
}
```

- **No priority** — all active scenarios multiply
- **Expiry** handled per-scenario; removal recomputes multiplier
- **Audit log** records each scenario's contribution

---

## 7. Driver Session Management

### 7.1 Data Structures

```cpp
// engine/src/agent/DriverSessionManager.h

struct DriverConstraints {
    std::vector<int64_t> avoid_nodes;
    std::vector<int64_t> via_nodes;
    RoutePreference preference = RoutePreference::FASTEST;
    std::chrono::steady_clock::time_point last_updated;
};

struct DriverSession {
    std::string driver_id;
    int64_t agent_id;           // Associated simulated agent
    int64_t current_origin;     // Nearest node ahead on path
    int64_t destination;        // Target node
    std::vector<int64_t> current_path;
    DriverConstraints constraints;
    bool active = true;
    std::chrono::steady_clock::time_point last_reroute;
};

class DriverSessionManager {
    // Maps
    std::unordered_map<std::string, DriverSession> sessions_;           // driver_id → session
    std::unordered_map<int64_t, std::vector<std::string>> edge_subscribers_; // edge_id → driver_ids
    
    // Core methods
    void register_driver(const std::string& driver_id, int64_t agent_id);
    void update_constraints(const std::string& driver_id, const DriverConstraints& c);
    void update_destination(const std::string& driver_id, int64_t dest);
    std::vector<std::string> get_subscribers(const std::vector<int64_t>& edges);
    void on_route_updated(const std::string& driver_id, const std::vector<int64_t>& new_path);
    void cleanup_inactive(std::chrono::seconds max_idle = 30min);
};
```

### 7.2 Subscription Model

- **On route compute:** `edge_subscribers_[edge].push_back(driver_id)` for all edges in path
- **On reroute:** Remove from old edges, add to new edges
- **On scenario/incident:** `get_subscribers(affected_edges)` returns unique driver IDs
- **Cleanup:** Inactive sessions (no WS heartbeat 30 min) removed

### 7.3 Driver Registration Flow

```
1. Dashboard: User selects Driver role → generates driver_id (UUID)
2. Dashboard: WS driver_register {driver_id, agent_id} 
   - agent_id = selected agent on map (or auto-assign nearest)
3. Engine: DriverSessionManager.register_driver()
   - Creates session with current agent position as origin
   - Subscribes to agent's current path edges
4. Engine: WS driver_registered {driver_id, status: "ok"}
5. Dashboard: Ready for route requests
```

---

## 8. Performance Targets

| Operation | Graph Size | Target | Measurement |
|-----------|------------|--------|-------------|
| `compute_path_constrained` (no constraints) | Chicago (29k nodes) | p50 ≤ 15 ms, p95 ≤ 50 ms | `bench_routing.cpp` |
| `compute_path_constrained` (5 avoid, 3 via) | Chicago | p50 ≤ 30 ms, p95 ≤ 100 ms | `bench_routing.cpp` |
| Batch reroute (100 drivers) | Chicago | p95 ≤ 500 ms | Integration test |
| Batch reroute (1000 drivers) | Chicago | p95 ≤ 5 s | Integration test |
| Scenario apply + notify | 10 edges affected | p95 ≤ 200 ms | Integration test |
| Memory per driver session | — | < 5 KB | Static analysis |

### 8.1 Optimization Techniques

| Technique | Applied |
|-----------|---------|
| Heuristic precomputation | ✅ Existing (Euclidean node-to-node) |
| Graph pruning (avoid) | ✅ Bitmask / adjacency filter |
| Waypoint decomposition | ✅ k+1 A* calls |
| Edge weight caching | ✅ `Graph::get_edge_multiplier()` O(1) |
| Batch processing | ✅ Chunked per tick |
| Stochastic diversification | ✅ Existing `noise_factor` |

---

## 9. Integration with Existing Engine

### 9.1 Files to Modify

| File | Changes |
|------|---------|
| `engine/src/agents/Pathfinder.h` | Add `compute_path_constrained()` method |
| `engine/src/agent/ScenarioManager.h` | New file: scenario composite, expiry, notifications |
| `engine/src/agent/DriverSessionManager.h` | New file: session registry, subscriptions |
| `engine/src/network/WebSocketServer.h` | Dispatch new message types |
| `engine/src/agent/Simulation.h` | Integrate ScenarioManager + DriverSessionManager in tick |
| `engine/include/Pathfinder.h` | Public API declarations |

### 9.2 Message Types (Engine WS)

**Inbound:**
```cpp
enum class InboundType {
    // Existing
    BOUNDS, CITY, PAUSE, RESUME, RESTART, RESET, 
    POLICY_SWITCH, INCIDENT,
    // New
    DRIVER_REGISTER,        // {driver_id, agent_id}
    ROUTE_REQUEST,          // {driver_id, origin, destination, avoid[], via[], preference}
    DRIVER_CONSTRAINTS,     // {driver_id, avoid[], via[]}
    APPLY_SCENARIO,         // {edges[], severity, duration_s, source}
    REMOVE_SCENARIO         // {edges[], source}
};
```

**Outbound:**
```cpp
enum class OutboundType {
    // Existing
    STATE_FRAME, CITY_LOADED, PAUSED, RESUMED, STOPPED, 
    POLICY_SWITCHED, ERROR,
    // New
    ROUTE_UPDATE,           // {driver_id, path[], eta_s, distance_m, reason}
    SCENARIO_CHANGED,       // {edges[], new_multiplier, source, active_scenarios[]}
    DRIVER_REGISTERED       // {driver_id, agent_id, status}
};
```

### 9.3 Tick Integration

```cpp
// In Simulation::tick()
void Simulation::tick(float dt) {
    // Existing: agent updates, signal updates, metrics
    update_agents(dt);
    update_signals(dt);
    compute_metrics();
    
    // New: scenario expiry check
    scenario_manager_.update_expiry(sim_time_);
    
    // New: congestion shift detection (batched, not every tick)
    if (tick_count_ % 100 == 0) {  // Every 100 ticks (~10s)
        auto congestion_changes = detect_significant_congestion_shifts();
        if (!congestion_changes.empty()) {
            notify_affected_drivers(congestion_changes, "congestion");
        }
    }
    
    broadcast_state();
}
```

---

## 10. Testing Scenarios

| Scenario | Test | Expected |
|----------|------|----------|
| Basic route | A* origin→dest | Path matches existing `compute_path` |
| Avoid single node | Path excludes node | Node not in path |
| Avoid multiple nodes | Path excludes all | No avoided nodes in path |
| Via single node | Path includes node | Node in path at correct position |
| Via multiple nodes | Path visits in order | Sequence preserved |
| Avoid + Via combined | Pruned graph + waypoints | Both constraints satisfied |
| No path with constraints | Error returned | Clear error message |
| Scenario apply → reroute | 10 drivers affected | All rerouted within 500 ms |
| Incident expiry → reroute | Drivers on incident edges | Reroute with reason="incident" |
| Constraint change → reroute | Single driver | Immediate reroute |
| 1000 simultaneous reroutes | Stress test | < 5 s, no frame drop > 16 ms |