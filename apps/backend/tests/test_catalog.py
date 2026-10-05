"""Integration tests run against PostgreSQL in a unique, disposable schema."""
import os
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from homate.bootstrap import create_catalog_app as create_app


@pytest.fixture
def client(monkeypatch):
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set TEST_DATABASE_URL to an isolated PostgreSQL database")
    schema = "test_" + uuid4().hex
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = make_url(url).update_query_dict({"options": f"-csearch_path={schema}"}).render_as_string(hide_password=False)
    monkeypatch.setenv("DATABASE_URL", scoped_url)
    try:
        command.upgrade(Config("alembic.ini"), "0001")
        with TestClient(create_app(scoped_url)) as test_client:
            yield test_client
    finally:
        with engine.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        engine.dispose()


def create(client, resource, **body):
    response = client.post(f"/api/{resource}", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def graph(client):
    home = create(client, "homes", name="Nhà của tôi")
    room = create(client, "rooms", name="Phòng khách", home_id=home["id"])
    device = create(client, "devices", name="Đèn", home_id=home["id"], room_id=room["id"], kind="light", capabilities=["turn_on", "turn_off"])
    return home, room, device


def test_crud_persistence_and_delete_dependencies(client):
    home, room, device = graph(client)
    scene_body = dict(name="Buổi sáng", home_id=home["id"], is_enabled=True,
                      steps=[dict(device_id=device["id"], action="turn_on", parameters={"brightness": 50})])
    scene = create(client, "scenes", **scene_body)
    assert client.get(f"/api/scenes/{scene['id']}").json()["steps"] == scene_body["steps"]
    assert client.get(f"/api/devices?home_id={home['id']}").json()[0]["id"] == device["id"]
    for kind, item in [("homes", home), ("rooms", room), ("devices", device)]:
        assert client.delete(f"/api/{kind}/{item['id']}").status_code == 409
    scene_body.update(name="Buổi tối", steps=[dict(device_id=device["id"], action="turn_off", parameters={})])
    assert client.put(f"/api/scenes/{scene['id']}", json=scene_body).status_code == 200
    assert client.get(f"/api/scenes/{scene['id']}").json()["steps"][0]["action"] == "turn_off"
    for kind, item in [("scenes", scene), ("devices", device), ("rooms", room), ("homes", home)]:
        assert client.delete(f"/api/{kind}/{item['id']}").status_code == 204
        assert client.get(f"/api/{kind}/{item['id']}").status_code == 404


def test_validation_and_home_boundaries(client):
    home, room, device = graph(client)
    other = create(client, "homes", name="Nhà khác")
    assert client.post("/api/homes", json={"name": "   "}).status_code == 422
    assert client.post("/api/homes", json={"name": "Bad", "timezone": "not/a-zone"}).status_code == 422
    assert client.post("/api/devices", json=dict(name="Sai nhà", home_id=other["id"], room_id=room["id"], kind="light")).status_code == 422
    assert client.post("/api/scenes", json=dict(name="Sai nhà", home_id=other["id"], steps=[dict(device_id=device["id"], action="turn_on")])).status_code == 422
    assert client.post("/api/scenes", json=dict(name="Sai hành động", home_id=home["id"], steps=[dict(device_id=device["id"], action="unlock")])).status_code == 422
    assert client.get(f"/api/devices?home_id={other['id']}").json() == []
    assert client.post("/api/rooms", json=dict(name=room["name"], home_id=home["id"])).status_code == 409
    assert client.get("/api/rooms/not-a-uuid").status_code == 422


def test_failed_scene_update_is_atomic_and_capabilities_are_protected(client):
    home, room, device = graph(client)
    scene = create(client, "scenes", name="Một", home_id=home["id"], steps=[dict(device_id=device["id"], action="turn_on")])
    create(client, "scenes", name="Hai", home_id=home["id"])
    response = client.put(f"/api/scenes/{scene['id']}", json=dict(name="Hai", home_id=home["id"], steps=[]))
    assert response.status_code == 409
    persisted = client.get(f"/api/scenes/{scene['id']}").json()
    assert persisted["name"] == "Một" and len(persisted["steps"]) == 1
    assert client.put(f"/api/devices/{device['id']}", json=dict(name="Đèn", home_id=home["id"], room_id=room["id"], kind="light", capabilities=[])).status_code == 409


def test_updates_for_home_room_device_and_openapi(client):
    home, room, device = graph(client)
    assert client.put(f"/api/homes/{home['id']}", json=dict(name="Nhà mới", timezone="UTC")).json()["timezone"] == "UTC"
    assert client.put(f"/api/rooms/{room['id']}", json=dict(name="Phòng mới", home_id=home["id"])).json()["name"] == "Phòng mới"
    assert client.put(f"/api/devices/{device['id']}", json=dict(name="Đèn mới", home_id=home["id"], room_id=room["id"], kind="light", capabilities=["turn_on"])).json()["name"] == "Đèn mới"
    assert client.get("/health").json() == {"status": "ok"}
    spec = client.get("/openapi.json").json()
    assert "requestBody" in spec["paths"]["/api/devices"]["post"]
