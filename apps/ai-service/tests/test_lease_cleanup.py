import asyncio
from uuid import uuid4
import httpx
import pytest
from homate_ai.agent.models import BackendError, ModelReply
from homate_ai.agent.tool_agent import ToolConversationAgent
from homate_ai.clients.workflow import WorkflowClient
from test_runtime import Backend, Model, Workflow, chat
from test_tool_agent import call


class CleanupWorkflow(Workflow):
    def __init__(self):
        super().__init__()
        self.released = []

    async def begin(self, *args, **kwargs):
        result = await super().begin(*args, **kwargs)
        return {**result, 'cleanup_token': 'cleanup-only'}

    async def release(self, credential, request_id, lease_id):
        assert credential == 'cleanup-only'
        self.released.append((request_id, lease_id))

    async def abort(self, *args):
        raise AssertionError('Must not use the expired access token')


def test_midturn_401_releases_with_cleanup_credential_before_retry():
    class ExpiringBackend(Backend):
        failed = False
        async def call(self, *args):
            if not self.failed:
                self.failed = True
                raise BackendError(401, 'Access expired')
            return await super().call(*args)
    workflow = CleanupWorkflow()
    model = Model([call('get_home_snapshot'), call('get_home_snapshot'), ModelReply('Đã đọc dữ liệu.')])
    agent = ToolConversationAgent(model, ExpiringBackend(), workflow)
    identifier = str(uuid4())
    with pytest.raises(BackendError) as error:
        chat(agent, 'Đọc thiết bị', identifier=identifier)
    assert error.value.status == 401
    assert len(workflow.released) == 1 and workflow.released[0][0] == identifier
    assert chat(agent, 'Đọc thiết bị', identifier=identifier)['reply'] == 'Đã đọc dữ liệu.'
    assert len(workflow.released) == 1


def test_cancellation_releases_lease_and_propagates_cancel():
    async def run():
        started = asyncio.Event()
        class WaitingModel:
            async def complete(self, *args):
                started.set()
                await asyncio.Event().wait()
        workflow = CleanupWorkflow()
        agent = ToolConversationAgent(WaitingModel(), Backend(), workflow)
        task = asyncio.create_task(agent.chat('valid', str(uuid4()), 'Test', []))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(workflow.released) == 1
    asyncio.run(run())


def test_cleanup_failure_logs_no_credentials_and_preserves_original_error(caplog):
    class FailingWorkflow(CleanupWorkflow):
        async def release(self, *args):
            raise RuntimeError('PRIVATE_CREDENTIAL')
    class FailingModel:
        async def complete(self, *args):
            raise BackendError(401, 'Access expired')
    with pytest.raises(BackendError) as error:
        chat(ToolConversationAgent(FailingModel(), Backend(), FailingWorkflow()), 'Test')
    assert error.value.status == 401
    assert 'agent_lease_cleanup_failed' in caplog.text
    assert 'PRIVATE_CREDENTIAL' not in caplog.text and 'cleanup-only' not in caplog.text


def test_workflow_release_uses_scoped_token_not_user_token():
    async def run():
        def handler(request):
            assert request.headers['Authorization'] == 'Bearer cleanup-only'
            assert request.url.path.endswith('/release')
            return httpx.Response(200, json={'status': 'released'})
        async with httpx.AsyncClient(base_url='http://backend', transport=httpx.MockTransport(handler)) as c:
            assert await WorkflowClient(c).release('cleanup-only', str(uuid4()), str(uuid4())) == {'status': 'released'}
    asyncio.run(run())
