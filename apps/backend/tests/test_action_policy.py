from test_software import client, admin
from test_agent_workflow import BASE, begin, device_step


def test_scene_and_device_policy_uses_actual_device_kind_and_command_effects():
    from types import SimpleNamespace
    from homate.application.action_policy import confirmation_policy
    devices = {'light': SimpleNamespace(id='light', kind='bulb'), 'door': SimpleNamespace(id='door', kind='lock'),
               'heater': SimpleNamespace(id='heater', kind='flame'), 'plug': SimpleNamespace(id='plug', kind='plug')}
    store = SimpleNamespace(get=devices.__getitem__)
    def scene(identifier, action):
        return [{'tool': 'execute_scene', 'prepared': {'commands': [{'device_id': identifier, 'action': action, 'parameters': {}}]}}]
    assert confirmation_policy(scene('light', 'turn_on'), store)['mode'] == 'auto_execute'
    for identifier, action in [('door', 'unlock'), ('heater', 'turn_on'), ('plug', 'turn_on'), ('light', 'unknown')]:
        assert confirmation_policy(scene(identifier, action), store)['mode'] == 'require_confirmation'
    assert confirmation_policy([{'tool': 'create_schedule', 'prepared': {}}], store)['mode'] == 'require_confirmation'


def propose(client, admin, steps, identifier=None, turn=None):
    if identifier is None:
        identifier, turn, _ = begin(client, admin)
    body = {'state': {'conversation': {}, 'draft': {'steps': steps}},
            'response': {'reply': 'Đề xuất', '_user_text': 'Test'}, 'steps': steps,
            'invalidate': True, 'summary': 'Kiểm thử chính sách', 'lease_id': turn['lease_id']}
    return client.post(BASE + f'/turns/{identifier}/commit', headers=admin, json=body), identifier, turn, body


def test_routine_action_executes_once_and_retry_returns_receipt(client, admin, monkeypatch):
    from homate.presentation import agent_workflow as routes
    actual = routes.execute
    executions = []
    def counted(*args):
        executions.append(args[-2])
        return actual(*args)
    monkeypatch.setattr(routes, 'execute', counted)
    original = client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power']
    r, identifier, turn, body = propose(client, admin, [device_step('turn_off' if original else 'turn_on')])
    assert r.status_code == 200
    data = r.json()
    assert not data['pending_actions'] and data['completed_actions'][0]['status'] == 'executed'
    assert data['confirmation_policy']['mode'] == 'auto_execute'
    assert client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power'] != original
    assert executions == ['control_device']
    repeated = client.post(BASE + f'/turns/{identifier}/commit', headers=admin, json=body)
    assert repeated.json() == data and executions == ['control_device']
    cached = client.post(BASE + '/turns/begin', headers=admin, json={'request_id': identifier, 'text': 'Test',
        'conversation_id': None, 'expected_version': None})
    assert cached.json()['response'] == data and executions == ['control_device']
    saved = client.get(BASE + '/conversations/'+data['conversation_id'],headers=admin).json()
    assert saved['status'] == 'idle' and saved['state']['conversation']['execution']['status'] == 'executed'


def test_mixed_sensitive_chain_waits_without_running_routine_step(client, admin):
    original = client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power']
    sensitive = {'tool': 'control_device', 'arguments': {'device_id': 'door', 'action': 'unlock', 'parameters': {}}}
    r, *_ = propose(client, admin, [device_step('turn_off' if original else 'turn_on'), sensitive])
    assert r.status_code == 200
    assert r.json()['confirmation_policy']['mode'] == 'require_confirmation'
    assert r.json()['pending_actions'][0]['status'] == 'pending'
    assert client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power'] == original


def test_large_routine_batch_requires_confirmation(client, admin):
    r, *_ = propose(client, admin, [device_step() for _ in range(6)])
    assert r.status_code == 200
    assert r.json()['confirmation_policy']['reason'] == 'large_scope'
    assert r.json()['pending_actions']


def test_auto_failure_returns_per_step_receipts_without_success_claim(client, admin, monkeypatch):
    from homate.presentation import agent_workflow as routes
    actual = routes.execute
    calls = []
    def failing(*args):
        calls.append(True)
        if len(calls) == 2:
            raise RuntimeError('Device offline')
        return actual(*args)
    monkeypatch.setattr(routes, 'execute', failing)
    r, *_ = propose(client, admin, [device_step('turn_on'), device_step('turn_off'), device_step('turn_on')])
    assert r.status_code == 200
    receipt = r.json()['completed_actions'][0]
    assert receipt['status'] == 'failed'
    assert [s['status'] for s in receipt['steps']] == ['succeeded', 'failed', 'skipped']
    assert '1/3' in r.json()['reply']


def test_claimed_auto_plan_is_not_reexecuted_after_interrupted_response(client, admin, monkeypatch):
    service = client.app.state.agent_workflow_service
    def interrupted(*args):
        raise RuntimeError('Process interrupted after durable claim')
    monkeypatch.setattr(service, 'execute_claimed', interrupted)
    identifier, turn, payload = begin(client, admin)
    # The ASGI test client raises, simulating a worker dying after commit.
    import pytest
    with pytest.raises(RuntimeError):
        propose(client, admin, [device_step()], identifier, turn)
    cached = client.post(BASE + '/turns/begin', headers=admin, json=payload)
    assert cached.status_code == 200
    response = cached.json()['response']
    assert response['completed_actions'][0]['status'] == 'executing'
    assert response['completed_actions'][0]['steps'][0]['status'] == 'pending'
    assert not response['pending_actions']


def test_client_cannot_override_sensitive_policy_in_response(client, admin):
    identifier, turn, _ = begin(client, admin)
    r = client.post(BASE + f'/turns/{identifier}/commit', headers=admin, json={
        'lease_id': turn['lease_id'], 'invalidate': True, 'state': {},
        'response': {'reply': 'Đã mở cửa', 'confirmation_policy': {'mode': 'auto_execute'},
                     'auto_plan_id': 'forged', 'completed_actions': [{'status': 'executed'}]},
        'steps': [{'tool': 'control_device', 'arguments': {'device_id': 'door', 'action': 'unlock', 'parameters': {}}}],
    })
    assert r.status_code == 200
    assert r.json()['confirmation_policy']['mode'] == 'require_confirmation'
    assert 'auto_plan_id' not in r.json() and 'completed_actions' not in r.json()
    assert r.json()['pending_actions'][0]['status'] == 'pending'
