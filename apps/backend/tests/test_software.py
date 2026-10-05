"""Software parity tests against a disposable PostgreSQL database."""
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.engine import make_url

from homate.bootstrap import create_app
from homate.infrastructure.postgres import household
from homate.infrastructure.postgres.connection import connect


@pytest.fixture(scope="module")
def client():
    url = os.environ.get("TEST_DATABASE_URL")
    if not url: pytest.skip("Set TEST_DATABASE_URL to a local PostgreSQL test server")
    database = "homate_test_" + uuid4().hex
    scoped = make_url(url).set(database=database).render_as_string(hide_password=False)
    with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"), autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database)))
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = scoped
    try:
        command.upgrade(Config("alembic.ini"), "head")
        with TestClient(create_app(scoped, start_workers=False)) as test_client:
            yield test_client
    finally:
        if previous is None: os.environ.pop("DATABASE_URL", None)
        else: os.environ["DATABASE_URL"] = previous
        with psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://"), autocommit=True) as conn:
            conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(database)))


@pytest.fixture
def admin(client):
    response = client.post("/api/dashboard/auth/login", json={"user_id": "minh-duc", "pin": "1234"})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_seed_matches_p072_and_startup_is_idempotent(client, admin):
    home = client.get("/api/dashboard/home").json()
    assert home["name"] == "Michelin Bois" and len(home["rooms"]) == 6
    assert {u["id"] for u in home["members"]} == {"minh-duc", "vinh", "thanh", "truong"}
    devices = client.get("/api/dashboard/devices", headers=admin).json()
    assert len(devices) == 22 and {"door", "curtain", "light-living", "ac-bed"} <= {d["id"] for d in devices}
    household.init_and_seed(client.app.state.database_url)
    assert len(household.load_devices(client.app.state.database_url)) == len(devices)
    assert client.get("/health").json()["ai_enabled"] is False


def test_auth_refresh_logout_and_member_permissions(client, admin):
    assert client.post("/api/dashboard/auth/login", json={"user_id": "minh-duc", "pin": "9999"}).status_code == 401
    assert client.get("/api/dashboard/devices").status_code == 401
    assert client.post("/api/dashboard/auth/refresh").status_code == 200
    response = client.post("/api/dashboard/auth/login", json={"user_id": "vinh", "pin": "1234"})
    member = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.get("/api/dashboard/devices", headers=member).status_code == 200
    assert client.get("/api/dashboard/users", headers=member).status_code == 403
    assert client.patch("/api/dashboard/settings", headers=member, json={"hitl_timeout_seconds": 40}).status_code == 403
    assert client.post("/api/dashboard/auth/logout").status_code == 200
    assert client.post("/api/dashboard/auth/refresh").status_code == 401


def test_manual_device_control_persists_and_validates(client, admin):
    path = "/api/dashboard/devices/light-living/actions"
    assert client.post(path, headers=admin, json={"key": "power", "value": True}).status_code == 200
    response = client.post(path, headers=admin, json={"key": "brightness", "value": 73})
    assert response.status_code == 200 and response.json()["device"]["state"]["brightness"] == 73
    saved = next(d for d in household.load_devices(client.app.state.database_url) if d.id == "light-living")
    assert saved.state["brightness"] == 73
    assert client.post(path, headers=admin, json={"key": "brightness", "value": 101}).status_code == 400
    assert client.post(path, headers=admin, json={"key": "not-a-control", "value": True}).status_code == 400
    assert client.post("/api/dashboard/devices/missing/actions", headers=admin, json={"key": "power", "value": True}).status_code == 404
    logs = client.get("/api/dashboard/command-logs", headers=admin).json()
    assert any(log["intent"] == "manual_control" for log in logs)


def test_authenticated_realtime_snapshot_and_update(client, admin):
    token = admin["Authorization"].split(" ")[1]
    with client.websocket_connect("/ws/devices?token=" + token) as websocket:
        snapshot = websocket.receive_json()
        assert snapshot["type"] == "snapshot" and len(snapshot["devices"]) > 20
        client.post("/api/dashboard/devices/light-living/actions", headers=admin, json={"key": "power", "value": False})
        event = websocket.receive_json()
        assert event["type"] == "device.updated" and event["state"]["power"] is False


def test_users_and_live_permission_changes(client, admin):
    name = "Thành viên test " + uuid4().hex[:8]
    created = client.post("/api/dashboard/users", headers=admin, json={"name": name, "role": "admin", "pin": "4321"})
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    response = client.post("/api/dashboard/auth/login", json={"user_id": identifier, "pin": "4321"})
    second = {"Authorization": "Bearer " + response.json()["access_token"]}
    assert client.get("/api/dashboard/users", headers=second).status_code == 200
    assert client.patch(f"/api/dashboard/users/{identifier}", headers=admin, json={"role": "member", "email": "test@example.com"}).status_code == 200
    assert client.get("/api/dashboard/users", headers=second).status_code == 403
    assert client.delete(f"/api/dashboard/users/{identifier}", headers=admin).status_code == 204
    assert client.get("/api/dashboard/devices", headers=second).status_code == 401
    assert client.delete("/api/dashboard/users/minh-duc", headers=admin).status_code == 400


def test_scenes_crud_validation_and_referenced_delete(client, admin):
    name = "Scene test " + uuid4().hex[:8]
    body = {"name": name, "voice_keyword": name, "steps": [{"device_id": "light-living", "action": "set_brightness", "parameters": {"brightness": 50}}]}
    created = client.post("/api/dashboard/scenes", headers=admin, json=body)
    assert created.status_code == 201, created.text
    identifier = created.json()["id"]
    response = client.put(f"/api/dashboard/scenes/{identifier}", headers=admin, json={**body, "name": "Renamed", "is_enabled": False})
    assert response.status_code == 200 and response.json()["is_enabled"] is False
    invalid = {**body, "steps": [{"device_id": "light-living", "action": "unlock", "parameters": {}}]}
    assert client.put(f"/api/dashboard/scenes/{identifier}", headers=admin, json=invalid).status_code == 400
    persisted = client.get(f"/api/dashboard/scenes/{identifier}", headers=admin).json()
    assert persisted["name"] == "Renamed" and len(persisted["steps"]) == 1
    assert client.post("/api/dashboard/scenes", headers=admin, json=body).status_code == 400
    assert client.delete(f"/api/dashboard/scenes/{identifier}", headers=admin).status_code == 204


def test_scene_conflicts_reject_incompatible_devices(client, admin):
    name = uuid4().hex
    response = client.post("/api/dashboard/scenes", headers=admin, json={"name": name, "voice_keyword": name, "steps": [{"device_id": "ac-living", "action": "turn_on"}, {"device_id": "heater-living", "action": "turn_on"}]})
    assert response.status_code == 400


def test_schedule_executes_once_and_records_history(client, admin):
    when = datetime.now(timezone.utc) - timedelta(seconds=1)
    response = client.post("/api/dashboard/schedules", headers=admin, json={"name": "Schedule test", "schedule_type": "once", "target_type": "device_action", "device_id": "light-living", "action": "turn_on", "run_at": when.isoformat()})
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    service = client.app.state.schedule_service
    assert service.execute_due(datetime.now(timezone.utc)) == 1
    assert service.execute_due(datetime.now(timezone.utc)) == 0
    runs = client.get(f"/api/dashboard/schedules/{identifier}/runs", headers=admin).json()
    assert len(runs) == 1 and runs[0]["status"] == "success"
    assert client.app.state.device_store.get("light-living").state["power"] is True
    assert client.delete(f"/api/dashboard/schedules/{identifier}", headers=admin).status_code == 204


def test_recurring_schedule_patch_validation_and_scene_reference(client, admin):
    body = {"name": "Recurring test", "schedule_type": "recurring", "target_type": "scene", "scene_id": "home", "recurrence_rule": {"frequency": "weekly", "time": "20:30", "days_of_week": [0, 2]}, "enabled": False}
    response = client.post("/api/dashboard/schedules", headers=admin, json=body)
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    assert client.patch(f"/api/dashboard/schedules/{identifier}", headers=admin, json={"enabled": True}).json()["status"] == "active"
    assert client.patch(f"/api/dashboard/schedules/{identifier}", headers=admin, json={"timezone": "invalid/zone"}).status_code == 400
    assert client.patch(f"/api/dashboard/schedules/{identifier}", headers=admin, json={"target_type": "device_action", "device_id": "light-living", "action": "unlock"}).status_code == 400
    assert client.delete("/api/dashboard/scenes/home", headers=admin).status_code == 409
    assert client.delete(f"/api/dashboard/schedules/{identifier}", headers=admin).status_code == 204


def test_settings_policies_and_room_mock_are_persistent(client, admin):
    response = client.patch("/api/dashboard/settings", headers=admin, json={"command_log_retention_days": 45, "hitl_timeout_seconds": 60})
    assert response.status_code == 200 and response.json()["hitl_timeout_seconds"] == 60
    assert client.get("/api/dashboard/settings", headers=admin).json()["command_log_retention_days"] == 45
    policies = client.get("/api/dashboard/hitl-policies", headers=admin).json()
    payload = [{"device_id": p["device_id"], "action": p["action"], "require_confirm": p["require_confirm"]} for p in policies]
    assert client.put("/api/dashboard/hitl-policies", headers=admin, json={"policies": payload}).status_code == 200
    response = client.patch("/api/dashboard/rooms/living/mock", headers=admin, json={"occupied": False, "vacant_minutes": 40, "indoor_temp_c": 31})
    assert response.status_code == 200
    room = next(r for r in response.json()["rooms"] if r["id"] == "living")
    assert room["occupied"] is False and room["vacant_minutes"] >= 40


@pytest.mark.parametrize("period", ["today", "7days", "30days", "3months", "year"])
def test_energy_reports_and_postgres_aggregation(client, admin, period):
    response = client.get("/api/dashboard/energy", headers=admin, params={"period": period, "room_id": "living"})
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["total_kwh"] >= 0 and report["source"] == "estimated"
    if period == "30days":
        assert report["total_kwh"] > 0 and len(report["timeseries"]) > 0
        result = client.app.state.energy_service.aggregate_daily_and_cleanup()
        assert result["daily_rows"] > 0


def test_ai_is_explicitly_deferred(client, admin):
    response = client.post("/api/dashboard/chat", headers=admin, json={"message": "Bật đèn"})
    assert response.status_code == 503 and "giai đoạn tiếp theo" in response.json()["detail"]
