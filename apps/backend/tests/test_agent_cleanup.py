from uuid import uuid4
from datetime import datetime, timedelta, timezone
import jwt
from test_software import client, admin
from test_agent_workflow import BASE, begin, commit
from homate.config import get_settings
from homate.infrastructure.tokens import _encode


def test_cleanup_survives_expired_access_and_same_request_retries_immediately(client, admin):
    identifier, first, payload = begin(client, admin)
    expired = _encode({'sub': 'minh-duc', 'home_id': first['session']['home_id'], 'typ': 'access'}, minutes=-1)
    assert client.post(BASE + f'/turns/{identifier}/abort', headers={'Authorization': 'Bearer ' + expired},
                       json={'lease_id': first['lease_id']}).status_code == 401
    cleanup = {'Authorization': 'Bearer ' + first['cleanup_token']}
    assert client.post(BASE + f'/turns/{identifier}/release', headers=cleanup,
                       json={'lease_id': first['lease_id']}).status_code == 200
    retried = client.post(BASE + '/turns/begin', headers=admin, json=payload)
    assert retried.status_code == 200
    assert retried.json()['lease_id'] != first['lease_id']
    # Replaying cleanup from the failed attempt must not unlock the new attempt.
    assert client.post(BASE + f'/turns/{identifier}/release', headers=cleanup,
                       json={'lease_id': first['lease_id']}).status_code == 200
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).status_code == 409
    client.app.state.test_leases[identifier] = retried.json()['lease_id']
    assert commit(client, admin, identifier, invalidate=False).status_code == 200


def test_cleanup_credential_has_no_access_or_execution_privileges(client, admin):
    identifier, turn, _ = begin(client, admin)
    cleanup = {'Authorization': 'Bearer ' + turn['cleanup_token']}
    assert client.get(BASE + '/identity', headers=cleanup).status_code == 401
    assert client.post(BASE + f'/turns/{identifier}/commit', headers=cleanup,
                       json={'lease_id': turn['lease_id'], 'response': {'reply': 'No'}}).status_code == 401
    # An ordinary access token is also not a cleanup capability.
    assert client.post(BASE + f'/turns/{identifier}/release', headers=admin,
                       json={'lease_id': turn['lease_id']}).status_code == 401
    assert client.post(BASE + f'/turns/{identifier}/release', headers=cleanup,
                       json={'lease_id': turn['lease_id']}).status_code == 200


def test_cleanup_rejects_foreign_request_lease_and_expired_credential(client, admin):
    identifier, turn, payload = begin(client, admin)
    cleanup = {'Authorization': 'Bearer ' + turn['cleanup_token']}
    for request_id, lease_id in [(str(uuid4()), turn['lease_id']), (identifier, str(uuid4()))]:
        assert client.post(BASE + f'/turns/{request_id}/release', headers=cleanup,
                           json={'lease_id': lease_id}).status_code == 401
    claims = jwt.decode(turn['cleanup_token'], get_settings().jwt_secret, algorithms=['HS256'])
    claims['exp'] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = jwt.encode(claims, get_settings().jwt_secret, algorithm='HS256')
    assert client.post(BASE + f'/turns/{identifier}/release', headers={'Authorization': 'Bearer ' + expired},
                       json={'lease_id': turn['lease_id']}).status_code == 401
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).status_code == 409
    client.post(BASE + f'/turns/{identifier}/release', headers=cleanup, json={'lease_id': turn['lease_id']})


def test_cleanup_does_not_change_completed_plan_or_return_credential_in_chat_response(client, admin):
    identifier, turn, payload = begin(client, admin)
    response = commit(client, admin, identifier, invalidate=False)
    assert response.status_code == 200
    assert 'cleanup_token' not in response.json()
    assert client.post(BASE + f'/turns/{identifier}/release', headers={'Authorization': 'Bearer ' + turn['cleanup_token']},
                       json={'lease_id': turn['lease_id']}).status_code == 200
    assert client.post(BASE + '/turns/begin', headers=admin, json=payload).json()['response'] == response.json()


def test_real_ai_backend_expired_tool_token_cleans_up_before_http_retry(client, admin):
    import asyncio
    import httpx
    from fastapi.testclient import TestClient
    from homate_ai.bootstrap import create_app
    from homate_ai.config import Settings
    from homate_ai.clients.backend import BackendClient
    from homate_ai.clients.workflow import WorkflowClient
    from homate_ai.agent.models import ModelReply, ToolCall
    expired = _encode({'sub': 'minh-duc', 'typ': 'access'}, minutes=-1)
    failures, released = [], []

    def handler(request):
        authorization = request.headers['authorization']
        if request.url.path.endswith('/agent/tools') and not failures:
            authorization = 'Bearer ' + expired
            failures.append(True)
        response = client.request(request.method, request.url.path, content=request.content,
                                  headers={'Authorization': authorization, 'Content-Type': 'application/json'})
        if request.url.path.endswith('/release'):
            released.append(response.status_code)
        return httpx.Response(response.status_code, json=response.json())

    class Model:
        calls = 0
        async def complete(self, messages, tools):
            self.calls += 1
            if self.calls < 3:
                return ModelReply(calls=[ToolCall(str(uuid4()), 'get_home_snapshot', {})])
            return ModelReply('Đã đọc dữ liệu sau khi làm mới phiên.')

    transport = httpx.AsyncClient(base_url='http://backend', transport=httpx.MockTransport(handler))
    try:
        app = create_app(Settings(_env_file=None), model=Model(), backend=BackendClient(transport), workflow=WorkflowClient(transport))
        with TestClient(app) as ai:
            payload = {'request_id': str(uuid4()), 'text': 'Kiểm tra thiết bị'}
            assert ai.post('/api/ai/chat', headers=admin, json=payload).status_code == 401
            assert released == [200]
            retried = ai.post('/api/ai/chat', headers=admin, json=payload)
            assert retried.status_code == 200
            assert retried.json()['reply'] == 'Đã đọc dữ liệu sau khi làm mới phiên.'
            assert 'cleanup_token' not in retried.json()
    finally:
        asyncio.run(transport.aclose())
