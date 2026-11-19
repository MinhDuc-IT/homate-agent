import pytest
from homate_ai.agent.models import ModelReply
from homate_ai.agent.runtime import ConversationAgent
from test_analysis import output
from test_runtime import Model, Workflow, chat
from test_read_scope import HomeBackend


def request(room=None, kind='query', relation='new_request', **extra):
    selector = {'path': 'device_id', 'entity': 'device', 'kind': 'snowflake'}
    if room:
        selector['room'] = room
    intent = {'goal': 'Nhiệt độ điều hòa', 'capability': 'get_home_snapshot',
              'arguments': {}, 'read_focus': [selector], 'requested_fields': ['temperature']}
    intent.update(extra)
    return output({'kind': kind, 'goal': 'Nhiệt độ điều hòa', 'answer_sources': ['backend'],
        'dialogue': {'relation': relation, 'task_action': 'replace' if kind == 'action' else 'preserve'},
        'intents': [intent]})


@pytest.mark.parametrize('fragment', ['phòng khách', 'cái ở phòng khách nhé', 'cho mình xem ở phòng khách'])
def test_fragment_uses_server_transcript_without_quote_or_memory_object(fragment):
    model = Model([request(), request('phòng khách', relation='clarification_answer'),
                   ModelReply('Điều hòa phòng khách đang đặt 25°C.')])
    workflow = Workflow()
    agent = ConversationAgent(model, HomeBackend(), workflow)
    first = chat(agent, 'Điều hòa đang bao nhiêu độ?')
    assert first['dialogue_state'] == 'clarifying'
    second = chat(agent, fragment, first)
    assert second['dialogue_state'] == 'idle'
    observed = workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices']
    assert [d['id'] for d in observed] == ['ac-living']
    history = model.messages[1]
    assert any(m['role'] == 'user' and m['content'] == 'Điều hòa đang bao nhiêu độ?' for m in history)
    assert any(m['role'] == 'assistant' and m['content'] == first['reply'] for m in history)
    assert history[-1]['content'] == fragment


def test_contextual_write_still_requires_backend_confirmation():
    selector = {'path': 'device_id', 'entity': 'device', 'kind': 'snowflake', 'room': 'phòng khách'}
    model = Model([request('phòng khách'), ModelReply('Đang đặt 25°C.'),
        request('phòng khách', kind='action', relation='correction', capability='control_device',
                arguments={'action': 'set_temperature', 'parameters': {}}, targets=[selector], read_focus=[],
                adjustments=[{'path': 'parameters.temperature', 'operation': 'decrease', 'amount': 2.0}])])
    # A write is an updated request rather than a preserved read task.
    workflow = Workflow()
    agent = ConversationAgent(model, HomeBackend(), workflow)
    first = chat(agent, 'Cho xem nhiệt độ điều hòa phòng khách')
    second = chat(agent, 'Giảm nó hai độ', first)
    assert second['pending_actions']
    step = workflow.commits[-1]['steps'][0]
    assert step['arguments']['device_id'] == 'ac-living'
    assert step['arguments']['parameters']['temperature'] == 23
    assert workflow.commits[-1]['state']['draft']


def test_contextual_selection_cannot_use_nonexistent_entity():
    agent = ConversationAgent(Model([request('phòng không tồn tại')]), HomeBackend(), Workflow())
    result = chat(agent, 'Cái trong phòng đó')
    assert not result['pending_actions'] and not result['trace']
    assert result['analysis']['reviews'][0]['issues'][0]['code'] == 'target_not_found'


def test_contextual_tool_schema_has_no_lexical_proof_fields_or_root_combinators():
    class SchemaModel(Model):
        async def complete(self, messages, tools):
            if tools:
                schema = tools[0]['function']['parameters']
                assert schema['type'] == 'object'
                assert not set(schema) & {'oneOf', 'anyOf', 'allOf', 'enum', 'const', 'not'}
                assert 'intents' in schema['required']
                assert not set(schema['$defs']['Target']['properties']) & {'quote', 'source', 'memory_ref', 'scope_evidence'}
                assert 'evidence' not in schema['$defs']['Intent']['properties']
            return await super().complete(messages, tools)
    agent = ConversationAgent(SchemaModel([request('phòng khách'), ModelReply('25°C.')]), HomeBackend(), Workflow())
    assert chat(agent, 'Xem điều hòa phòng khách')['trace'][0]['status'] == 'success'


def test_state_field_path_preserves_actual_value():
    workflow = Workflow()
    model = Model([request('phòng khách', requested_fields=['state.temperature']), ModelReply('25°C.')])
    chat(ConversationAgent(model, HomeBackend(), workflow), 'Nhiệt độ phòng khách?')
    devices = workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices']
    assert devices[0]['state'] == {'temperature': 25}
