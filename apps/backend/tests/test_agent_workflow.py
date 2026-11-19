"""Real PostgreSQL tests: durable turns, immutable plans and failure boundaries."""
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from test_software import client, admin
from homate.infrastructure.postgres.connection import connect

BASE = '/api/dashboard/agent'


def begin(client, admin, text='Test', conversation=None, version=None, identifier=None):
    identifier = identifier or str(uuid4())
    payload = {'request_id': identifier, 'text': text, 'conversation_id': conversation, 'expected_version': version}
    response = client.post(BASE + '/turns/begin', headers=admin, json=payload)
    assert response.status_code == 200, response.text
    leases = getattr(client.app.state, 'test_leases', {})
    leases[identifier] = response.json().get('lease_id')
    client.app.state.test_leases = leases
    return identifier, response.json(), payload


def commit(client, admin, identifier, steps=None, state=None, invalidate=True):
    return client.post(BASE + f'/turns/{identifier}/commit', headers=admin, json={
        'state': state or {}, 'response': {'reply': 'Review plan', '_user_text': 'Test', 'sources': [], 'trace': []},
        'invalidate': invalidate, 'steps': steps or [], 'summary': 'Test plan',
        'lease_id': client.app.state.test_leases[identifier]})


def abort(client, admin, identifier):
    return client.post(BASE + f'/turns/{identifier}/abort', headers=admin,
        json={'lease_id': client.app.state.test_leases[identifier]})


def device_step(action='turn_on', depends=None):
    return {'tool': 'control_device', 'arguments': {'device_id': 'light-living', 'action': action, 'parameters': {}}, 'depends_on': depends or []}


def plan(client, admin, steps=None):
    identifier, turn, _ = begin(client, admin)
    response = commit(client, admin, identifier, steps or [device_step()])
    assert response.status_code == 200, response.text
    return response.json(), turn


def decide(client, admin, action, approved=True):
    return client.post(BASE + f'/plans/{action["id"]}/decision', headers=admin,
                       json={'approved': approved, 'version': action['plan_version']})


def test_plan_proposal_has_no_effect_and_confirmation_is_idempotent(client, admin):
    original = client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power']
    result, _ = plan(client, admin, [device_step('turn_off' if original else 'turn_on')])
    action = result['pending_actions'][0]
    assert action['kind'] == 'plan' and 'prepared' not in action['steps'][0]
    assert client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power'] == original
    first = decide(client, admin, action)
    assert first.status_code == 200, first.text
    assert first.json()['status'] == 'executed' and first.json()['steps'][0]['status'] == 'succeeded'
    assert client.get('/api/dashboard/devices/light-living', headers=admin).json()['state']['power'] != original
    repeated = decide(client, admin, action)
    assert repeated.json() == first.json()


def test_turn_retry_caches_response_and_rejects_request_id_reuse(client, admin):
    identifier, _, payload = begin(client, admin)
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).status_code == 409
    response = commit(client, admin, identifier, [device_step()])
    assert response.status_code == 200, response.text
    retry = client.post(BASE + '/turns/begin', headers=admin, json=payload)
    assert retry.json()['cached'] is True and retry.json()['response'] == response.json()
    payload['text'] = 'Changed'
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).status_code == 409


def test_correction_invalidates_old_confirmation_version(client, admin):
    result, turn = plan(client, admin)
    old = result['pending_actions'][0]
    identifier, _, _ = begin(client, admin, 'Correction', result['conversation_id'], result['conversation_version'])
    correction = commit(client, admin, identifier, [device_step('turn_off')])
    assert correction.status_code == 200, correction.text
    new = correction.json()['pending_actions'][0]
    assert new['plan_version'] > old['plan_version']
    assert old['id'] in correction.json()['invalidated_plan_ids']
    assert decide(client, admin, old).status_code == 409
    wrong = client.post(BASE + f'/plans/{new["id"]}/decision', headers=admin, json={'approved': True, 'version': old['plan_version']})
    assert wrong.status_code == 409


def test_read_turn_preserves_pending_plan_and_close_revokes_it(client, admin):
    result, _ = plan(client, admin)
    action = result['pending_actions'][0]
    identifier, _, _ = begin(client, admin, 'Question', result['conversation_id'], result['conversation_version'])
    read = commit(client, admin, identifier, invalidate=False)
    assert read.status_code == 200 and read.json()['pending_actions'][0]['id'] == action['id']
    assert client.delete(BASE + '/conversations/' + result['conversation_id'], headers=admin).status_code == 200
    assert decide(client, admin, action).status_code == 409


def test_rejection_expiry_and_cancel_do_not_execute(client, admin):
    result, _ = plan(client, admin)
    action = result['pending_actions'][0]
    assert decide(client, admin, action, False).json()['status'] == 'rejected'
    result, _ = plan(client, admin)
    action = result['pending_actions'][0]
    with connect(client.app.state.database_url) as conn:
        conn.execute("UPDATE agent_plans SET expires_at=now()-interval '1 second' WHERE id=%s", (action['id'],))
    expired = decide(client, admin, action).json()
    assert expired['status'] == 'expired' and expired['steps'][0]['status'] == 'skipped'
    result, _ = plan(client, admin)
    identifier, _, _ = begin(client, admin, 'Cancel', result['conversation_id'], result['conversation_version'])
    cancelled = commit(client, admin, identifier, state={'cancelled': True})
    assert cancelled.json()['invalidated_status'] == 'cancelled'
    assert decide(client, admin, result['pending_actions'][0]).status_code == 409


def test_dialogue_survives_reload_and_is_isolated_by_owner(client, admin):
    identifier, turn, _ = begin(client, admin)
    response = commit(client, admin, identifier, state={'draft': {'question': 'Which room?'}})
    saved = client.get(BASE + '/conversations/' + response.json()['conversation_id'], headers=admin)
    assert saved.json()['state']['draft']['question'] == 'Which room?'
    assert saved.json()['messages'][0]['content'] == 'Test'
    member_token = client.post('/api/dashboard/auth/login', json={'user_id': 'vinh', 'pin': '1234'}).json()['access_token']
    member = {'Authorization': 'Bearer ' + member_token}
    assert client.get(BASE + '/conversations/' + response.json()['conversation_id'], headers=member).status_code == 404
    planned, _ = plan(client, admin)
    action = planned['pending_actions'][0]
    assert client.get(BASE + '/plans/' + action['id'], headers=member).status_code == 404
    assert decide(client, member, action).status_code == 404


def test_invalid_late_step_rolls_back_entire_proposal(client, admin):
    identifier, turn, _ = begin(client, admin)
    steps = [device_step(), {'tool': 'control_device', 'arguments': {'device_id': 'missing', 'action': 'turn_on', 'parameters': {}}}]
    response = commit(client, admin, identifier, steps)
    assert response.status_code == 404
    with connect(client.app.state.database_url) as conn:
        assert conn.execute('SELECT count(*) AS n FROM agent_plans WHERE session_id=%s', (turn['session']['id'],)).fetchone()['n'] == 0
    abort(client, admin, identifier)


def test_concurrent_decisions_claim_plan_only_once(client, admin):
    result, _ = plan(client, admin)
    action = result['pending_actions'][0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: decide(client, admin, action), range(2)))
    assert all(response.status_code == 200 for response in responses)
    state = client.get(BASE + '/plans/' + action['id'], headers=admin).json()
    assert state['status'] == 'executed'
    assert state['steps'][0]['status'] == 'succeeded'


def test_busy_session_and_stale_dialogue_version_are_rejected(client, admin):
    result, _ = plan(client, admin)
    identifier, _, _ = begin(client, admin, 'First', result['conversation_id'], result['conversation_version'])
    payload = {'request_id': str(uuid4()), 'text': 'Second', 'conversation_id': result['conversation_id']}
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).status_code == 409
    assert decide(client, admin, result['pending_actions'][0]).status_code == 409
    abort(client, admin, identifier)
    payload['expected_version'] = result['conversation_version'] - 1
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).status_code == 409


def test_interrupted_execution_is_not_retried_and_is_visible(client, admin):
    result, _ = plan(client, admin)
    action = result['pending_actions'][0]
    user = client.get(BASE + '/identity', headers=admin).json()
    repo = client.app.state.agent_workflow_service.repository
    claimed = repo.claim(user, action['id'], action['plan_version'], True)
    assert claimed['claimed']
    repo.start_step(action['id'], 0)
    with connect(client.app.state.database_url) as conn:
        conn.execute("UPDATE agent_plans SET updated_at=now()-interval '10 minutes' WHERE id=%s", (action['id'],))
    receipt = decide(client, admin, action).json()
    assert receipt['status'] == 'executing' and receipt['recovery_required']
    assert receipt['steps'][0]['status'] == 'running'
    path = BASE + f"/plans/{action['id']}/recover"
    assert client.post(path, headers=admin, json={'version': action['plan_version'], 'acknowledged': False}).status_code == 422
    assert client.post(path, headers=admin, json={'version': action['plan_version'] + 1, 'acknowledged': True}).status_code == 409
    recovered = client.post(path, headers=admin, json={'version': action['plan_version'], 'acknowledged': True}).json()
    assert recovered['status'] == 'failed'
    assert recovered['steps'][0]['status'] == 'failed'
    assert not repo.finish_step(action['id'], 0, 'succeeded', {'message': 'Late worker'})
    assert repo.finish_plan(action['id'], 'executed', {'message': 'Late worker'})['status'] == 'failed'
    assert decide(client, admin, action).json()['status'] == 'failed'
    saved = client.get(BASE + '/conversations/' + result['conversation_id'], headers=admin).json()
    assert saved['status'] == 'idle'


def test_recovery_cannot_close_an_active_execution(client, admin):
    result, _ = plan(client, admin)
    action = result['pending_actions'][0]
    user = client.get(BASE + '/identity', headers=admin).json()
    client.app.state.agent_workflow_service.repository.claim(user, action['id'], action['plan_version'], True)
    response = client.post(BASE + f"/plans/{action['id']}/recover", headers=admin,
        json={'version': action['plan_version'], 'acknowledged': True})
    assert response.status_code == 409


def test_partial_failure_records_success_and_skips_remaining_steps(client, admin):
    result, _ = plan(client, admin, [device_step(), device_step('turn_off', [0]), device_step('turn_on', [1])])
    action = result['pending_actions'][0]
    user = client.get(BASE + '/identity', headers=admin).json()
    calls = []
    def run(tool, args):
        calls.append(tool)
        if len(calls) == 2: raise RuntimeError('Injected failure')
        return {'device_ids': ['light-living']}
    receipt = client.app.state.agent_workflow_service.decide(user, action['id'], action['plan_version'], True, lambda _: None, run)
    assert receipt['status'] == 'failed'
    assert [step['status'] for step in receipt['steps']] == ['succeeded', 'failed', 'skipped']
    again = decide(client, admin, action).json()
    assert again['status'] == 'failed' and len(calls) == 2


def test_read_after_write_runs_in_plan_order(client, admin):
    result, _ = plan(client, admin, [device_step('turn_on'), {'tool': 'get_home_snapshot', 'arguments': {}, 'depends_on': [0]}])
    response = decide(client, admin, result['pending_actions'][0])
    assert response.status_code == 200, response.text
    receipt = response.json()
    device = next(d for d in receipt['steps'][1]['result']['devices'] if d['id'] == 'light-living')
    assert device['state']['power'] is True


def test_conversation_memory_survives_execution_and_rejection_without_a_live_task(client, admin):
    for approved, expected in ((True, 'executed'), (False, 'rejected')):
        identifier, _, _ = begin(client, admin)
        result = commit(client, admin, identifier, [device_step()], state={
            'draft': {'pending': True}, 'conversation': {'topic': 'Đèn phòng khách',
                'observations': [{'old': 'stale'}], 'entities': [{'value': 'light-living'}]}}).json()
        receipt = decide(client, admin, result['pending_actions'][0], approved).json()
        assert receipt['status'] == expected
        saved = client.get(BASE + '/conversations/' + result['conversation_id'], headers=admin).json()['state']
        assert 'draft' not in saved
        assert saved['conversation']['topic'] == 'Đèn phòng khách'
        assert saved['conversation']['observations'] == []
        assert saved['conversation']['execution']['status'] == expected
        assert saved['conversation']['execution']['steps'][0]['status'] == ('succeeded' if approved else 'skipped')


def test_expired_dialogue_discards_old_draft(client, admin):
    identifier, turn, _ = begin(client, admin)
    result = commit(client, admin, identifier, state={'draft': {'old': True}}).json()
    with connect(client.app.state.database_url) as conn:
        conn.execute("UPDATE agent_sessions SET expires_at=now()-interval '1 second' WHERE id=%s", (result['conversation_id'],))
    identifier, loaded, _ = begin(client, admin, 'New', result['conversation_id'], result['conversation_version'])
    assert loaded['session']['state'] == {} and loaded['session']['messages'] == []
    abort(client, admin, identifier)


def test_old_lease_cannot_abort_or_commit_a_reclaimed_turn(client, admin):
    identifier, turn, payload = begin(client, admin)
    old_lease = turn['lease_id']
    with connect(client.app.state.database_url) as conn:
        conn.execute("UPDATE agent_sessions SET busy_until=now()-interval '1 second' WHERE id=%s", (turn['session']['id'],))
    retry = client.post(BASE + '/turns/begin', headers=admin, json=payload).json()
    assert retry['lease_id'] != old_lease
    client.post(BASE + f'/turns/{identifier}/abort', headers=admin, json={'lease_id': old_lease})
    stale = client.post(BASE + f'/turns/{identifier}/commit', headers=admin, json={
        'lease_id': old_lease, 'response': {'reply': 'stale'}, 'state': {}})
    assert stale.status_code == 409
    client.app.state.test_leases[identifier] = retry['lease_id']
    assert commit(client, admin, identifier).status_code == 200


def test_relative_plan_shows_value_and_refuses_changed_source_state(client, admin):
    device = client.get('/api/dashboard/devices/ac-bed', headers=admin).json()
    current = device['state']['temperature']
    target = current - 1 if current > 16 else current + 1
    step = {'tool': 'control_device', 'arguments': {'device_id': 'ac-bed', 'action': 'set_temperature',
        'parameters': {'temperature': target}}, 'expected_state': {'ac-bed': {'temperature': current}}}
    result, _ = plan(client, admin, [step])
    action = result['pending_actions'][0]
    assert any(str(target) in line for line in action['arguments']['review'])
    client.post('/api/dashboard/devices/ac-bed/actions', headers=admin, json={'key': 'power', 'value': True})
    client.post('/api/dashboard/devices/ac-bed/actions', headers=admin, json={'key': 'temperature', 'value': target})
    receipt = decide(client, admin, action).json()
    assert receipt['status'] == 'failed'
    assert receipt['steps'][0]['status'] == 'skipped'


def test_ai_http_workflow_persists_clarification_then_confirms_one_version(client, admin):
    import asyncio
    import httpx
    from fastapi.testclient import TestClient
    from homate_ai.bootstrap import create_app as ai_app
    from homate_ai.config import Settings
    from homate_ai.clients.backend import BackendClient
    from homate_ai.clients.workflow import WorkflowClient
    from homate_ai.agent.models import ModelReply, ToolCall

    class Model:
        calls = 0
        async def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return ModelReply(calls=[ToolCall('snapshot', 'get_home_snapshot', {})])
            if self.calls == 2:
                return ModelReply('Bạn muốn chọn đèn phòng nào?')
            if self.calls == 3:
                assert any(m.get('content') == 'Bạn muốn chọn đèn phòng nào?' for m in messages)
                return ModelReply(calls=[ToolCall('proposal', 'propose_plan', {'steps': [{
                    'tool': 'control_device', 'arguments': {'device_id': 'light-living', 'action': 'turn_off', 'parameters': {}}}]})])
            return ModelReply('Bạn xác nhận nhé.')

    def handle(request):
        response = client.request(request.method, request.url.path, content=request.content,
            headers={'Authorization': request.headers['authorization'], 'Content-Type': 'application/json'})
        return httpx.Response(response.status_code, json=response.json())

    transport = httpx.AsyncClient(base_url='http://backend', transport=httpx.MockTransport(handle))
    model = Model()
    try:
        with TestClient(ai_app(Settings(_env_file=None), model=model, backend=BackendClient(transport), workflow=WorkflowClient(transport))) as ai:
            first_response = ai.post('/api/ai/chat', headers=admin, json={'request_id': str(uuid4()), 'text': 'Tắt đèn'})
            assert first_response.status_code == 200, first_response.text
            first = first_response.json()
            assert not first['pending_actions'] and 'phòng nào' in first['reply']
            payload = {'request_id': str(uuid4()), 'text': 'Phòng khách', 'conversation_id': first['conversation_id'],
                       'conversation_version': first['conversation_version']}
            response = ai.post('/api/ai/chat', headers=admin, json=payload)
            assert response.status_code == 200, response.text
            second = response.json()
            assert second['dialogue_state'] == 'pending' and model.calls == 4
            assert ai.post('/api/ai/chat', headers=admin, json=payload).json() == second
            action = second['pending_actions'][0]
            receipt = decide(client, admin, action)
            assert receipt.json()['status'] == 'executed'
            saved = client.get(BASE + '/conversations/' + second['conversation_id'], headers=admin).json()
            assert saved['plan']['status'] == 'executed' and 'draft' not in saved['state']
            assert saved['state']['conversation']['execution']['status'] == 'executed'
    finally:
        asyncio.run(transport.aclose())
