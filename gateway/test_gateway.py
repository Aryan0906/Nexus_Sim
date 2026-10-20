"""Tests for NexusSim Unified Backend Gateway (Port 8000)."""

import pytest
from fastapi.testclient import TestClient
from gateway.server import app

client = TestClient(app)


def test_gateway_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 8000
    assert "services" in data
    assert "gateway" in data


def test_gateway_chat_offline_graceful():
    # The gateway must never crash or hang on a chat request: with the
    # upstream down it returns 502/503; with the upstream up it proxies the
    # real response (e.g. 422 for a schema mismatch). Any HTTP status is fine.
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code in [200, 404, 422, 502, 503]


def test_gateway_incident_offline_graceful():
    response = client.post("/api/incident", json={"text": "crash on loop"})
    assert response.status_code in [200, 404, 422, 502, 503]


def test_gateway_algo_offline_graceful():
    response = client.get("/api/algo/matrix")
    assert response.status_code in [200, 404, 422, 502, 503]


def test_event_bus_ws_url_matches_upstream_route():
    # Regression: the gateway proxies /ws/events to EVENT_BUS_WS_URL, but the
    # event bus serves its stream at /ws (not /ws/events). A mismatch makes the
    # proxy close every client connection with "Event bus offline: HTTP 403".
    from gateway import server
    assert server.EVENT_BUS_WS_URL.rstrip("/").endswith("/ws")
