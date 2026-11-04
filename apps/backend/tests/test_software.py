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


def propose(client, headers, tool='control_device', arguments=None, request_id=None):
    return client.post('/api/dashboard/agent/tools', headers=headers, json={
        'request_id':request_id or str(uuid4()), 'tool':tool,
        'arguments':arguments if arguments is not None else {'device_id':'light-living','action':'turn_off','parameters':{}}})


def test_agent_proposal_is_durable_and_executes_only_once(client, admin):
    store = client.app.state.device_store
    original = store.get('light-living').state['power']
    identifier = str(uuid4())
    args = {'device_id':'light-living','action':'turn_off' if original else 'turn_on','parameters':{}}
    response = propose(client, admin, arguments=args, request_id=identifier)
    assert response.status_code == 200, response.text
    pending = response.json()
    assert pending['status'] == 'pending' and store.get('light-living').state['power'] == original
    assert propose(client, admin, arguments=args, request_id=identifier).json()['id'] == pending['id']
    path = f"/api/dashboard/agent/actions/{pending['id']}/decision"
    assert client.post(path,headers=admin,json={'approved':True}).json()['status'] == 'executed'
    assert store.get('light-living').state['power'] is not original
    store.apply_action('light-living','power',original)
    assert client.post(path,headers=admin,json={'approved':True}).json()['status'] == 'executed'
    assert store.get('light-living').state['power'] == original


def test_agent_confirmation_is_user_bound_rejectable_and_expiring(client, admin):
    pending = propose(client,admin).json()
    member_login = client.post('/api/dashboard/auth/login',json={'user_id':'vinh','pin':'1234'}).json()
    member = {'Authorization':'Bearer '+member_login['access_token']}
    path = f"/api/dashboard/agent/actions/{pending['id']}/decision"
    assert client.post(path,headers=member,json={'approved':True}).status_code == 404
    assert client.post(path,headers=admin,json={'approved':False}).json()['status'] == 'rejected'
    assert client.post(path,headers=admin,json={'approved':True}).json()['status'] == 'rejected'
    pending = propose(client,admin).json()
    with connect(client.app.state.database_url) as conn:
        conn.execute("UPDATE agent_actions SET expires_at=now()-interval '1 second' WHERE id=%s",(pending['id'],))
    path = f"/api/dashboard/agent/actions/{pending['id']}/decision"
    assert client.post(path,headers=admin,json={'approved':True}).json()['status'] == 'expired'


def test_agent_tool_authorization_and_validation(client, admin):
    assert propose(client,{}).status_code == 401
    assert propose(client,admin,arguments={'device_id':'light-living','action':'set_brightness','parameters':{'brightness':999}}).status_code == 400
    identifier = str(uuid4())
    assert propose(client,admin,request_id=identifier).status_code == 200
    assert propose(client,admin,arguments={'device_id':'light-living','action':'turn_on','parameters':{}},request_id=identifier).status_code == 400
    assert propose(client,admin,'get_home_snapshot',{}).json()['devices']
    assert propose(client,admin,'get_energy_report',{'period':'today'}).json()['source'] == 'estimated'
    assert client.get('/api/dashboard/agent/identity',headers=admin).json()['role'] == 'admin'
    member = client.post('/api/dashboard/auth/login',json={'user_id':'vinh','pin':'1234'}).json()
    headers = {'Authorization':'Bearer '+member['access_token']}
    schedule = {'name':'Agent test','schedule_type':'recurring','target_type':'device_action','device_id':'light-living','action':'turn_off','recurrence_rule':{'frequency':'daily','time':'23:00'}}
    assert propose(client,headers,'create_schedule',schedule).status_code == 403
    pending = propose(client,admin,'create_schedule',schedule).json()
    response = client.post(f"/api/dashboard/agent/actions/{pending['id']}/decision",headers=admin,json={'approved':True})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'executed'
    client.delete('/api/dashboard/schedules/'+response.json()['result']['id'],headers=admin)


def test_agent_scene_executes_and_rejects_changed_scene(client, admin):
    payload = {'name':'Agent scene','voice_keyword':'agent scene','steps':[{'device_id':'light-living','action':'turn_off','parameters':{}}]}
    scene = client.post('/api/dashboard/scenes',headers=admin,json=payload).json()
    pending = propose(client,admin,'execute_scene',{'scene_id':scene['id']}).json()
    path = f"/api/dashboard/agent/actions/{pending['id']}/decision"
    assert client.post(path,headers=admin,json={'approved':True}).json()['status'] == 'executed'
    pending = propose(client,admin,'execute_scene',{'scene_id':scene['id']}).json()
    payload['name'] = 'Changed scene'
    assert client.put('/api/dashboard/scenes/'+scene['id'],headers=admin,json=payload).status_code == 200
    path = f"/api/dashboard/agent/actions/{pending['id']}/decision"
    assert client.post(path,headers=admin,json={'approved':True}).status_code == 400
    assert client.post(path,headers=admin,json={'approved':True}).json()['status'] == 'failed'
    client.delete('/api/dashboard/scenes/'+scene['id'],headers=admin)


def agent_confirm(client, headers, tool, arguments):
    proposal = propose(client,headers,tool,arguments)
    assert proposal.status_code == 200, proposal.text
    pending = proposal.json()
    assert pending['status'] == 'pending'
    response = client.post(f"/api/dashboard/agent/actions/{pending['id']}/decision",headers=headers,json={'approved':True})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'executed'
    return response.json()['result']


def test_agent_scene_management(client, admin):
    data = {'name':'Managed by agent','voice_keyword':'managed by agent','steps':[{'device_id':'light-living','action':'set_brightness','parameters':{'brightness':45}}]}
    pending = propose(client,admin,'create_scene',data).json()
    assert all(scene['name'] != data['name'] for scene in propose(client,admin,'list_scenes',{}).json()['scenes'])
    receipt = client.post(f"/api/dashboard/agent/actions/{pending['id']}/decision",headers=admin,json={'approved':True}).json()
    scene = receipt['result']
    assert scene['steps'][0]['parameters']['brightness'] == 45
    assert propose(client,admin,'get_scene',{'scene_id':scene['id']}).json()['name'] == data['name']
    updated = agent_confirm(client,admin,'update_scene',{'scene_id':scene['id'],'changes':{'name':'Renamed by agent'}})
    assert updated['name'] == 'Renamed by agent' and len(updated['steps']) == 1
    for enabled in (False,True):
        assert agent_confirm(client,admin,'set_scene_enabled',{'scene_id':scene['id'],'enabled':enabled})['is_enabled'] == enabled
    assert agent_confirm(client,admin,'delete_scene',{'scene_id':scene['id']})['deleted']
    assert propose(client,admin,'get_scene',{'scene_id':scene['id']}).status_code == 400


def test_agent_schedule_management_and_run_history(client, admin):
    when = datetime.now(timezone.utc)+timedelta(hours=2)
    data = {'name':'Managed schedule','schedule_type':'once','target_type':'device_action','device_id':'light-living','action':'turn_off','run_at':when.isoformat()}
    schedule = agent_confirm(client,admin,'create_schedule',data)
    assert schedule['id'] in {row['id'] for row in propose(client,admin,'list_schedules',{'room_id':'living','include_finished':True}).json()['schedules']}
    assert propose(client,admin,'get_schedule',{'schedule_id':schedule['id']}).json()['name'] == data['name']
    changed = agent_confirm(client,admin,'update_schedule',{'schedule_id':schedule['id'],'changes':{'name':'Updated schedule'}})
    assert changed['name'] == 'Updated schedule'
    for enabled in (False,True):
        assert agent_confirm(client,admin,'set_schedule_enabled',{'schedule_id':schedule['id'],'enabled':enabled})['enabled'] == enabled
    assert propose(client,admin,'get_schedule_runs',{'schedule_id':schedule['id']}).json()['runs'] == []
    client.app.state.schedule_service.execute_due(when+timedelta(minutes=1))
    runs = propose(client,admin,'get_schedule_runs',{'schedule_id':schedule['id']}).json()['runs']
    assert len(runs) == 1 and runs[0]['status'] == 'success'
    assert agent_confirm(client,admin,'delete_schedule',{'schedule_id':schedule['id']})['deleted']


def test_agent_management_checks_live_roles_and_stale_updates(client, admin):
    data = {'name':'Stale test','voice_keyword':'stale test','steps':[]}
    scene = agent_confirm(client,admin,'create_scene',data)
    pending = propose(client,admin,'update_scene',{'scene_id':scene['id'],'changes':{'name':'Agent new name'}}).json()
    client.put('/api/dashboard/scenes/'+scene['id'],headers=admin,json={**data,'name':'Changed elsewhere'})
    response = client.post(f"/api/dashboard/agent/actions/{pending['id']}/decision",headers=admin,json={'approved':True})
    assert response.status_code == 400 and 'thay đổi' in response.json()['detail']
    member = client.post('/api/dashboard/auth/login',json={'user_id':'vinh','pin':'1234'}).json()
    headers = {'Authorization':'Bearer '+member['access_token']}
    for tool,args in [('create_scene',data),('update_scene',{'scene_id':scene['id'],'changes':{'name':'No permission'}}),('delete_scene',{'scene_id':scene['id']}),('set_scene_enabled',{'scene_id':scene['id'],'enabled':False})]:
        assert propose(client,headers,tool,args).status_code == 403
    assert propose(client,headers,'list_scenes',{}).status_code == 200
    assert propose(client,headers,'list_schedules',{}).status_code == 200
    assert propose(client,admin,'update_scene',{'scene_id':scene['id'],'changes':{}}).status_code == 400
    assert propose(client,admin,'update_scene',{'scene_id':scene['id'],'changes':None}).status_code == 400
    assert propose(client,admin,'update_scene',{'scene_id':scene['id'],'changes':{'steps':None}}).status_code == 400
    agent_confirm(client,admin,'delete_scene',{'scene_id':scene['id']})


def test_agent_detailed_energy_matches_backend(client, admin):
    filters = {'period':'7days','room_id':'living','device_id':'light-living','anchor':'2026-10-01'}
    expected = client.get('/api/dashboard/energy',headers=admin,params=filters)
    actual = propose(client,admin,'get_energy_report',filters)
    assert actual.status_code == 200, actual.text
    assert actual.json() == expected.json()
    for args in ({'anchor':'not-a-date'},{'room_id':'unknown'},{'device_id':'unknown'}, {'room_id':'bed','device_id':'light-living'},{'period':'invalid'},{'unexpected':True}):
        assert propose(client,admin,'get_energy_report',args).status_code == 400
