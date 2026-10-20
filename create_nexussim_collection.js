const fs = require('fs');
const path = require('path');
const BASE = 'E:/Coding/Nexus_Sim';

function write(filePath, content) {
  const full = path.join(BASE, filePath);
  fs.mkdirSync(path.dirname(full), { recursive: true });
  fs.writeFileSync(full, content, 'utf8');
  console.log('CREATED: ' + filePath);
}

// ── Collection root ──────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/.resources/definition.yaml',
`$kind: collection
name: NexusSim API Tests
description: |-
  Full-stack API test suite for NexusSim.
  Covers Gateway (:8000), Virtual Camera (:9003), NLP Chat (:9004),
  Event Bus (:9005), Algo Explorer (:9006), Dashboard (:3000), and Engine (:9001).
variables:
  - key: gateway
    value: 'http://localhost:8000'
  - key: camera
    value: 'http://localhost:9003'
  - key: nlp
    value: 'http://localhost:9004'
  - key: event_bus
    value: 'http://localhost:9005'
  - key: algo
    value: 'http://localhost:9006'
  - key: dashboard
    value: 'http://localhost:3000'
`);

// ── A - Gateway ──────────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/A - Gateway/.resources/definition.yaml',
`$kind: collection
name: 'A - Gateway (:8000)'
order: 1000
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A1 - GET health.request.yaml',
`$kind: http-request
name: 'A1 - GET /api/health'
order: 1000
method: GET
url: '{{gateway}}/api/health'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('A1 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('A1 - Has services object', () => { pm.expect(pm.response.json()).to.have.property('services'); });
      pm.test('A1 - camera is healthy', () => { pm.expect(pm.response.json().services.camera).to.eql('healthy'); });
      pm.test('A1 - nlp is healthy', () => { pm.expect(pm.response.json().services.nlp).to.eql('healthy'); });
      pm.test('A1 - event_bus is healthy', () => { pm.expect(pm.response.json().services.event_bus).to.eql('healthy'); });
      pm.test('A1 - algo_explorer is healthy', () => { pm.expect(pm.response.json().services.algo_explorer).to.eql('healthy'); });
      pm.test('A1 - engine key exists', () => { pm.expect(pm.response.json().services).to.have.property('engine'); });
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A2 - POST chat.request.yaml',
`$kind: http-request
name: 'A2 - POST /api/chat'
order: 2000
method: POST
url: '{{gateway}}/api/chat'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "query": "what is the average wait time",
      "city": "chicago"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('A2 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('A2 - Has intent', () => { pm.expect(pm.response.json()).to.have.property('intent'); });
      pm.test('A2 - Has answer', () => { pm.expect(pm.response.json()).to.have.property('answer'); });
      pm.test('A2 - Has confidence', () => { pm.expect(pm.response.json()).to.have.property('confidence'); });
      pm.test('A2 - Has handler', () => { pm.expect(pm.response.json()).to.have.property('handler'); });
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A3 - POST incident.request.yaml',
`$kind: http-request
name: 'A3 - POST /api/incident'
order: 3000
method: POST
url: '{{gateway}}/api/incident'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "text": "accident on main street",
      "city": "chicago"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('A3 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('A3 - Has status', () => { pm.expect(pm.response.json()).to.have.property('status'); });
      pm.test('A3 - Has message', () => { pm.expect(pm.response.json()).to.have.property('message'); });
      pm.test('A3 - Has incident_spec', () => { pm.expect(pm.response.json()).to.have.property('incident_spec'); });
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A4 - GET camera feed.request.yaml',
`$kind: http-request
name: 'A4 - GET /api/camera/feed'
order: 4000
method: GET
url: '{{gateway}}/api/camera/feed'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('A4 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('A4 - Content-Type is application/json', () => { pm.expect(pm.response.headers.get('Content-Type')).to.include('application/json'); });
      pm.test('A4 - Body > 10 KB', () => { pm.expect(pm.response.responseSize).to.be.above(10240); });
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A5 - GET algo.request.yaml',
`$kind: http-request
name: 'A5 - GET /api/algo'
order: 5000
method: GET
url: '{{gateway}}/api/algo'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('A5 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('A5 - Returns 48 algorithms', () => {
        const json = pm.response.json();
        const arr = Array.isArray(json) ? json : json.algorithms;
        pm.expect(arr).to.be.an('array').with.lengthOf(48);
      });
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A6 - POST events publish.request.yaml',
`$kind: http-request
name: 'A6 - POST /api/events/publish/cv.anomaly'
order: 6000
method: POST
url: '{{gateway}}/api/events/publish/cv.anomaly'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "message": "test anomaly",
      "severity": "low"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('A6 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('A6 - Has status', () => { pm.expect(pm.response.json()).to.have.property('status'); });
      pm.test('A6 - Has topic', () => { pm.expect(pm.response.json()).to.have.property('topic'); });
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A7 - WS gateway.request.yaml',
`$kind: websocket-request
name: 'A7 - WS ws://localhost:8000/ws'
order: 7000
url: 'ws://localhost:8000/ws'
`);

write('postman/collections/NexusSim API Tests/A - Gateway/A8 - WS events.request.yaml',
`$kind: websocket-request
name: 'A8 - WS ws://localhost:8000/ws/events'
order: 8000
url: 'ws://localhost:8000/ws/events'
`);

// ── B - Virtual Camera ───────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/B - Virtual Camera/.resources/definition.yaml',
`$kind: collection
name: 'B - Virtual Camera (:9003)'
order: 2000
`);

write('postman/collections/NexusSim API Tests/B - Virtual Camera/B9 - GET health.request.yaml',
`$kind: http-request
name: 'B9 - GET /health'
order: 1000
method: GET
url: '{{camera}}/health'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('B9 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('B9 - status is ok', () => { pm.expect(pm.response.json().status).to.eql('ok'); });
      pm.test('B9 - service is virtual_camera', () => { pm.expect(pm.response.json().service).to.eql('virtual_camera'); });
      pm.test('B9 - port is 9003', () => { pm.expect(pm.response.json().port).to.eql(9003); });
`);

write('postman/collections/NexusSim API Tests/B - Virtual Camera/B10 - GET camera feed.request.yaml',
`$kind: http-request
name: 'B10 - GET /api/camera/feed'
order: 2000
method: GET
url: '{{camera}}/api/camera/feed'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('B10 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('B10 - Content-Type is application/json', () => { pm.expect(pm.response.headers.get('Content-Type')).to.include('application/json'); });
      pm.test('B10 - Body > 10 KB', () => { pm.expect(pm.response.responseSize).to.be.above(10240); });
`);

// ── C - NLP Chat ─────────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/C - NLP Chat/.resources/definition.yaml',
`$kind: collection
name: 'C - NLP Chat (:9004)'
order: 3000
`);

write('postman/collections/NexusSim API Tests/C - NLP Chat/C11 - GET health.request.yaml',
`$kind: http-request
name: 'C11 - GET /health'
order: 1000
method: GET
url: '{{nlp}}/health'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('C11 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('C11 - status is ok', () => { pm.expect(pm.response.json().status).to.eql('ok'); });
      pm.test('C11 - service is nlp_chat', () => { pm.expect(pm.response.json().service).to.eql('nlp_chat'); });
      pm.test('C11 - port is 9004', () => { pm.expect(pm.response.json().port).to.eql(9004); });
`);

write('postman/collections/NexusSim API Tests/C - NLP Chat/C12 - POST chat.request.yaml',
`$kind: http-request
name: 'C12 - POST /chat'
order: 2000
method: POST
url: '{{nlp}}/chat'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "query": "set signal mode fuzzy",
      "city": "chicago"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('C12 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('C12 - Has intent', () => { pm.expect(pm.response.json()).to.have.property('intent'); });
      pm.test('C12 - Has answer', () => { pm.expect(pm.response.json()).to.have.property('answer'); });
      pm.test('C12 - Has confidence', () => { pm.expect(pm.response.json()).to.have.property('confidence'); });
      pm.test('C12 - Has handler', () => { pm.expect(pm.response.json()).to.have.property('handler'); });
`);

write('postman/collections/NexusSim API Tests/C - NLP Chat/C13 - POST incident.request.yaml',
`$kind: http-request
name: 'C13 - POST /incident'
order: 3000
method: POST
url: '{{nlp}}/incident'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "text": "road closed at 5th avenue",
      "city": "chicago"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('C13 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('C13 - Has status', () => { pm.expect(pm.response.json()).to.have.property('status'); });
      pm.test('C13 - Has message', () => { pm.expect(pm.response.json()).to.have.property('message'); });
      pm.test('C13 - Has incident_spec', () => { pm.expect(pm.response.json()).to.have.property('incident_spec'); });
`);

write('postman/collections/NexusSim API Tests/C - NLP Chat/C14 - POST feedback.request.yaml',
`$kind: http-request
name: 'C14 - POST /feedback'
order: 4000
method: POST
url: '{{nlp}}/feedback'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "text": "the simulation is great",
      "city": "chicago"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('C14 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('C14 - Has category', () => { pm.expect(pm.response.json()).to.have.property('category'); });
      pm.test('C14 - Has city', () => { pm.expect(pm.response.json()).to.have.property('city'); });
      pm.test('C14 - Has sentiment', () => { pm.expect(pm.response.json()).to.have.property('sentiment'); });
      pm.test('C14 - Has status', () => { pm.expect(pm.response.json()).to.have.property('status'); });
      pm.test('C14 - Has text', () => { pm.expect(pm.response.json()).to.have.property('text'); });
`);

// ── D - Event Bus ────────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/D - Event Bus/.resources/definition.yaml',
`$kind: collection
name: 'D - Event Bus (:9005)'
order: 4000
`);

write('postman/collections/NexusSim API Tests/D - Event Bus/D15 - GET health.request.yaml',
`$kind: http-request
name: 'D15 - GET /health'
order: 1000
method: GET
url: '{{event_bus}}/health'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('D15 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('D15 - status is ok', () => { pm.expect(pm.response.json().status).to.eql('ok'); });
      pm.test('D15 - service is cross_subject_event_bus', () => { pm.expect(pm.response.json().service).to.eql('cross_subject_event_bus'); });
      pm.test('D15 - port is 9005', () => { pm.expect(pm.response.json().port).to.eql(9005); });
`);

write('postman/collections/NexusSim API Tests/D - Event Bus/D16 - GET events.request.yaml',
`$kind: http-request
name: 'D16 - GET /events'
order: 2000
method: GET
url: '{{event_bus}}/events'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('D16 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('D16 - Returns an array', () => { pm.expect(pm.response.json()).to.be.an('array'); });
`);

write('postman/collections/NexusSim API Tests/D - Event Bus/D17 - POST publish.request.yaml',
`$kind: http-request
name: 'D17 - POST /publish/cv.anomaly'
order: 3000
method: POST
url: '{{event_bus}}/publish/cv.anomaly'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "message": "test anomaly",
      "severity": "low"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('D17 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('D17 - status is published', () => { pm.expect(pm.response.json().status).to.eql('published'); });
      pm.test('D17 - topic is cv.anomaly', () => { pm.expect(pm.response.json().topic).to.eql('cv.anomaly'); });
`);

write('postman/collections/NexusSim API Tests/D - Event Bus/D18 - WS event bus.request.yaml',
`$kind: websocket-request
name: 'D18 - WS ws://localhost:9005/ws'
order: 4000
url: 'ws://localhost:9005/ws'
`);

// ── E - Algo Explorer ────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/E - Algo Explorer/.resources/definition.yaml',
`$kind: collection
name: 'E - Algo Explorer (:9006)'
order: 5000
`);

write('postman/collections/NexusSim API Tests/E - Algo Explorer/E19 - GET health.request.yaml',
`$kind: http-request
name: 'E19 - GET /health'
order: 1000
method: GET
url: '{{algo}}/health'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('E19 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('E19 - status is ok', () => { pm.expect(pm.response.json().status).to.eql('ok'); });
      pm.test('E19 - service is algo_explorer', () => { pm.expect(pm.response.json().service).to.eql('algo_explorer'); });
      pm.test('E19 - port is 9006', () => { pm.expect(pm.response.json().port).to.eql(9006); });
      pm.test('E19 - total_algorithms is 48', () => { pm.expect(pm.response.json().total_algorithms).to.eql(48); });
`);

write('postman/collections/NexusSim API Tests/E - Algo Explorer/E20 - GET algorithms.request.yaml',
`$kind: http-request
name: 'E20 - GET /algorithms'
order: 2000
method: GET
url: '{{algo}}/algorithms'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('E20 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('E20 - Returns array of 48', () => {
        pm.expect(pm.response.json()).to.be.an('array').with.lengthOf(48);
      });
      pm.test('E20 - Each item has required fields', () => {
        pm.response.json().forEach(item => {
          pm.expect(item).to.have.property('id');
          pm.expect(item).to.have.property('name');
          pm.expect(item).to.have.property('category');
          pm.expect(item).to.have.property('status');
          pm.expect(item).to.have.property('latency_ms');
          pm.expect(item).to.have.property('metric');
        });
      });
`);

write('postman/collections/NexusSim API Tests/E - Algo Explorer/E21a - POST toggle disable.request.yaml',
`$kind: http-request
name: 'E21a - POST /algorithms/toggle (disable CV-1)'
order: 3000
method: POST
url: '{{algo}}/algorithms/toggle'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "algo_id": "CV-1",
      "active": false
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('E21a - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('E21a - status is updated', () => { pm.expect(pm.response.json().status).to.eql('updated'); });
      pm.test('E21a - algo status is DISABLED', () => { pm.expect(pm.response.json().algo.status).to.eql('DISABLED'); });
`);

write('postman/collections/NexusSim API Tests/E - Algo Explorer/E21b - POST toggle restore.request.yaml',
`$kind: http-request
name: 'E21b - POST /algorithms/toggle (restore CV-1)'
order: 4000
method: POST
url: '{{algo}}/algorithms/toggle'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "algo_id": "CV-1",
      "active": true
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('E21b - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('E21b - status is updated', () => { pm.expect(pm.response.json().status).to.eql('updated'); });
      pm.test('E21b - algo status is ACTIVE', () => { pm.expect(pm.response.json().algo.status).to.eql('ACTIVE'); });
`);

// ── F - Dashboard ────────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/F - Dashboard/.resources/definition.yaml',
`$kind: collection
name: 'F - Dashboard (:3000)'
order: 6000
`);

write('postman/collections/NexusSim API Tests/F - Dashboard/F22 - GET root.request.yaml',
`$kind: http-request
name: 'F22 - GET /'
order: 1000
method: GET
url: '{{dashboard}}/'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('F22 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('F22 - HTML contains id=root', () => { pm.expect(pm.response.text()).to.include('id="root"'); });
`);

write('postman/collections/NexusSim API Tests/F - Dashboard/F23 - GET algo matrix json.request.yaml',
`$kind: http-request
name: 'F23 - GET /data/36_algo_matrix.json'
order: 2000
method: GET
url: '{{dashboard}}/data/36_algo_matrix.json'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('F23 - Status 200', () => { pm.response.to.have.status(200); });
      pm.test('F23 - total_algorithms is 48', () => { pm.expect(pm.response.json().total_algorithms).to.eql(48); });
      pm.test('F23 - Has metrics_provenance', () => { pm.expect(pm.response.json()).to.have.property('metrics_provenance'); });
`);

// ── G - Engine Direct ────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/G - Engine Direct/.resources/definition.yaml',
`$kind: collection
name: 'G - Engine Direct (:9001)'
order: 7000
`);

write('postman/collections/NexusSim API Tests/G - Engine Direct/G24 - WS engine.request.yaml',
`$kind: websocket-request
name: 'G24 - WS ws://localhost:9001'
order: 1000
url: 'ws://localhost:9001'
`);

// ── H - Edge Cases ───────────────────────────────────────────────────────────
write('postman/collections/NexusSim API Tests/H - Edge Cases/.resources/definition.yaml',
`$kind: collection
name: 'H - Edge Cases'
order: 8000
`);

write('postman/collections/NexusSim API Tests/H - Edge Cases/H25 - POST chat wrong field.request.yaml',
`$kind: http-request
name: 'H25 - POST /api/chat (wrong field -> 422)'
order: 1000
method: POST
url: '{{gateway}}/api/chat'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "message": "x"
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('H25 - Expect 422 for wrong field', () => { pm.response.to.have.status(422); });
`);

write('postman/collections/NexusSim API Tests/H - Edge Cases/H26 - POST algo toggle wrong fields.request.yaml',
`$kind: http-request
name: 'H26 - POST /api/algo/toggle (wrong fields -> 422)'
order: 2000
method: POST
url: '{{gateway}}/api/algo/toggle'
headers:
  - key: Content-Type
    value: application/json
body:
  type: json
  content: |-
    {
      "id": "CV-1",
      "enabled": false
    }
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('H26 - Expect 422 for wrong fields', () => { pm.response.to.have.status(422); });
`);

write('postman/collections/NexusSim API Tests/H - Edge Cases/H27 - GET events no path.request.yaml',
`$kind: http-request
name: 'H27 - GET /api/events (no path -> 404)'
order: 3000
method: GET
url: '{{gateway}}/api/events'
scripts:
  - type: afterResponse
    language: text/javascript
    code: |-
      pm.test('H27 - Expect 404 for missing path segment', () => { pm.response.to.have.status(404); });
`);

console.log('\nALL FILES CREATED SUCCESSFULLY');
