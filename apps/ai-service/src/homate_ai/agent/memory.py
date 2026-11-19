"""Request-scoped context and durable, evidence-backed conversational memory.

The model chooses turn relationships. Code enforces transitions and records only
grounded references and actual read results, never model-written device facts.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from homate_ai.agent.capabilities import CAPABILITIES
from homate_ai.agent.models import AgentUnavailable


def context_for(session):
    state = session['state']
    memory = deepcopy(state.get('conversation', {}))
    references = {}
    for item in memory.get('entities', []):
        item['reference_id'] = item['path'] + ':' + str(item['value'])
        item['usage'] = ['recent_topic']
        references[item['reference_id']] = item
    for review in (state.get('draft') or {}).get('report', {}).get('reviews', []):
        if review.get('status') == 'forbidden':
            continue
        for path, proof in review.get('provenance', {}).items():
            if isinstance(proof, dict) and proof.get('source') == 'backend' and path.endswith('_id'):
                identifier = path + ':' + str(proof['value'])
                if identifier in references:
                    references[identifier]['usage'].append('active_task')
                else:
                    references[identifier] = {'path': path, **deepcopy(proof), 'reference_id': identifier, 'usage': ['active_task']}
    memory['entities'] = list(references.values())
    return {'version': 1, 'conversation': memory,
            'active_task': state.get('draft'), 'task_status': session['status'],
            'side_question': state.get('side_question'), 'partial_candidate': state.get('partial_candidate')}


def resolve_references(intent, context, snapshot, schedules, history):
    """The model selects a memory link; code verifies its original user evidence."""
    from homate_ai.agent.grounding import has_evidence, normalize
    from homate_ai.agent.interpretation import Issue
    value = intent.model_copy(deep=True)
    errors = []
    references = {item['reference_id']: item for item in context.get('conversation', {}).get('entities', [])}
    collections = {'device': snapshot['devices'], 'room': snapshot['rooms'],
                   'scene': snapshot['scenes'], 'schedule': schedules}
    for target in [*value.targets, *value.read_focus]:
        if not target.memory_ref:
            continue
        proof = references.get(target.memory_ref)
        item = next((item for item in collections[target.entity] if proof and item['id'] == proof.get('value')), None)
        valid = proof and proof.get('source') == 'backend' and item
        if valid and target.name:
            valid = normalize(target.name) in {normalize(item['id']), normalize(item['name'])}
        if valid and target.kind:
            valid = item.get('kind') == target.kind
        if valid and target.room:
            valid = any(room['id'] == item.get('room') and normalize(target.room) in {
                normalize(room['id']), normalize(room['name'])} for room in snapshot['rooms'])
        if not valid:
            errors.append(Issue(code='unverified_target', path=target.path,
                                message='Tham chiếu hội thoại chưa có đối tượng và bằng chứng phù hợp.'))
            target.source = 'assumption'
            continue
        target.name, target.reference = item['id'], None
        target.source, target.quote = 'history', proof['quote']
    return value, errors


def validate_transition(interpretation):
    decision = interpretation.dialogue
    if decision is None:
        return  # Observer and deterministic approval/cancel paths.
    if decision.task_action == 'clear' and decision.relation != 'cancel' and interpretation.kind != 'cancel':
        raise ValueError('Only an explicit cancellation can clear the active task. A new read question or topic change must preserve it.')
    if decision.relation in {'follow_up', 'unclear'} and decision.task_action != 'preserve':
        raise ValueError('A follow-up question or uncertain relationship must preserve the active task')
    if interpretation.kind == 'query' and decision.task_action == 'replace':
        raise ValueError('A read question must not replace a pending task; choose preserve or explicitly clear it')
    if decision.task_action == 'preserve' and any(CAPABILITIES.get(i.capability) and
            CAPABILITIES[i.capability].effect == 'write' for i in interpretation.intents):
        raise ValueError('A preserved task cannot propose writes; use replace for an updated full action request')
    if decision.task_action == 'clear' and interpretation.kind not in {'cancel', 'query', 'conversation'}:
        raise ValueError('Clearing a task must not also propose a write; use correction/replace')


def update_memory(state):
    previous = state['session']['state']
    current = deepcopy(state['next_state'])
    interpretation = state['interpretation']
    decision = interpretation.dialogue
    task_action = decision.task_action if decision else (
        'clear' if interpretation.kind == 'cancel' else 'replace' if state['invalidate'] else 'preserve')
    if task_action == 'preserve':
        if state['steps']:
            raise AgentUnavailable('Yêu cầu mới chưa rõ là hỏi thêm hay thay đổi thao tác. Bạn nói rõ giúp tôi nhé.')
        # A side question has its own clarification state; never overwrite the
        # unfinished write task with that question, even when it is ambiguous.
        if previous.get('draft'):
            if current.get('draft') and current['draft'] != previous['draft']:
                current['side_question'] = current['draft']
            current['draft'] = deepcopy(previous['draft'])
        if previous.get('partial_candidate'):
            current['partial_candidate'] = deepcopy(previous['partial_candidate'])
        if not state.get('planning_error') and all(r.status == 'ready_for_review' for r in state['report'].reviews):
            current.pop('side_question', None)
            if decision and decision.relation == 'clarification_answer' and (
                    previous.get('draft', {}).get('interpretation', {}).get('kind') == 'query'):
                current.pop('draft', None)
        state['invalidate'] = False
    elif task_action == 'clear':
        current = {'cancelled': True}
        state['invalidate'] = True
    else:
        current.pop('side_question', None)
    old = previous.get('conversation', {})
    entities = []
    for review in state['report'].reviews:
        if review.status == 'forbidden':
            continue
        bindings = {**review.provenance, **review.read_context.get('provenance', {})}
        for path, binding in bindings.items():
            if isinstance(binding, dict) and binding.get('source') == 'backend' and path.endswith('_id'):
                entities.append({'path': path, **deepcopy(binding)})
    # Preserve multiple candidates rather than silently choosing the last one.
    observations = state.get('observations', [])
    if len(json.dumps(observations, ensure_ascii=False)) > 18000:
        observations = [{'tool': item['tool'], 'result': {'omitted': 'Large result; read again for current facts'}} for item in observations]
    memory = {'version': 1, 'topic': (decision.topic or old.get('topic', '')) if decision else old.get('topic', ''),
              'user_goal': (decision.user_goal or old.get('user_goal', '')) if decision else old.get('user_goal', ''),
              'relation': decision.relation if decision else ('cancel' if interpretation.kind == 'cancel' else old.get('relation', 'new_request')),
              'entities': entities or old.get('entities', []),
              'last_turn': {'interpretation': interpretation.model_dump(),
                            'reviews': [r.model_dump() for r in state['report'].reviews]},
              'observations': observations,
              'updated_at': datetime.now(timezone.utc).isoformat()}
    if old.get('execution'):
        memory['execution'] = deepcopy(old['execution'])
    current['conversation'] = memory
    return current
