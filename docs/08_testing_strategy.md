# 08_testing_strategy.md — Testing Strategy & Acceptance Criteria

**Version:** 1.0  
**Status:** Draft  
**Owner:** Senior Systems Architect  
**Last Updated:** October 2026

---

## Table of Contents
1. [Testing Philosophy](#1-testing-philosophy)
2. [Test Pyramid](#2-test-pyramid)
3. [Unit Tests](#3-unit-tests)
4. [NLP Intent Accuracy Tests](#4-nlp-intent-accuracy-tests)
5. [Routing Correctness Tests](#5-routing-correctness-tests)
6. [Dynamic Reroute Tests](#6-dynamic-reroute-tests)
7. [Role-Permission Tests](#7-role-permission-tests)
8. [Load & Performance Tests](#8-load--performance-tests)
9. [Integration Tests](#9-integration-tests)
10. [End-to-End Acceptance Tests](#10-end-to-end-acceptance-tests)
11. [Test Data & Fixtures](#11-test-data--fixtures)
12. [CI/CD Integration](#12-cicd-integration)
13. [Test Execution Checklist](#13-test-execution-checklist)

---

## 1. Testing Philosophy

| Principle | Application |
|-----------|-------------|
| **Test at the right level** | Unit for logic, integration for contracts, E2E for user flows |
| **Deterministic over flaky** | Mock external services (Engine WS, Gazetteer, LLM) |
| **Fast feedback** | Unit < 1s, Integration < 30s, E2E < 5 min |
| **Realistic data** | Use Chicago graph (29k nodes) for routing benchmarks |
| **Guardrail verification** | Every role×intent combination tested |
| **Audit trail** | Every audit log entry format verified |

---

## 2. Test Pyramid

```
                    ┌─────────────┐
                    │   E2E (5)   │  ← Full user journeys
                   ┌┴─────────────┴┐
                  │ Integration (20)│  ← Component contracts
                 ┌┴────────────────┴┐
                │  Component (50)   │  ← NLP, Routing, Scenario, Auth
               ┌┴────────────────────┴┐
              │      Unit (200+)      │  ← Pure functions, algorithms
             ┌┴────────────────────────┴┐
            │   Static Analysis (CI)    │  ← Lint, type-check, security scan
           └────────────────────────────┘
```

**Target Distribution:**
- Unit: ~70% (fast, isolated)
- Component: ~20% (single service, mocked deps)
- Integration: ~8% (multi-service, real deps)
- E2E: ~2% (full stack, critical paths only)

---

## 3. Unit Tests

### 3.1 NLP Service (`ml/nlp/`)

| Test File | Target | Key Cases |
|-----------|--------|-----------|
| `test_intent_classifier.py` | `classify_intent_and_answer()` | All 17 intents; confidence thresholds; unknown fallback |
| `test_entity_extractor.py` | `extract_entities()` | NodeRef, TargetRef, DurationSpec, Severity mapping |
| `test_gazetteer.py` | `IncidentParser.gazetteer` | Exact match, fuzzy match (typo), multi-match, no match |
| `test_guardrails.py` | `check_permission()` | All 4 roles × 17 intents = 68 combinations |
| `test_clarification.py` | `ClarificationEngine` | Multi-match detection, option format, re-execution |
| `test_audit_logger.py` | `AuditLogger` | Hash chain integrity, rotation, concurrent writes |

### 3.2 Routing Engine (`engine/tests/`)

| Test File | Target | Key Cases |
|-----------|--------|-----------|
| `test_pathfinder_constrained.cpp` | `compute_path_constrained()` | Avoid single/multi, Via single/multi, Combined, No path |
| `test_scenario_manager.cpp` | `ScenarioManager` | Apply/remove/expiry, composite multipliers, edge deltas |
| `test_driver_session.cpp` | `DriverSessionManager` | Register, constraints, subscription, cleanup |
| `test_edge_weights.cpp` | `Graph::get_effective_multiplier()` | Base, congestion, scenario, incident, composite |

### 3.3 Dashboard (`dashboard/src/`)

| Test File | Target | Key Cases |
|-----------|--------|-----------|
| `ChatBotPanel.test.tsx` | ChatBotPanel | Role selection, message send, clarification dialog, route display |
| `ClarificationDialog.test.tsx` | ClarificationDialog | Option rendering, selection, cancel, timeout |
| `useWebSocket.test.ts` | `useWebSocket` hook | New message types: route_update, scenario_changed, driver_registered |
| `auditLogViewer.test.tsx` | AuditLogViewer | Table render, sorting, pagination, export |

### 3.4 Gateway (`gateway/`)

| Test File | Target | Key Cases |
|-----------|--------|-----------|
| `test_auth_extended.py` | `auth.py` | Driver role login, JWT claims, require_role driver |
| `test_rate_limiter.py` | `platform_services.py` | Token bucket, per-user limits, 429 response |

---

## 4. NLP Intent Accuracy Tests

### 4.1 Test Dataset

**File:** `ml/nlp/test_data/intent_test_set.json`

```json
[
  {
    "utterance": "best route to Junction 42",
    "expected_intent": "route_request",
    "expected_entities": { "destination": { "id": 42 } },
    "role": "driver"
  },
  {
    "utterance": "avoid Junction A and Junction B",
    "expected_intent": "avoid_node",
    "expected_entities": { "nodes": [{ "id": 12 }, { "id": 45 }] },
    "role": "driver"
  },
  {
    "utterance": "bridge at Junction A under construction, heavy traffic",
    "expected_intent": "scenario_update",
    "expected_entities": { 
      "target": { "type": "junction", "junction_id": 12 },
      "operation": "reduce_capacity",
      "severity": 0.7
    },
    "role": "admin"
  },
  {
    "utterance": "what's the citywide average wait time",
    "expected_intent": "query_efficiency",
    "expected_entities": { "metric": "avg_wait" },
    "role": "admin"
  }
]
```

### 4.2 Accuracy Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Intent Classification Accuracy** | ≥ 95% | Held-out test set (500 utterances) |
| **Entity Extraction F1** | ≥ 90% | Per-entity micro-F1 |
| **Clarification Trigger Rate** | < 5% | Ambiguous utterances in test set |
| **Guardrail False Positive** | 0% | All 68 role×intent combos |
| **Guardrail False Negative** | 0% | All denied intents correctly blocked |

### 4.3 Test Execution

```bash
# Unit tests
python -m pytest ml/nlp/tests/test_intent_classifier.py -v
python -m pytest ml/nlp/tests/test_entity_extractor.py -v
python -m pytest ml/nlp/tests/test_guardrails.py -v

# Accuracy benchmark
python -m pytest ml/nlp/tests/test_accuracy_benchmark.py -v \
  --dataset=ml/nlp/test_data/intent_test_set.json \
  --threshold=0.95
```

---

## 5. Routing Correctness Tests

### 5.1 Correctness Properties

| Property | Test Method |
|----------|-------------|
| **Optimal path** | Compare A* result vs Dijkstra on small graph (100 nodes) |
| **Avoid constraint** | Verify no avoided node in result path |
| **Via constraint** | Verify all via nodes in path, in order |
| **Combined constraints** | Verify both avoid + via satisfied |
| **No path detection** | Disconnected graph after pruning → error |
| **Determinism** | Same input → same path (no stochastic noise for driver routes) |

### 5.2 Test Graphs

| Graph | Nodes | Edges | Purpose |
|-------|-------|-------|---------|
| `toy_grid_4x4` | 16 | 24 | Unit test fixture (deterministic) |
| `chicago_subgraph` | 1,000 | 2,000 | Integration test (real topology) |
| `chicago_full` | 29,733 | 54,210 | Performance benchmark |

### 5.3 Test Cases (GoogleTest)

```cpp
// engine/tests/test_pathfinder_constrained.cpp

TEST(PathfinderConstrained, AvoidSingleNode) {
    // Graph: 1-2-3-4, avoid 2
    // Expected path: 1-5-6-4 (alternative)
    auto path = pathfinder.compute_path_constrained(1, 4, {2}, {});
    EXPECT_FALSE(std::find(path.begin(), path.end(), 2) != path.end());
    EXPECT_EQ(path.front(), 1);
    EXPECT_EQ(path.back(), 4);
}

TEST(PathfinderConstrained, ViaNodesInOrder) {
    // Graph with waypoints
    auto path = pathfinder.compute_path_constrained(1, 10, {}, {5, 7});
    auto it5 = std::find(path.begin(), path.end(), 5);
    auto it7 = std::find(path.begin(), path.end(), 7);
    EXPECT_TRUE(it5 != path.end());
    EXPECT_TRUE(it7 != path.end());
    EXPECT_LT(std::distance(path.begin(), it5), std::distance(path.begin(), it7));
}

TEST(PathfinderConstrained, AvoidAndViaCombined) {
    auto path = pathfinder.compute_path_constrained(1, 10, {3}, {5});
    // Path must include 5, exclude 3
    EXPECT_TRUE(std::find(path.begin(), path.end(), 5) != path.end());
    EXPECT_FALSE(std::find(path.begin(), path.end(), 3) != path.end());
}

TEST(PathfinderConstrained, NoPathWhenFullyBlocked) {
    // Graph where avoid nodes disconnect origin/dest
    auto path = pathfinder.compute_path_constrained(1, 4, {2, 3}, {});
    EXPECT_TRUE(path.empty());  // Error: no path
}
```

### 5.4 Regression Tests

- **Baseline:** Current `compute_path()` and `compute_path_stochastic()` outputs preserved
- **Run:** `ctest -R Pathfinder` before and after changes
- **Compare:** Path equality for same origin/dest (no constraints)

---

## 6. Dynamic Reroute Tests

### 6.1 Trigger Scenarios

| Test | Trigger | Expected |
|------|---------|----------|
| `reroute_on_scenario_apply` | Admin applies scenario on driver's path | Driver receives `route_update` with new path, `reason="scenario"` |
| `reroute_on_incident` | NLP incident on driver's path | Driver rerouted, `reason="incident"` |
| `reroute_on_incident_expiry` | Incident timer expires | Driver rerouted back (if better), `reason="incident"` |
| `reroute_on_constraint_change` | Driver adds avoid node | Immediate reroute, `reason="constraint"` |
| `reroute_congestion_shift` | Significant congestion change (engine-detected) | Batched reroute, `reason="congestion"` |
| `no_reroute_unaffected` | Scenario on unrelated edges | Driver NOT rerouted |

### 6.2 Batch Reroute Tests

```cpp
// engine/tests/test_dynamic_reroute.cpp

TEST(DynamicReroute, BatchReroutePriority) {
    // 100 drivers affected, varying delay deltas
    // Verify top 20% (highest delay) rerouted first
    scenario_manager.apply_scenario(edges, 0.7, 3600);
    driver_manager.notify_affected(edges);
    
    auto reroute_order = driver_manager.get_last_reroute_order();
    // Check ordering by estimated_delay_delta descending
    for (size_t i = 1; i < reroute_order.size(); ++i) {
        EXPECT_GE(reroute_order[i-1].delay_delta, reroute_order[i].delay_delta);
    }
}

TEST(DynamicReroute, BatchChunking) {
    // 1000 drivers, verify chunked processing (50 per tick)
    // No single tick exceeds 16ms budget
    scenario_manager.apply_scenario(edges, 0.7, 3600);
    auto start = std::chrono::steady_clock::now();
    driver_manager.notify_affected(edges);
    // Wait for completion
    while (driver_manager.pending_reroutes() > 0) engine.tick();
    auto elapsed = std::chrono::steady_clock::now() - start;
    EXPECT_LT(elapsed.count(), 5000ms);  // < 5s for 1000
}
```

### 6.3 Conflict Resolution Tests

```cpp
TEST(ConflictResolution, SimultaneousRerouteDiversification) {
    // 50 drivers on same corridor, scenario forces alternate
    // Verify paths diversify (stochastic noise applied)
    std::set<std::vector<int64_t>> unique_paths;
    for (auto& driver : affected_drivers) {
        unique_paths.insert(driver.current_path);
    }
    // At least 3 distinct paths for 50 drivers
    EXPECT_GE(unique_paths.size(), 3);
}
```

---

## 7. Role-Permission Tests

### 7.1 Authorization Test Matrix

**File:** `ml/nlp/tests/test_guardrails.py`

```python
import pytest
from nlp.chat_service import check_permission

ROLE_INTENT_MATRIX = {
    "driver": {"route_request", "avoid_node", "via_node", "clear_constraints", "query_my_route", "query_traffic", "help"},
    "admin": {"scenario_update", "query_efficiency", "query_incidents", "cancel_scenario", "query_zone", "broadcast_alert", "help", "query_traffic"},
    "editor": {"scenario_update", "query_efficiency", "query_incidents", "cancel_scenario", "query_zone", "help", "query_traffic"},
    "viewer": {"query_efficiency", "query_incidents", "query_zone", "help", "query_traffic"},
}

@pytest.mark.parametrize("role,allowed_intents", ROLE_INTENT_MATRIX.items())
def test_role_allows_intents(role, allowed_intents):
    all_intents = {"route_request", "avoid_node", "via_node", "clear_constraints", "query_my_route", 
                   "query_traffic", "help", "scenario_update", "query_efficiency", "query_incidents",
                   "cancel_scenario", "query_zone", "broadcast_alert"}
    for intent in all_intents:
        allowed, _ = check_permission(role, intent)
        if intent in allowed_intents:
            assert allowed, f"Role {role} should allow {intent}"
        else:
            assert not allowed, f"Role {role} should deny {intent}"

def test_guardrail_audit_log_on_denial():
    # Verify audit log entry created on denial
    from nlp.audit_logger import AuditLogger
    logger = AuditLogger()
    log_id = logger.log_guardrail_denial(
        user={"username": "driver1", "role": "driver"},
        intent="scenario_update",
        raw_text="close the bridge"
    )
    # Verify log entry exists and has correct fields
    with open(AUDIT_LOG_PATH) as f:
        lines = f.readlines()
    last = json.loads(lines[-1])
    assert last["event_type"] == "guardrail_denial"
    assert last["user"]["role"] == "driver"
    assert last["request"]["intent"] == "scenario_update"
    assert last["result"] == "denied"
```

### 7.2 Engine-Level Authorization Tests

```cpp
// engine/tests/test_driver_auth.cpp

TEST(DriverAuth, DriverCanRegister) {
    ws.send(R"({"type":"driver_register","driver_id":"drv_test","agent_id":42})");
    auto msg = ws.receive();
    EXPECT_EQ(msg["type"], "driver_registered");
    EXPECT_EQ(msg["status"], "ok");
}

TEST(DriverAuth, AdminCannotRegisterDriver) {
    // Simulate admin role sending driver_register
    ws.send(R"({"type":"driver_register","driver_id":"drv_test","agent_id":42})");
    // With admin role headers
    auto msg = ws.receive();
    EXPECT_EQ(msg["type"], "error");
    EXPECT_EQ(msg["code"], 4002);
}

TEST(DriverAuth, DriverCannotApplyScenario) {
    ws.send(R"({"type":"apply_scenario","edges":[42],"severity":0.7,"duration_s":3600})");
    auto msg = ws.receive();
    EXPECT_EQ(msg["type"], "error");
    EXPECT_EQ(msg["code"], 4003);  // Forbidden
}
```

---

## 8. Load & Performance Tests

### 8.1 Benchmark Targets

| Benchmark | Target | Tool |
|-----------|--------|------|
| Single route computation (no constraints) | p95 ≤ 50 ms | `bench_routing.cpp` |
| Single route (5 avoid, 3 via) | p95 ≤ 100 ms | `bench_routing.cpp` |
| Scenario apply + notify (10 edges) | p95 ≤ 200 ms | `bench_scenario.cpp` |
| 100 drivers reroute | p95 ≤ 500 ms | `bench_reroute.cpp` |
| 1000 drivers reroute | p95 ≤ 5 s | `bench_reroute.cpp` |
| NLP intent classification (rule-based) | p95 ≤ 10 ms | `pytest --benchmark` |
| NLP intent classification (LLM) | p95 ≤ 2 s | `pytest --benchmark` |
| Chatbot E2E (utterance → map update) | p95 ≤ 2 s | Playwright E2E |

### 8.2 Benchmark Implementation

```cpp
// engine/bench/bench_routing.cpp
#include <benchmark/benchmark.h>
#include "Pathfinder.h"

static void BM_RouteRequest_NoConstraints(benchmark::State& state) {
    Pathfinder pf(graph);  // Chicago full graph
    for (auto _ : state) {
        auto path = pf.compute_path_constrained(100, 5000, {}, {});
        benchmark::DoNotOptimize(path);
    }
}
BENCHMARK(BM_RouteRequest_NoConstraints);

static void BM_RouteRequest_WithConstraints(benchmark::State& state) {
    Pathfinder pf(graph);
    for (auto _ : state) {
        auto path = pf.compute_path_constrained(100, 5000, {12, 45, 78}, {20, 30});
        benchmark::DoNotOptimize(path);
    }
}
BENCHMARK(BM_RouteRequest_WithConstraints);

static void BM_ScenarioApply(benchmark::State& state) {
    ScenarioManager sm(graph);
    std::vector<int64_t> edges = {42, 43, 44, 45, 46, 47, 48, 49, 50, 51};
    for (auto _ : state) {
        sm.apply_scenario(edges, 0.7, 3600);
        sm.remove_scenario(edges);
    }
}
BENCHMARK(BM_ScenarioApply);
```

### 8.3 Load Test Scenarios

| Scenario | Virtual Users | Duration | Success Criteria |
|----------|---------------|----------|------------------|
| **Steady state** | 50 drivers + 5 admins | 10 min | 0 errors, p95 route < 2s |
| **Burst** | 200 drivers simultaneous route requests | 1 min | 0 errors, p95 route < 5s |
| **Scenario storm** | 10 admins applying scenarios concurrently | 5 min | 0 conflicts, all applied |
| **Mixed** | 100 drivers + 10 admins + 50 viewers | 30 min | System stable, no memory leaks |

---

## 9. Integration Tests

### 9.1 Cross-Component Tests

| Test | Components | Description |
|------|------------|-------------|
| `test_chat_to_route.py` | Dashboard → Gateway → NLP → Engine | Full driver route request flow |
| `test_admin_scenario.py` | Dashboard → Gateway → NLP → Engine | Full admin scenario flow |
| `test_clarification_flow.py` | Dashboard → NLP → Dashboard → NLP | Ambiguity resolution round-trip |
| `test_guardrail_e2e.py` | Dashboard → Gateway → NLP | Driver denied on admin intent |
| `test_audit_log_e2e.py` | NLP → Audit Log → Dashboard | Audit entry created and viewable |

### 9.2 Test Infrastructure

```yaml
# docker-compose.test.yml
services:
  engine-test:
    build: ./engine
    command: ./engine --test-mode --city=toy_grid
    ports: ["9001:9001"]
  
  nlp-test:
    build: ./ml/nlp
    command: python -m uvicorn chat_service:app --port 9004
    ports: ["9004:9004"]
    depends_on: [engine-test]
  
  gateway-test:
    build: ./gateway
    command: python -m uvicorn server:app --port 8000
    ports: ["8000:8000"]
    depends_on: [engine-test, nlp-test]
  
  dashboard-test:
    build: ./dashboard
    command: npm run test:ci
    depends_on: [gateway-test]
```

---

## 10. End-to-End Acceptance Tests

### 10.1 Acceptance Criteria (User Stories)

| User Story | Acceptance Test | Pass Criteria |
|------------|-----------------|---------------|
| **US-D1**: Driver requests route | Playwright: Open chatbot → select Driver → type "route to Junction 42" → verify route on map | Route polyline appears, ETA shown, < 2s |
| **US-D2**: Driver adds avoid constraint | Playwright: Type "avoid Junction 5" → verify route updates | New route excludes Junction 5, < 1s |
| **US-D3**: Driver adds via constraint | Playwright: Type "go through Junction 20" → verify route updates | Route includes Junction 20, < 1s |
| **US-D4**: Driver cleared constraints | Playwright: Type "clear constraints" → verify route reverts | Original route restored |
| **US-A1**: Admin applies scenario | Playwright: Select Admin → type "construction at Junction A heavy traffic" → verify scenario applied | Edge multipliers updated, drivers rerouted |
| **US-A2**: Admin queries metrics | Playwright: Type "citywide average wait time" → verify response | Correct metric value returned |
| **US-A3**: Admin cancels scenario | Playwright: Type "clear construction at Junction A" → verify removed | Multipliers reverted, drivers rerouted |
| **US-G1**: Role guardrail works | Playwright: Login as driver → type "close bridge at Junction A" → verify denial | 403 error, audit log entry |
| **US-G2**: Ambiguity handled | Playwright: Type "avoid Junction A" (3 matches) → select one → verify | Clarification dialog shown, correct node avoided |
| **US-G3**: Audit log visible | Playwright: Login as admin → open Audit Log → verify entries | Table shows scenario updates with details |

### 10.2 Playwright Test Example

```typescript
// dashboard/tests/e2e/chatbot_driver_route.spec.ts
import { test, expect } from '@playwright/test';

test('Driver can request route with avoid constraint', async ({ page }) => {
  await page.goto('http://localhost:3000');
  await login(page, 'driver1', 'driver1');
  await startSimulation(page, 'chicago');
  
  // Open chatbot
  await page.click('[data-testid="chatbot-button"]');
  await expect(page.locator('[data-testid="role-modal"]')).toBeVisible();
  await page.click('[data-testid="role-driver"]');
  await page.click('[data-testid="role-confirm"]');
  
  // Request route
  await page.fill('[data-testid="chat-input"]', 'best route to Junction 42');
  await page.click('[data-testid="chat-send"]');
  
  // Wait for route on map
  await expect(page.locator('[data-testid="route-polyline"]')).toBeVisible({ timeout: 2000 });
  await expect(page.locator('[data-testid="route-eta"]')).toContainText(/\d+ min/);
  
  // Add avoid constraint
  await page.fill('[data-testid="chat-input"]', 'avoid Junction 5');
  await page.click('[data-testid="chat-send"]');
  
  // Verify route updated
  await expect(page.locator('[data-testid="avoid-chip"]')).toContainText('Junction 5');
  await expect(page.locator('[data-testid="route-polyline"]')).toHaveAttribute('data-updated', 'true');
});
```

---

## 11. Test Data & Fixtures

### 11.1 Test Graphs

| Fixture | Location | Description |
|---------|----------|-------------|
| `toy_grid_4x4.graph.json` | `engine/tests/fixtures/` | 16 nodes, deterministic |
| `chicago_subgraph_1k.graph.json` | `engine/tests/fixtures/` | 1k nodes, real topology |
| `chicago_full.graph.json` | `data/chicago/` | Production graph |

### 11.2 Test OD Matrices

| Fixture | Location | Description |
|---------|----------|-------------|
| `toy_od.json` | `engine/tests/fixtures/` | Uniform demand |
| `chicago_od_sample.json` | `data/chicago/` | 1000 trips sample |

### 11.3 NLP Test Data

| Fixture | Location | Description |
|---------|----------|-------------|
| `intent_test_set.json` | `ml/nlp/test_data/` | 500 utterances with labels |
| `gazetteer_test_cases.json` | `ml/nlp/test_data/` | Exact/fuzzy/multi-match cases |
| `clarification_cases.json` | `ml/nlp/test_data/` | Ambiguous queries + expected options |

---

## 12. CI/CD Integration

### 12.1 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run C++ unit tests
        run: cd engine/build && ctest --output-on-failure
      - name: Run Python unit tests
        run: python -m pytest pipeline/tests/ ml/nlp/tests/ -v
      - name: Run Dashboard unit tests
        run: cd dashboard && npm run test

  integration:
    runs-on: ubuntu-latest
    needs: unit
    steps:
      - uses: actions/checkout@v4
      - name: Start test stack
        run: docker-compose -f docker-compose.test.yml up -d
      - name: Wait for services
        run: sleep 10 && curl -f http://localhost:8000/health
      - name: Run integration tests
        run: python -m pytest tests/integration/ -v
      - name: Run E2E tests
        run: cd dashboard && npm run test:e2e

  benchmark:
    runs-on: ubuntu-latest
    needs: unit
    steps:
      - uses: actions/checkout@v4
      - name: Build benchmarks
        run: cd engine/build && cmake -DBUILD_BENCHMARKS=ON .. && cmake --build .
      - name: Run routing benchmarks
        run: ./bench_routing --benchmark_format=json > bench_routing.json
      - name: Check regression
        run: python scripts/check_benchmark_regression.py bench_routing.json
```

### 12.2 Quality Gates

| Gate | Threshold | Action on Fail |
|------|-----------|----------------|
| Unit test pass rate | 100% | Block merge |
| Intent accuracy | ≥ 95% | Block merge |
| Routing p95 (no constraints) | ≤ 50 ms | Block merge |
| Routing p95 (with constraints) | ≤ 100 ms | Block merge |
| Guardrail coverage | 100% (68 combos) | Block merge |
| Audit log integrity | Hash chain valid | Block merge |
| E2E critical paths | 100% pass | Block merge |

---

## 13. Test Execution Checklist

### Pre-Commit (Local)
- [ ] `cd engine && ctest --output-on-failure` (56 tests)
- [ ] `cd pipeline && python -m pytest tests/ -v` (39 tests)
- [ ] `cd ml/nlp && python -m pytest tests/ -v` (NLP tests)
- [ ] `cd dashboard && npm run test` (Vitest)

### Pre-Merge (CI)
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Benchmarks within thresholds
- [ ] Guardrail matrix 100% covered
- [ ] Audit log hash chain verified

### Release (Manual)
- [ ] Full E2E test suite (Playwright)
- [ ] Load test: 1000 drivers + 10 admins for 10 min
- [ ] Chaos test: Engine restart mid-scenario
- [ ] Security scan: `bandit`, `semgrep`, dependency audit