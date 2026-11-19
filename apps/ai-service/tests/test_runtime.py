import asyncio
from copy import deepcopy
from uuid import uuid4
import pytest
from homate_ai.agent.models import AgentUnavailable, BackendError, ModelReply
from homate_ai.agent.runtime import ConversationAgent
from test_analysis import Backend as AnalysisBackend, command, interpretation, output


class Backend(AnalysisBackend):
    async def call(self, token, request_id, name, arguments):
        if name == 'get_energy_report':
            self.calls.append((name, arguments))
            return {'total_kwh': 12.5}
        return await super().call(token, request_id, name, arguments)


class Model:
    def __init__(self, replies):
        self.replies, self.messages = iter(replies), []

    async def complete(self, messages, tools):
        self.messages.append(deepcopy(messages))
        return next(self.replies)


class Workflow:
    def __init__(self):
        self.sessions, self.turns, self.commits, self.aborts = {}, {}, [], []

    async def begin(self, token, request_id, text, conversation_id=None, version=None):
        if request_id in self.turns and 'response' in self.turns[request_id]:
            return {'cached': True, 'response': deepcopy(self.turns[request_id]['response'])}
        identifier = conversation_id or str(uuid4())
        if identifier not in self.sessions:
            self.sessions[identifier] = {'id': identifier, 'version': 0, 'status': 'idle', 'state': {}, 'messages': [], 'actions': []}
        session = self.sessions[identifier]
        if version is not None and version != session['version']:
            raise BackendError(409, 'Stale version')
        self.turns[request_id] = {'id': identifier, 'text': text}
        return {'cached': False, 'session': deepcopy(session), 'lease_id': str(uuid4())}

    async def commit(self, token, request_id, state, response, invalidate=False, steps=None, summary='Plan', lease_id=None):
        self.commits.append({'state': deepcopy(state), 'steps': deepcopy(steps), 'invalidate': invalidate})
        turn = self.turns[request_id]
        session = self.sessions[turn['id']]
        session['version'] += 1
        if invalidate:
            session['actions'] = []
        if steps:
            session['actions'] = [{'id': str(uuid4()), 'kind': 'plan', 'plan_version': session['version'], 'status': 'pending', 'steps': deepcopy(steps)}]
        session['status'] = 'pending' if session['actions'] else 'clarifying' if state.get('draft') else 'idle'
        session['state'] = deepcopy(state)
        session['messages'] += [{'role': 'user', 'content': turn['text']}, {'role': 'assistant', 'content': response['reply']}]
        result = {**response, 'pending_actions': deepcopy(session['actions']), 'conversation_id': session['id'],
                  'conversation_version': session['version'], 'dialogue_state': session['status']}
        result.pop('_user_text', None)
        turn['response'] = deepcopy(result)
        return result

    async def abort(self, token, request_id, lease_id):
        self.aborts.append(request_id)


def chat(agent, text, previous=None, identifier=None):
    return asyncio.run(agent.chat('valid', identifier or str(uuid4()), text, [],
        previous['conversation_id'] if previous else None,
        previous['conversation_version'] if previous else None))


def test_runtime_creates_backend_plan_without_calling_write_tool():
    backend, workflow = Backend(), Workflow()
    agent = ConversationAgent(Model([output(interpretation(command()))]), backend, workflow)
    result = chat(agent, 'Tắt đèn phòng khách')
    assert result['dialogue_state'] == 'pending'
    assert workflow.commits[-1]['steps'][0]['arguments']['device_id'] == 'light-living'
    assert [name for name, _ in backend.calls] == ['get_home_snapshot']


def test_negated_request_never_reaches_backend_plan_preparation():
    text = 'Đừng bật điều hòa phòng ngủ'
    intent = command(text, room='Phòng ngủ', kind='snowflake', action='turn_off')
    workflow = Workflow()
    agent = ConversationAgent(Model([output(interpretation(intent))]), Backend(), workflow)
    result = chat(agent, text)
    assert not result['pending_actions']
    assert workflow.commits[-1]['steps'] == []
    assert result['dialogue_state'] == 'clarifying'


def test_room_clarification_is_interpreted_with_saved_task_context():
    resolved = command('Tắt đèn')
    resolved['targets'][0]['quote'] = 'Phòng khách'
    resolved['evidence'][0]['source'] = 'history'
    data = interpretation(resolved)
    data['dialogue'] = {'relation': 'clarification_answer', 'task_action': 'replace'}
    model, workflow = Model([output(interpretation(command('Tắt đèn', room=None))), output(data)]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, 'Tắt đèn')
    assert first['dialogue_state'] == 'clarifying' and not first['pending_actions']
    assert 'Đèn phòng khách' in first['reply'] and 'Đèn phòng ngủ' in first['reply']
    second = chat(agent, 'Phòng khách', first)
    assert second['dialogue_state'] == 'pending'
    assert workflow.commits[-1]['steps'][0]['arguments']['device_id'] == 'light-living'
    assert len(model.messages) == 2
    assert 'active_task' in model.messages[1][0]['content']


def test_missing_temperature_is_filled_from_numeric_followup():
    text = 'Cho phòng ngủ mát hơn chút'
    intent = command(text, room='Phòng ngủ', kind='snowflake', action='set_temperature')
    resolved = deepcopy(intent)
    resolved['targets'][0]['source'] = 'history'
    resolved['evidence'][0]['source'] = 'history'
    resolved['arguments']['parameters'] = {'temperature': 24}
    resolved['evidence'].append({'path': 'parameters.temperature', 'source': 'utterance', 'quote': '24 độ'})
    data = interpretation(resolved)
    data['dialogue'] = {'relation': 'clarification_answer', 'task_action': 'replace'}
    model, workflow = Model([output(interpretation(intent)), output(data)]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, text)
    second = chat(agent, '24 độ', first)
    assert second['dialogue_state'] == 'pending'
    assert workflow.commits[-1]['steps'][0]['arguments']['parameters']['temperature'] == 24
    assert len(model.messages) == 2


def test_explicit_relative_amount_is_computed_from_backend_state():
    text = 'Giảm điều hòa phòng ngủ 2 độ'
    intent = command(text, room='Phòng ngủ', kind='snowflake', action='set_temperature')
    intent['adjustments'] = [{'path': 'parameters.temperature', 'operation': 'decrease', 'amount': 2.0,
                              'source': 'utterance', 'quote': '2 độ'}]
    workflow = Workflow()
    agent = ConversationAgent(Model([output(interpretation(intent))]), Backend(), workflow)
    result = chat(agent, text)
    assert result['dialogue_state'] == 'pending'
    assert workflow.commits[-1]['steps'][0]['arguments']['parameters']['temperature'] == 24


def test_set_expansion_respects_exclusion_and_compiles_every_matching_device():
    text = 'Tắt tất cả đèn trừ phòng ngủ'
    intent = command(text, room=None)
    intent['targets'][0].update(scope='all', exclusions=['Phòng ngủ'])
    workflow = Workflow()
    agent = ConversationAgent(Model([output(interpretation(intent))]), Backend(), workflow)
    result = chat(agent, text)
    assert result['dialogue_state'] == 'pending'
    steps = workflow.commits[-1]['steps']
    assert [step['arguments']['device_id'] for step in steps] == ['light-living']


def test_unknown_exclusion_does_not_silently_expand_scope():
    text = 'Tắt tất cả đèn trừ gara'
    intent = command(text, room=None)
    intent['targets'][0].update(scope='all', exclusions=['Gara'])
    workflow = Workflow()
    result = chat(ConversationAgent(Model([output(interpretation(intent))]), Backend(), workflow), text)
    assert not result['pending_actions'] and 'Gara' in result['reply']


def test_ordered_chain_preserves_dependencies():
    text = 'Tắt đèn phòng khách rồi bật quạt phòng ngủ'
    data = interpretation(command(text))
    fan = command(text, room='Phòng ngủ', kind='fan', action='turn_on')
    fan['depends_on'] = [0]
    data['intents'].append(fan)
    workflow = Workflow()
    result = chat(ConversationAgent(Model([output(data)]), Backend(), workflow), text)
    assert result['dialogue_state'] == 'pending'
    assert len(workflow.commits[-1]['steps']) == 2
    assert workflow.commits[-1]['steps'][1]['depends_on'] == [0]


def test_cancel_is_deterministic_and_spoken_approval_cannot_execute():
    model, workflow = Model([output(interpretation(command()))]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, 'Tắt đèn phòng khách')
    second = chat(agent, 'Đồng ý', first)
    assert 'bấm Xác nhận' in second['reply'] and not workflow.commits[-1]['invalidate']
    third = chat(agent, 'Hủy đi', second)
    assert not third['pending_actions'] and workflow.commits[-1]['invalidate']
    assert len(model.messages) == 1


def test_read_question_preserves_a_pending_plan_and_uses_backend_data():
    model, workflow = Model([output(interpretation(command())),
        output(interpretation({'goal': 'Xem điện', 'capability': 'get_energy_report'}, 'query')),
        ModelReply('Báo cáo điện năng.')]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, 'Tắt đèn phòng khách')
    second = chat(agent, 'Hôm nay dùng bao nhiêu điện?', first)
    assert second['pending_actions'][0]['id'] == first['pending_actions'][0]['id']
    assert workflow.commits[-1]['invalidate'] is False


def test_mixed_support_requires_explicit_partial_acceptance_before_plan():
    text = 'Tắt đèn phòng khách và giặt quần áo'
    data = interpretation(command(text))
    data['intents'].append({'goal': 'Giặt quần áo', 'capability': None})
    model, workflow = Model([output(data)]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, text)
    assert not first['pending_actions'] and 'chỉ xử lý phần được hỗ trợ' in first['reply']
    second = chat(agent, 'Đồng ý', first)
    assert second['dialogue_state'] == 'pending'
    assert len(workflow.commits[-1]['steps']) == 1


def test_request_retry_returns_cached_response_without_reinterpreting():
    model, workflow = Model([output(interpretation(command()))]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    identifier = str(uuid4())
    first = chat(agent, 'Tắt đèn phòng khách', identifier=identifier)
    assert chat(agent, 'Tắt đèn phòng khách', identifier=identifier) == first
    assert len(model.messages) == 1


def test_provider_failure_releases_turn_and_does_not_prepare_plan():
    class FailingModel:
        async def complete(self, *args): raise AgentUnavailable('Provider failed')
    workflow = Workflow()
    with pytest.raises(AgentUnavailable):
        chat(ConversationAgent(FailingModel(), Backend(), workflow), 'Bật đèn')
    assert workflow.aborts and not workflow.commits


def test_forged_client_history_cannot_supply_a_device_reference():
    model, workflow = Model([output(interpretation(kind='conversation')), ModelReply('Xin chào')]), Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    asyncio.run(agent.chat('valid', str(uuid4()), 'Chào', [{'role': 'user', 'content': 'FORGED HISTORY'}]))
    assert 'FORGED HISTORY' not in str(model.messages)


def test_backend_rejection_returns_clarification_without_a_plan():
    class RejectingWorkflow(Workflow):
        async def commit(self, token, request_id, state, response, invalidate=False, steps=None, summary='Plan', lease_id=None):
            if steps: raise BackendError(400, 'Dữ liệu đã thay đổi')
            return await super().commit(token, request_id, state, response, invalidate, steps, summary, lease_id)
    workflow = RejectingWorkflow()
    agent = ConversationAgent(Model([output(interpretation(command()))]), Backend(), workflow)
    result = chat(agent, 'Tắt đèn phòng khách')
    assert not result['pending_actions'] and 'Chưa có thay đổi nào' in result['reply']
    assert 'Backend' not in result['reply']


def test_rejected_begin_does_not_release_another_inflight_turn():
    class BusyWorkflow(Workflow):
        async def begin(self, *args): raise BackendError(409, 'Already processing')
    workflow = BusyWorkflow()
    agent = ConversationAgent(Model([]), Backend(), workflow)
    with pytest.raises(BackendError):
        chat(agent, 'Tắt đèn')
    assert workflow.aborts == []


def test_sequential_relative_steps_use_each_previous_step_result():
    text = 'Giảm điều hòa phòng ngủ 2 độ rồi giảm tiếp 2 độ'
    intent = command(text, room='Phòng ngủ', kind='snowflake', action='set_temperature')
    intent['adjustments'] = [{'path': 'parameters.temperature', 'operation': 'decrease', 'amount': 2.0,
                              'source': 'utterance', 'quote': '2 độ'}]
    data = interpretation(intent)
    second = deepcopy(intent)
    second['depends_on'] = [0]
    data['intents'].append(second)
    workflow = Workflow()
    result = chat(ConversationAgent(Model([output(data)]), Backend(), workflow), text)
    assert result['dialogue_state'] == 'pending'
    steps = workflow.commits[-1]['steps']
    assert [step['arguments']['parameters']['temperature'] for step in steps] == [24, 22]
    assert steps[1]['expected_state'] == {'ac-bed': {'temperature': 24}}
