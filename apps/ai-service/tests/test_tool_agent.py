import asyncio
from uuid import uuid4
import pytest
from homate_ai.agent.tool_agent import ToolConversationAgent, AGENT_TOOLS
from homate_ai.agent.models import ModelReply, ToolCall, AgentUnavailable
from test_runtime import Backend, Model, Workflow, chat


def call(name, **arguments):
    return ModelReply('', [ToolCall(str(uuid4()), name, arguments)])


def plan(temperature=24, device='ac-bed'):
    return call('propose_plan', steps=[{'tool': 'control_device',
        'arguments': {'device_id': device, 'action': 'set_temperature', 'parameters': {'temperature': temperature}}}])


def test_tool_loop_observes_results_then_answers_without_interpretation_labels():
    model = Model([call('get_home_snapshot'), ModelReply('Đang đặt 26°C.')])
    workflow = Workflow()
    result = chat(ToolConversationAgent(model, Backend(), workflow), 'Điều hòa đang bao nhiêu độ?')
    assert result['trace'] == [{'tool': 'get_home_snapshot', 'status': 'success'}]
    assert any(m['role'] == 'tool' and 'temperature' in m['content'] for m in model.messages[1])
    assert 'submit_interpretation' not in str(model.messages)
    assert not result['pending_actions']
    assert not workflow.commits[-1]['steps']


def test_fragment_and_read_followup_use_saved_tool_transcript_after_reload():
    workflow = Workflow()
    first_agent = ToolConversationAgent(Model([call('get_home_snapshot'), ModelReply('Bạn muốn xem phòng nào?')]), Backend(), workflow)
    first = chat(first_agent, 'Điều hòa bao nhiêu độ?')
    model = Model([call('get_home_snapshot'), ModelReply('Phòng ngủ đang đặt 26°C.')])
    second = chat(ToolConversationAgent(model, Backend(), workflow), 'phòng ngủ', first)
    messages = model.messages[0]
    assert any(m['role'] == 'tool' for m in messages)
    assert any(m.get('content') == 'Bạn muốn xem phòng nào?' for m in messages)
    assert messages[-1]['content'] == 'phòng ngủ'
    assert second['reply'] == 'Phòng ngủ đang đặt 26°C.'


def test_write_plan_is_validated_and_only_prepared_not_executed():
    backend, workflow = Backend(), Workflow()
    agent = ToolConversationAgent(Model([call('get_home_snapshot'), plan(), ModelReply('Đã giảm rồi.')]), backend, workflow)
    result = chat(agent, 'Giảm nó 2 độ')
    assert result['pending_actions']
    assert 'Chưa có thay đổi' in result['reply']
    assert all(name != 'control_device' for name, _ in backend.calls)
    assert workflow.commits[-1]['steps'][0]['expected_state']['ac-bed']['temperature'] == 26


def test_invalid_tool_arguments_return_to_model_for_correction():
    model = Model([call('get_home_snapshot', home_id='foreign'), call('get_home_snapshot'), ModelReply('26°C.')])
    backend = Backend()
    result = chat(ToolConversationAgent(model, backend, Workflow()), 'Đọc thiết bị')
    assert result['trace'][0]['status'] == 'error'
    assert 'invalid_arguments' in model.messages[1][-1]['content']
    assert backend.calls == [('get_home_snapshot', {})]


@pytest.mark.parametrize('device,temperature', [('foreign-device', 24), ('ac-bed', 99)])
def test_invalid_plan_never_reaches_preparation(device, temperature):
    model = Model([plan(temperature, device), ModelReply('Bạn kiểm tra lại thiết bị nhé.')])
    workflow = Workflow()
    result = chat(ToolConversationAgent(model, Backend(), workflow), 'Điều chỉnh')
    assert not result['pending_actions']
    assert not workflow.commits[-1]['steps']
    assert 'needs_correction' in model.messages[1][-1]['content']


def test_plan_batch_is_atomic_when_later_step_is_invalid():
    good, bad = plan().calls[0].arguments['steps'][0], plan(99).calls[0].arguments['steps'][0]
    workflow = Workflow()
    result = chat(ToolConversationAgent(Model([call('propose_plan', steps=[good, bad]), ModelReply('Giá trị chưa hợp lệ.')]), Backend(), workflow), 'Hai thao tác')
    assert not result['pending_actions'] and not workflow.commits[-1]['steps']


def test_side_question_keeps_pending_plan_then_cancel_invalidates_it():
    workflow = Workflow()
    model = Model([plan(), ModelReply('Chờ xác nhận'), call('get_home_snapshot'), ModelReply('Đang đặt 26°C.'),
                   call('cancel_pending_request'), ModelReply('Đã hủy')])
    agent = ToolConversationAgent(model, Backend(), workflow)
    first = chat(agent, 'Đặt 24 độ')
    second = chat(agent, 'Khoan, hiện đang bao nhiêu?', first)
    assert second['pending_actions'][0]['id'] == first['pending_actions'][0]['id']
    third = chat(agent, 'Thôi hủy', second)
    assert not third['pending_actions']
    assert workflow.commits[-1]['invalidate']


def test_model_cannot_bypass_plan_by_calling_backend_write_tool():
    workflow = Workflow()
    result = chat(ToolConversationAgent(Model([call('control_device', device_id='ac-bed', action='turn_on', parameters={}),
                                            ModelReply('Cần đề xuất kế hoạch.')]), Backend(), workflow), 'Bật điều hòa')
    assert result['trace'][0]['status'] == 'error' and not result['pending_actions']
    assert 'control_device' not in {t['function']['name'] for t in AGENT_TOOLS}


def test_member_cannot_stage_admin_plan():
    workflow = Workflow()
    model = Model([call('propose_plan', steps=[{'tool': 'delete_scene', 'arguments': {'scene_id': 'night'}}]), ModelReply('Bạn chưa có quyền.')])
    result = chat(ToolConversationAgent(model, Backend(role='member'), workflow), 'Xóa kịch bản')
    assert not result['pending_actions']
    assert 'permission_denied' in model.messages[1][-1]['content']


def test_repeated_tool_requests_have_bounded_loop_and_release_lease():
    workflow = Workflow()
    agent = ToolConversationAgent(Model([call('get_home_snapshot') for _ in range(10)]), Backend(), workflow)
    with pytest.raises(AgentUnavailable) as error:
        chat(agent, 'Xem thiết bị')
    assert error.value.code == 'agent_step_limit'
    assert workflow.aborts and not workflow.commits


def test_http_chat_uses_native_tool_graph():
    from fastapi.testclient import TestClient
    from homate_ai.bootstrap import create_app
    from homate_ai.config import Settings
    workflow = Workflow()
    app = create_app(Settings(_env_file=None), model=Model([call('get_home_snapshot'), ModelReply('26°C.')]),
                     backend=Backend(), workflow=workflow)
    with TestClient(app) as client:
        r = client.post('/api/ai/chat', headers={'Authorization': 'Bearer valid'},
                        json={'request_id': str(uuid4()), 'text': 'Xem nhiệt độ'})
        assert r.status_code == 200
        assert r.json()['trace'] == [{'tool': 'get_home_snapshot', 'status': 'success'}]
        assert 'analysis' not in r.json()


def test_invalid_revision_cannot_commit_previous_staged_plan():
    workflow = Workflow()
    model = Model([plan(), call('propose_plan', steps=[]), ModelReply('Cần làm rõ yêu cầu.')])
    result = chat(ToolConversationAgent(model, Backend(), workflow), 'Điều chỉnh')
    assert not result['pending_actions'] and not workflow.commits[-1]['steps']


def test_replayed_request_does_not_call_model_or_duplicate_plan():
    workflow = Workflow()
    agent = ToolConversationAgent(Model([plan(), ModelReply('Chờ xác nhận')]), Backend(), workflow)
    identifier = str(uuid4())
    first = chat(agent, 'Đặt 24 độ', identifier=identifier)
    second = chat(agent, 'Đặt 24 độ', identifier=identifier)
    assert second == first
    assert len(workflow.commits) == 1


def test_rag_tool_results_and_sources_reach_final_reply():
    class Retriever:
        async def retrieve(self, token, query, device_id=None):
            return [{'chunk_id': 'chunk', 'content': 'Hướng dẫn sử dụng', 'title': 'Tài liệu'}]
    model = Model([call('search_knowledge', query='Cách dùng'), ModelReply('Theo hướng dẫn [1].')])
    result = chat(ToolConversationAgent(model, Backend(), Workflow(), retriever=Retriever()), 'Hướng dẫn dùng')
    assert result['sources'][0]['citation'] == 1
    assert 'Hướng dẫn sử dụng' in model.messages[1][-1]['content']
