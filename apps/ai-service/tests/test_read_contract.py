import asyncio
import pytest
from homate_ai.agent.interpretation import Interpretation
from homate_ai.agent.interpreter import check_contract
from homate_ai.agent.models import AgentUnavailable, BackendError, ModelReply
from homate_ai.agent.runtime import ConversationAgent
from test_analysis import output
from test_runtime import Backend, Model, Workflow, chat


def query(intents=None, **extra):
    return {'kind': 'query', 'goal': 'Liệt kê thiết bị', 'intents': intents or [],
            'answer_sources': ['backend'], **extra}


def read():
    return {'goal': 'Đọc danh sách thiết bị', 'capability': 'get_home_snapshot', 'arguments': {}}


def test_empty_query_is_repaired_before_answer_and_reads_real_data():
    model = Model([output(query()), output(query([read()])), ModelReply('Có bốn thiết bị.')])
    backend, workflow = Backend(), Workflow()
    result = chat(ConversationAgent(model, backend, workflow), 'Nhà có những thiết bị nào?')
    assert result['trace'] == [{'tool': 'get_home_snapshot', 'status': 'success'}]
    assert 'Incomplete plan' in model.messages[1][-1]['content']
    observations = workflow.commits[-1]['state']['conversation']['observations']
    assert len(observations[0]['result']['devices']) == 4


def test_repeated_empty_plan_never_generates_answer_or_commits():
    model = Model([output(query()), output(query())])
    workflow, backend = Workflow(), Backend()
    with pytest.raises(AgentUnavailable) as error:
        chat(ConversationAgent(model, backend, workflow), 'Thiết bị trong nhà?')
    assert error.value.code == 'interpreter_schema_invalid'
    assert not backend.calls and not workflow.commits
    assert workflow.aborts


@pytest.mark.parametrize('sources', [['knowledge'], ['backend', 'knowledge']])
def test_missing_required_source_is_rejected(sources):
    with pytest.raises(ValueError, match='Incomplete read plan'):
        check_contract(Interpretation.model_validate(query([read()], answer_sources=sources)))


def test_topic_change_cannot_clear_pending_work():
    with pytest.raises(ValueError, match='explicit cancellation'):
        check_contract(Interpretation.model_validate(query([read()], dialogue={
            'relation': 'topic_change', 'task_action': 'clear'})))


def test_failed_backend_read_does_not_ask_model_to_invent_answer():
    class FailingBackend(Backend):
        async def call(self, *args):
            raise BackendError(503, 'unavailable')
    model = Model([])
    agent = ConversationAgent(model, FailingBackend(), Workflow())
    result = asyncio.run(agent.answer({'request_id': '00000000-0000-0000-0000-000000000001',
        'token': 'valid', 'interpretation': Interpretation.model_validate(query([read()]))},
        [type('Review', (), {'capability': 'get_home_snapshot', 'arguments': {}})()]))
    assert result[2] == [{'tool': 'get_home_snapshot', 'status': 'error'}]
    assert 'chưa tra cứu được' in result[0]
    assert not model.messages


def test_successful_empty_read_is_preserved_as_data():
    class EmptyBackend(Backend):
        async def call(self, *args):
            return {'rooms': [], 'devices': [], 'scenes': []}
    model = Model([output(query([read()])), ModelReply('Nhà chưa có thiết bị.')])
    workflow = Workflow()
    result = chat(ConversationAgent(model, EmptyBackend(), workflow), 'Nhà có thiết bị nào?')
    assert result['trace'][0]['status'] == 'success'
    assert workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices'] == []


def test_dialogue_question_can_answer_without_backend_read():
    value = Interpretation(kind='conversation', goal='Đang nhờ việc gì?', answer_sources=['conversation'])
    assert check_contract(value).intents == []


def test_schema_failure_logs_reason_without_user_or_model_content(caplog):
    secret = 'private-conversation-value'
    bad = query([read()])
    bad['intents'][0]['read_focus'] = [{'path': 'device_id', 'entity': 'invalid', 'name': secret}]
    bad[secret] = secret
    workflow = Workflow()
    with pytest.raises(AgentUnavailable):
        chat(ConversationAgent(Model([output(bad), output(bad)]), Backend(), workflow), secret)
    assert 'agent_interpretation_rejected attempt=2' in caplog.text
    assert 'read_focus.0.entity' in caplog.text
    assert 'literal_error' in caplog.text
    assert secret not in caplog.text


def test_contract_failure_logs_stable_reason_without_raw_payload(caplog):
    with pytest.raises(AgentUnavailable):
        chat(ConversationAgent(Model([output(query()), output(query())]), Backend(), Workflow()),
             'private-user-utterance')
    assert 'empty_query_plan' in caplog.text
    assert 'private-user-utterance' not in caplog.text
