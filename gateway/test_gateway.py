"""Tests for NexusSim Unified Backend Gateway (Port 8000)."""

import io
import os
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient
from gateway.server import app, DATA_DIR, SIMULATIONS, SCENARIOS, ENGINE_PROCESSES

client = TestClient(app)


def test_gateway_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["port"] == 8000
    assert "services" in data
    assert "gateway" in data


def test_gateway_chat_offline_graceful():
    response = client.post("/api/chat", json={"message": "hello"})
    assert response.status_code in [200, 404, 422, 502, 503]


def test_gateway_incident_offline_graceful():
    response = client.post("/api/incident", json={"text": "crash on loop"})
    assert response.status_code in [200, 404, 422, 502, 503]


def test_gateway_algo_offline_graceful():
    response = client.get("/api/algo/matrix")
    assert response.status_code in [200, 404, 422, 502, 503]


def test_event_bus_ws_url_matches_upstream_route():
    from gateway import server
    assert server.EVENT_BUS_WS_URL.rstrip("/").endswith("/ws")


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

def test_auth_login_success():
    response = client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"


def test_auth_login_failure():
    response = client.post("/api/auth/login", data={"username": "admin", "password": "wrong"})
    assert response.status_code == 401


def test_auth_me_requires_token():
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_auth_me_with_token():
    login_resp = client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
    token = login_resp.json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["username"] == "admin"


# ---------------------------------------------------------------------------
# Workspace tests
# ---------------------------------------------------------------------------

def test_list_workspaces_requires_auth():
    response = client.get("/api/workspaces")
    assert response.status_code == 401


def test_list_workspaces_with_token():
    login_resp = client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
    token = login_resp.json()["access_token"]
    response = client.get("/api/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    workspaces = response.json()
    assert isinstance(workspaces, list)
    ws_ids = {w["workspace_id"] for w in workspaces}
    assert "ws_default" in ws_ids


# ---------------------------------------------------------------------------
# City management tests
# ---------------------------------------------------------------------------

def test_list_cities_returns_list():
    response = client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    city_ids = {c["city_id"] for c in data}
    for expected in ["chicago", "paris", "ahmedabad", "piedmont"]:
        assert expected in city_ids, f"{expected} missing from city list"


def test_city_entries_have_required_fields():
    response = client.get("/api/cities")
    assert response.status_code == 200
    data = response.json()
    for city in data:
        assert "city_id" in city
        assert "city_name" in city
        assert "source" in city
        assert "status" in city


def test_get_city_existing():
    response = client.get("/api/cities/chicago")
    assert response.status_code == 200
    data = response.json()
    assert data["city_id"] == "chicago"


def test_get_city_not_found():
    response = client.get("/api/cities/nonexistent-city-xyz")
    assert response.status_code == 404


def test_upload_city_minimal_osm():
    osm_content = """<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <node id="1" lat="19.0760" lon="72.8777"/>
  <node id="2" lat="19.0770" lon="72.8787"/>
  <node id="3" lat="19.0765" lon="72.8795"/>
  <way id="10">
    <nd ref="1"/>
    <nd ref="2"/>
    <tag k="highway" v="residential"/>
  </way>
  <way id="11">
    <nd ref="2"/>
    <nd ref="3"/>
    <tag k="highway" v="residential"/>
  </way>
</osm>
"""
    test_city_id = "test-mumbai-upload"
    test_city_dir = os.path.join(DATA_DIR, test_city_id)
    if os.path.exists(test_city_dir):
        import shutil
        shutil.rmtree(test_city_dir, ignore_errors=True)

    response = client.post(
        "/api/cities/upload",
        files={"file": ("test-mumbai.osm", io.BytesIO(osm_content.encode()), "application/xml")},
        data={"city_id": test_city_id, "city_name": "Test Mumbai"},
    )
    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    assert data["city_id"] == test_city_id
    assert data["city_name"] == "Test Mumbai"
    assert data["status"] == "ready"
    assert data["node_count"] >= 1
    assert data["edge_count"] >= 1

    list_response = client.get("/api/cities")
    assert list_response.status_code == 200
    city_ids = {c["city_id"] for c in list_response.json()}
    assert test_city_id in city_ids

    get_response = client.get(f"/api/cities/{test_city_id}")
    assert get_response.status_code == 200
    assert get_response.json()["city_id"] == test_city_id


def test_upload_city_invalid_extension():
    response = client.post(
        "/api/cities/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        data={"city_id": "test-bad-ext"},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Simulation tests (require engine to be built; check gracefully)
# ---------------------------------------------------------------------------

def test_create_simulation_requires_auth():
    response = client.post("/api/simulations", data={"city_id": "chicago"})
    assert response.status_code in [401, 403]


def test_create_simulation_unknown_city():
    login_resp = client.post("/api/auth/login", data={"username": "admin", "password": "admin"})
    token = login_resp.json()["access_token"]
    response = client.post(
        "/api/simulations",
        data={"city_id": "nonexistent-city"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404


def test_create_simulation_workspace_access():
    login_resp = client.post("/api/auth/login", data={"username": "viewer", "password": "viewer"})
    token = login_resp.json()["access_token"]
    # viewer only has ws_default, should be allowed for ws_default
    response = client.post(
        "/api/simulations",
        data={"city_id": "chicago", "workspace_id": "ws_default"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # May fail if engine not built, but should not be 403/401
    assert response.status_code not in [401, 403]


def test_list_simulations_requires_auth():
    response = client.get("/api/simulations")
    assert response.status_code == 401


def test_create_scenario_requires_auth():
    response = client.post("/api/scenarios", data={"base_simulation_id": "sim_nonexistent"})
    assert response.status_code in [401, 403]
