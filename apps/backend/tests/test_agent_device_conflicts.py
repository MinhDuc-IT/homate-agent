from uuid import uuid4
from datetime import datetime, timedelta, timezone
from homate.infrastructure.postgres.connection import connect
from test_software import client, admin
from test_agent_workflow import BASE, begin, commit, decide


def step(identifier, action='turn_on'):
    return {'tool': 'control_device', 'arguments': {'device_id': identifier, 'action': action, 'parameters': {}}}


def reset(client):
    devices = client.app.state.device_store
    devices.apply_action('ac-living', 'power', False)
    devices.apply_action('heater-living', 'power', False)


def test_snapshot_includes_scoped_rules_and_dry_run_reports_current_conflict(client, admin):
    reset(client)
    client.app.state.device_store.apply_action('ac-living', 'power', True)
    def tool(name, args):
        return client.post(BASE + '/tools', headers=admin, json={'request_id': str(uuid4()), 'tool': name, 'arguments': args})
    snapshot = tool('get_home_snapshot', {}).json()
    assert snapshot['device_conflicts']['ac-living'][0]['device_id'] == 'heater-living'
    check = tool('validate_plan', {'steps': [step('heater-living')]}).json()
    assert check['valid'] is False
    assert check['issues'][0]['policy'] == 'ask'
    assert client.app.state.device_store.get('heater-living').state['power'] is False


def test_invalid_batch_never_becomes_pending_or_changes_devices(client, admin):
    reset(client)
    identifier, _, _ = begin(client, admin)
    result = commit(client, admin, identifier, [step('ac-living'), step('heater-living')])
    assert result.status_code == 400
    assert client.app.state.device_store.get('ac-living').state['power'] is False
    assert client.app.state.device_store.get('heater-living').state['power'] is False


def test_old_confirmation_rechecks_latest_peer_state(client, admin):
    reset(client)
    identifier, _, _ = begin(client, admin)
    proposal = commit(client, admin, identifier, [step('heater-living')]).json()
    client.app.state.device_store.apply_action('ac-living', 'power', True)
    receipt = decide(client, admin, proposal['pending_actions'][0]).json()
    assert receipt['status'] == 'failed'
    assert client.app.state.device_store.get('heater-living').state['power'] is False


def test_explicit_switch_order_and_manual_bypass(client, admin):
    reset(client)
    client.app.state.device_store.apply_action('ac-living', 'power', True)
    manual = client.post('/api/dashboard/devices/heater-living/actions', headers=admin, json={'key': 'power', 'value': True})
    assert manual.status_code == 400
    identifier, _, _ = begin(client, admin)
    proposal = commit(client, admin, identifier, [step('ac-living', 'turn_off'), step('heater-living')]).json()
    assert decide(client, admin, proposal['pending_actions'][0]).json()['status'] == 'executed'
    assert client.app.state.device_store.get('ac-living').state['power'] is False
    reset(client)


def test_scheduled_scene_checks_whole_sequence_before_first_effect(client, admin):
    reset(client)
    devices = client.app.state.device_store
    devices.apply_action('ac-living', 'power', True)
    devices.apply_action('light-living', 'power', False)
    scene = client.post('/api/dashboard/scenes', headers=admin, json={'name': 'Conflict runtime',
        'voice_keyword': 'conflict runtime', 'steps': [step('light-living')['arguments'], step('heater-living')['arguments']]}).json()
    when = datetime.now(timezone.utc) + timedelta(hours=1)
    schedule = client.post('/api/dashboard/schedules', headers=admin, json={'name': 'Conflict due',
        'schedule_type': 'once', 'target_type': 'scene', 'scene_id': scene['id'], 'run_at': when.isoformat()}).json()
    client.app.state.schedule_service.execute_due(when + timedelta(minutes=1))
    runs = client.app.state.schedule_service.runs('home-michelin-bois', schedule['id'])
    assert runs[0]['status'] == 'failed'
    assert devices.get('light-living').state['power'] is False
    assert devices.get('heater-living').state['power'] is False
    reset(client)


def test_scene_configuration_allows_ordered_switch_but_rejects_transient_conflict(client, admin):
    reset(client)
    base = {'name': 'Ordered climate', 'voice_keyword': 'ordered climate'}
    valid = [step('ac-living'), step('ac-living', 'turn_off'), step('heater-living')]
    response = client.post('/api/dashboard/scenes', headers=admin,
        json={**base, 'steps': [s['arguments'] for s in valid]})
    assert response.status_code == 201, response.text
    invalid = [step('ac-living'), step('heater-living'), step('ac-living', 'turn_off')]
    response = client.post('/api/dashboard/scenes', headers=admin,
        json={**base, 'name': 'Invalid climate', 'voice_keyword': 'invalid climate', 'steps': [s['arguments'] for s in invalid]})
    assert response.status_code == 400


def test_auto_off_is_visible_and_sensitive_shutdown_requires_confirmation(client, admin):
    reset(client)
    devices = client.app.state.device_store
    devices.apply_action('heater-living', 'power', True)
    with connect(client.app.state.database_url) as connection:
        connection.execute("UPDATE device_conflicts SET on_conflict='auto_off_other'")
        connection.commit()
    try:
        identifier, _, _ = begin(client, admin)
        # Policy mode rather than the always-confirm helper.
        response = client.post(BASE + f'/turns/{identifier}/commit', headers=admin, json={
            'lease_id': client.app.state.test_leases[identifier], 'response': {'reply': 'Test'}, 'invalidate': True,
            'steps': [step('ac-living')]})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['confirmation_policy']['mode'] == 'require_confirmation'
        assert devices.get('heater-living').state['power'] is True
        action = result['pending_actions'][0]
        assert 'Máy sưởi' in action['steps'][0]['summary']
        assert decide(client, admin, action).json()['status'] == 'executed'
        assert devices.get('heater-living').state['power'] is False
        assert devices.get('ac-living').state['power'] is True
    finally:
        with connect(client.app.state.database_url) as connection:
            connection.execute("UPDATE device_conflicts SET on_conflict='ask'")
            connection.commit()
        reset(client)
