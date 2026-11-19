from copy import deepcopy
from homate_ai.agent.models import ModelReply
from homate_ai.agent.runtime import ConversationAgent
from test_analysis import SNAPSHOT, output
from test_runtime import Backend, Model, Workflow, chat


class HomeBackend(Backend):
    async def call(self, token, request_id, name, arguments):
        data = await super().call(token, request_id, name, arguments)
        if name == 'get_home_snapshot':
            other = deepcopy(SNAPSHOT['devices'][2])
            other.update(id='ac-living', name='Điều hòa phòng khách', room='living')
            other['state']['temperature'] = 25
            data['devices'].append(other)
        return data


def query(targets, relation='new_request'):
    return output({'kind': 'query', 'goal': 'Xem nhiệt độ điều hòa', 'answer_sources': ['backend'],
        'dialogue': {'relation': relation, 'task_action': 'preserve'},
        'intents': [{'goal': 'Xem nhiệt độ điều hòa', 'capability': 'get_home_snapshot',
                    'arguments': {}, 'read_focus': targets, 'requested_fields': ['temperature']}]})


def target(**extra):
    return {'path': 'device_id', 'entity': 'device', 'kind': 'snowflake', 'quote': 'điều hòa', **extra}


def test_ambiguous_read_asks_then_room_answer_continues_same_query():
    workflow, backend = Workflow(), HomeBackend()
    model = Model([query([target()]), query([target(room='phòng ngủ', quote='phòng ngủ')],
        'clarification_answer'), ModelReply('Điều hòa phòng ngủ đang đặt 26°C.')])
    agent = ConversationAgent(model, backend, workflow)
    first = chat(agent, 'điều hòa đang bao nhiêu độ')
    assert 'hay' in first['reply']
    assert first['analysis']['reviews'][0]['issues'][0]['code'] == 'ambiguous_target'
    assert workflow.commits[-1]['state']['draft']['interpretation']['kind'] == 'query'
    second = chat(agent, 'phòng ngủ', first)
    assert second['trace'][0]['status'] == 'success'
    devices = workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices']
    assert [d['id'] for d in devices] == ['ac-bed']
    assert not second['pending_actions']
    assert second['dialogue_state'] == 'idle'


def test_explicit_all_reads_all_matching_devices():
    workflow = Workflow()
    agent = ConversationAgent(Model([query([target(scope='all', quote='tất cả điều hòa',
        scope_evidence={'path': 'scope', 'source': 'utterance', 'quote': 'tất cả điều hòa'})]),
        ModelReply('Phòng ngủ 26°C; phòng khách 25°C.')]), HomeBackend(), workflow)
    chat(agent, 'tất cả điều hòa đang bao nhiêu độ')
    devices = workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices']
    assert {d['id'] for d in devices} == {'ac-bed', 'ac-living'}


def test_multiple_explicit_read_targets_are_combined_without_invalid_value():
    workflow = Workflow()
    agent = ConversationAgent(Model([query([target(room='phòng ngủ', quote='phòng ngủ'),
        target(room='phòng khách', quote='phòng khách')]), ModelReply('26°C và 25°C.')]), HomeBackend(), workflow)
    result = chat(agent, 'điều hòa phòng ngủ và phòng khách đang bao nhiêu độ')
    assert result['analysis']['reviews'][0]['status'] == 'ready_for_review'
    assert len(workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices']) == 2


def test_ambiguous_descriptions_still_require_selection_without_lexical_gate():
    workflow = Workflow()
    bad = query([target(quote='Điều hòa phòng ngủ'), target(quote='Điều hòa phòng khách')])
    result = chat(ConversationAgent(Model([bad, bad]), HomeBackend(), workflow), 'điều hòa đang bao nhiêu độ')
    assert not result['trace']
    assert all(i['code'] == 'ambiguous_target' for i in result['analysis']['reviews'][0]['issues'])
    assert 'hay' in result['reply']


def test_contextual_all_does_not_require_extra_evidence_object():
    workflow = Workflow()
    result = chat(ConversationAgent(Model([query([target(scope='all')]), ModelReply('26°C và 25°C.')]), HomeBackend(), workflow),
                  'tất cả điều hòa đang bao nhiêu độ')
    assert result['trace'][0]['status'] == 'success'
