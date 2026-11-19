from copy import deepcopy
import pytest
from homate_ai.agent.models import ModelReply
from homate_ai.agent.memory import validate_transition
from homate_ai.agent.interpretation import Interpretation
from test_analysis import command, interpretation, output
from test_runtime import Backend, Model, Workflow, chat
from homate_ai.agent.runtime import ConversationAgent


def turn(intent, kind, relation, action, goal):
    data = interpretation(intent, kind)
    data['goal'] = goal
    data['dialogue'] = {'relation': relation, 'task_action': action,
                        'topic': 'Thiết bị trong nhà', 'user_goal': goal}
    return output(data)


def reading(quote, room='Phòng ngủ', kind='snowflake', source='history', fields=None):
    return {'goal': 'Đọc thông số hiện tại của thiết bị đang được hỏi',
            'capability': 'get_home_snapshot', 'arguments': {},
            'read_focus': [{'path': 'device_id', 'entity': 'device', 'room': room,
                            'kind': kind, 'source': source, 'quote': quote}],
            'requested_fields': fields or ['temperature']}


@pytest.mark.parametrize('question', ['hiện tại đang là bao nhiêu độ',
    'Khoan đã, cho mình xem mức đang đặt trước nhé', 'Thông số của nó lúc này thế nào?'])
def test_model_resolves_side_question_and_resumes_original_goal_after_reload(question):
    initial = 'Giảm điều hòa phòng ngủ 2 độ'
    intent = command(initial, room='Phòng ngủ', kind='snowflake', action='set_temperature')
    intent['adjustments'] = [{'path': 'parameters.temperature', 'operation': 'decrease',
                              'amount': 2.0, 'source': 'utterance', 'quote': '2 độ'}]
    workflow, backend = Workflow(), Backend()
    first_model = Model([turn(intent, 'action', 'new_request', 'replace', initial)])
    first = chat(ConversationAgent(first_model, backend, workflow), initial)
    assert workflow.commits[-1]['steps'][0]['arguments']['parameters']['temperature'] == 24
    active = deepcopy(workflow.commits[-1]['state']['draft'])
    corrected = command('Đặt điều hòa phòng ngủ 23 độ', room='Phòng ngủ', kind='snowflake',
                        action='set_temperature', parameters={'temperature': 23})
    corrected['targets'][0].update(source='history', quote='điều hòa phòng ngủ')
    corrected['evidence'] = [{'path': 'action', 'source': 'utterance', 'quote': 'đặt'},
                             {'path': 'parameters.temperature', 'source': 'utterance', 'quote': '23'}]
    model = Model([turn(reading('điều hòa phòng ngủ'), 'query', 'follow_up', 'preserve',
                        'Nhiệt độ đang đặt của điều hòa phòng ngủ'),
                   ModelReply('Điều hòa phòng ngủ đang đặt ở 26°C.'),
                   turn(corrected, 'correction', 'resume', 'replace', 'Đặt điều hòa phòng ngủ 23 độ')])
    # New agent instance: all context must come from server state, not a Python field.
    agent = ConversationAgent(model, backend, workflow)
    second = chat(agent, question, first)
    assert second['pending_actions'][0]['id'] == first['pending_actions'][0]['id']
    assert workflow.commits[-1]['state']['draft'] == active
    memory = workflow.commits[-1]['state']['conversation']
    assert memory['relation'] == 'follow_up'
    devices = memory['observations'][0]['result']['devices']
    assert [d['id'] for d in devices] == ['ac-bed']
    assert devices[0]['state'] == {'temperature': 26}
    assert 'active_task' in model.messages[0][0]['content']
    assert workflow.commits[-1]['steps'] == []
    third = chat(agent, 'Vậy đặt 23 đi', second)
    assert third['pending_actions'][0]['id'] != first['pending_actions'][0]['id']
    assert workflow.commits[-1]['steps'][0]['arguments']['parameters']['temperature'] == 23
    context = model.messages[2][0]['content']
    assert 'observations' in context and initial in context


def test_ambiguous_side_question_does_not_replace_the_unfinished_task():
    initial = 'Tắt đèn phòng khách'
    model = Model([turn(command(), 'action', 'new_request', 'replace', initial),
                   turn(reading('đèn', room=None, kind='bulb', source='utterance', fields=['power']),
                        'query', 'follow_up', 'preserve', 'Hỏi trạng thái đèn')])
    workflow = Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, initial)
    original = deepcopy(workflow.commits[-1]['state']['draft'])
    second = chat(agent, 'Còn đèn thì sao?', first)
    saved = workflow.commits[-1]
    assert saved['state']['draft'] == original
    assert 'side_question' in saved['state']
    assert saved['state']['conversation']['last_turn']['reviews'][0]['status'] == 'needs_clarification'
    assert second['pending_actions'][0]['id'] == first['pending_actions'][0]['id']
    assert not saved['invalidate'] and not saved['steps']


def test_explicit_new_read_topic_uses_new_entity_without_cancelling_pending_task():
    initial = 'Đặt điều hòa phòng ngủ 24 độ'
    first_intent = command(initial, room='Phòng ngủ', kind='snowflake', action='set_temperature', parameters={'temperature': 24})
    first_intent['evidence'].append({'path': 'parameters.temperature', 'source': 'utterance', 'quote': '24'})
    model = Model([turn(first_intent, 'action', 'new_request', 'replace', initial),
        turn(reading('đèn phòng khách', 'Phòng khách', 'bulb', 'utterance', ['brightness']),
             'query', 'topic_change', 'preserve', 'Độ sáng đèn phòng khách'), ModelReply('Đèn phòng khách đang ở 50%.')])
    workflow = Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, initial)
    second = chat(agent, 'Chuyện khác, đèn phòng khách sáng mức nào?', first)
    assert workflow.commits[-1]['state']['conversation']['observations'][0]['result']['devices'][0]['id'] == 'light-living'
    assert second['pending_actions'][0]['id'] == first['pending_actions'][0]['id']
    from homate_ai.agent.memory import context_for
    context = context_for(workflow.sessions[second['conversation_id']])
    references = {e['reference_id']: e['usage'] for e in context['conversation']['entities']}
    assert references['device_id:ac-bed'] == ['active_task']
    assert references['device_id:light-living'] == ['recent_topic']


def test_transcript_can_supply_context_without_literal_user_quote():
    model = Model([turn(None, 'conversation', 'new_request', 'preserve', 'Chào'), ModelReply('Bạn đang nói về điều hòa phòng ngủ.'),
                   turn(reading('điều hòa phòng ngủ'), 'query', 'follow_up', 'preserve', 'Hỏi nhiệt độ'),
                   ModelReply('Điều hòa phòng ngủ đang đặt 26°C.')])
    workflow = Workflow()
    agent = ConversationAgent(model, Backend(), workflow)
    first = chat(agent, 'Xin chào')
    second = chat(agent, 'Nó đang bao nhiêu?', first)
    assert not second['pending_actions']
    review = second['analysis']['reviews'][0]
    assert review['status'] == 'ready_for_review'
    assert second['trace'][0]['status'] == 'success'


def test_relationship_cannot_clear_a_task_under_an_uncertain_followup_label():
    value = Interpretation.model_validate({'kind': 'query', 'goal': 'Hỏi thêm',
        'dialogue': {'relation': 'follow_up', 'task_action': 'clear'}})
    with pytest.raises(ValueError, match='preserve'):
        validate_transition(value)


@pytest.mark.parametrize('reference,room,ready', [('device_id:ac-bed', None, True),
    ('device_id:foreign-home', None, False), ('device_id:ac-bed', 'Phòng khách', False)])
def test_model_selected_memory_link_is_verified_against_user_evidence_and_fresh_scope(reference, room, ready):
    initial = 'Giảm điều hòa phòng ngủ 2 độ'
    intent = command(initial, room='Phòng ngủ', kind='snowflake', action='set_temperature')
    # A missing value still establishes a grounded subject, not an executed fact.
    query = reading('nó', room=room, kind=None, source='utterance')
    query['read_focus'][0]['memory_ref'] = reference
    replies = [turn(intent, 'action', 'new_request', 'replace', initial),
               turn(query, 'query', 'follow_up', 'preserve', 'Đọc thông số đối tượng được tham chiếu')]
    if ready:
        replies.append(ModelReply('Điều hòa phòng ngủ đang đặt ở 26°C.'))
    workflow = Workflow()
    agent = ConversationAgent(Model(replies), Backend(), workflow)
    first = chat(agent, initial)
    second = chat(agent, 'Thông số của nó lúc này ra sao?', first)
    review = second['analysis']['reviews'][0]
    assert (review['status'] == 'ready_for_review') == ready
    assert not workflow.commits[-1]['steps']
    if ready:
        assert review['read_context']['entities'] == {'device_id': 'ac-bed'}
        assert review['read_context']['provenance']['device_id']['quote'] == initial


def test_reply_receives_active_task_and_backend_receipt_as_separate_kinds_of_context():
    workflow = Workflow()
    first = chat(ConversationAgent(Model([turn(command(), 'action', 'new_request', 'replace', 'Tắt đèn phòng khách')]), Backend(), workflow), 'Tắt đèn phòng khách')
    saved = workflow.sessions[first['conversation_id']]['state']
    saved['conversation']['execution'] = {'status': 'failed', 'steps': [{'status': 'failed', 'summary': 'Một việc trước đó'}]}
    model = Model([turn(None, 'conversation', 'follow_up', 'preserve', 'Hỏi việc đang chờ'), ModelReply('Bạn đang chờ xác nhận tắt đèn phòng khách.')])
    result = chat(ConversationAgent(model, Backend(), workflow), 'Tôi đang nhờ bạn làm việc gì ấy nhỉ?', first)
    prompt = model.messages[-1][0]['content']
    assert 'active_goal' in prompt and 'execution_receipt' in prompt
    assert 'pending' in prompt and 'failed' in prompt
    assert result['pending_actions'][0]['id'] == first['pending_actions'][0]['id']
