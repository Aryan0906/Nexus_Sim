# NexusSim API Test Prompt (for Postman AI / LLM)

You are testing the NexusSim full-stack API. All services are already running.
Generate and run HTTP + WebSocket tests for every endpoint below. For each
request, assert the expected status code AND validate the response shape.
Report a PASS/FAIL table at the end; on failure show the actual response.

## Environment

- Gateway (unified entry): http://localhost:8000
- C++ Engine WS: ws://localhost:9001 (also proxied at ws://localhost:8000/ws)
- Virtual Camera: http://localhost:9003
- NLP Chat: http://localhost:9004
- Event Bus: http://localhost:9005 (WS: ws://localhost:9005/ws)
- Algo Explorer: http://localhost:9006
- Dashboard: http://localhost:3000

## Test cases

### A. Gateway (:8000)

1. GET /api/health
   - Expect 200. JSON has "services" with keys gateway, engine, camera, nlp,
     event_bus, algo_explorer. camera/nlp/event_bus/algo_explorer must be
     "healthy"; engine is "configured" (WS-only, no HTTP health) — that is OK.
2. POST /api/chat  body: {"query": "what is the average wait time", "city": "chicago"}
   - Expect 200 with keys: intent, answer, confidence, handler.
   - Note: the field is "query" (NOT "message"); "message" returns 422.
3. POST /api/incident  body: {"text": "accident on main street", "city": "chicago"}
   - Expect 200 with keys: status, message, incident_spec.
4. GET /api/camera/feed
   - Expect 200, content-type application/json, body > 10 KB (frame + blobs).
5. GET /api/algo
   - Expect 200, a JSON array (or object with "algorithms") of length 48.
6. POST /api/events/publish/cv.anomaly  body: {"message": "test anomaly", "severity": "low"}
   - Expect 200 with keys: status, topic.
   - Note: GET on /api/events/publish/... returns 405 (POST-only) — expected.
7. WS ws://localhost:8000/ws
   - Connect, send {"type":"city","city":"chicago"}, expect a JSON frame with
     "agents" (array) and "signals" (array). Then send
     {"type":"policy_switch","policy":"fuzzy"} and expect a control frame
     {"type":"policy_switched","ok":true,"mode":"fuzzy"}. Repeat for
     "type2_fuzzy" and "webster".
8. WS ws://localhost:8000/ws/events
   - Connect, POST http://localhost:9005/publish/cv.anomaly with
     {"message":"ws test","severity":"low"}, then expect a JSON frame on the WS
     with keys topic, payload, timestamp.

### B. Virtual Camera (:9003)

9.  GET /health -> 200 {"status":"ok","service":"virtual_camera","port":9003}
10. GET /api/camera/feed -> 200 application/json, > 10 KB.

### C. NLP Chat (:9004)

11. GET /health -> 200 {"status":"ok","service":"nlp_chat","port":9004}
12. POST /chat  body: {"query":"set signal mode fuzzy","city":"chicago"}
    -> 200 with keys intent, answer, confidence, handler.
13. POST /incident  body: {"text":"road closed at 5th avenue","city":"chicago"}
    -> 200 with keys status, message, incident_spec.
14. POST /feedback  body: {"text":"the simulation is great","city":"chicago"}
    -> 200 with keys category, city, sentiment, status, text.

### D. Event Bus (:9005)

15. GET /health -> 200 {"status":"ok","service":"cross_subject_event_bus","port":9005}
16. GET /events -> 200, a JSON array (may be empty).
17. POST /publish/cv.anomaly  body: {"message":"test anomaly","severity":"low"}
    -> 200 {"status":"published","topic":"cv.anomaly"}.
18. WS ws://localhost:9005/ws
    - Connect, send {"topic":"cv.anomaly","payload":{"message":"via ws"}},
      expect a frame with keys topic, payload, timestamp.

### E. Algo Explorer (:9006)

19. GET /health -> 200 {"status":"ok","service":"algo_explorer","port":9006,"total_algorithms":48}
20. GET /algorithms -> 200, array of 48 items, each with id, name, category,
    status, latency_ms, metric.
21. POST /algorithms/toggle  body: {"algo_id":"CV-1","active":false}
    -> 200 {"status":"updated","algo":{...,"status":"DISABLED"}}.
    Then POST again with {"algo_id":"CV-1","active":true} to restore ACTIVE.
    - Note: fields are "algo_id" and "active" (NOT "id"/"enabled").

### F. Dashboard (:3000)

22. GET / -> 200 HTML containing id="root".
23. GET /data/36_algo_matrix.json -> 200 JSON with total_algorithms == 48 and
    a metrics_provenance field.

### G. Engine direct (:9001)

24. WS ws://localhost:9001
    - Connect, send {"type":"city","city":"chicago"}, expect a frame with
      "agents" and "signals" arrays.

## Edge cases to also verify

- POST /api/chat with {"message":"x"} (wrong field) -> expect 422 (this is
  correct behavior; assert 422, not 200).
- POST /api/algo/toggle with {"id":"CV-1","enabled":false} -> expect 422.
- GET /api/events (no path segment) -> expect 404 (gateway route requires
  /api/events/{path}).

## Output format

For each test: ID, name, method+path, expected, actual, PASS/FAIL.
End with: TOTAL x/24 PASSED, and list any failures with their responses.
