"""Expand explicit sets and compile validated intents into an ordered plan."""
from copy import deepcopy
from homate_ai.agent.capabilities import CAPABILITIES
from homate_ai.agent.grounding import has_evidence, normalize
from homate_ai.agent.interpretation import Interpretation


def expand_sets(interpretation, snapshot, text, history, contextual=False):
    expanded, mapping = [], {}
    for index, original in enumerate(interpretation.intents):
        if any(dep < 0 or dep >= index for dep in original.depends_on):
            raise ValueError('Quan hệ phụ thuộc phải trỏ tới yêu cầu trước đó.')
        batch = [t for t in original.targets if t.scope == 'all' or t.exclusions]
        if not batch:
            copies = [original.model_copy(deep=True)]
        else:
            if original.capability != 'control_device' or len(batch) != 1 or batch[0].entity != 'device':
                raise ValueError('Chưa hỗ trợ tập hợp cho yêu cầu này; hãy chỉ rõ từng đối tượng.')
            target = batch[0]
            if not contextual and not has_evidence(target.source, target.quote, text, history):
                raise ValueError('Phạm vi tập hợp chưa có bằng chứng từ lời người dùng.')
            if target.reference:
                raise ValueError('Cần xác định phạm vi của tham chiếu trước khi chọn nhiều thiết bị.')
            devices = list(snapshot['devices'])
            if target.room:
                room_ids = {r['id'] for r in snapshot['rooms'] if normalize(target.room) in {normalize(r['id']), normalize(r['name'])}}
                devices = [d for d in devices if d['room'] in room_ids]
            if target.kind:
                devices = [d for d in devices if d['kind'] == target.kind]
            if target.name:
                devices = [d for d in devices if normalize(target.name) in {normalize(d['id']), normalize(d['name'])}]
            for exclusion in target.exclusions:
                room_ids = {r['id'] for r in snapshot['rooms'] if normalize(exclusion) in {normalize(r['id']), normalize(r['name'])}}
                excluded = [d for d in devices if d['room'] in room_ids or normalize(exclusion) in {normalize(d['id']), normalize(d['name'])}]
                if not excluded:
                    raise ValueError('Không xác định được đối tượng cần loại trừ: ' + exclusion)
                excluded_ids = {d['id'] for d in excluded}
                devices = [d for d in devices if d['id'] not in excluded_ids]
            if not devices:
                raise ValueError('Không còn thiết bị phù hợp sau khi áp dụng phạm vi và ngoại lệ.')
            copies = []
            for device in devices:
                item = original.model_copy(deep=True)
                item.targets = [t.model_copy(update={'scope': 'single', 'exclusions': [], 'name': device['id'],
                    'room': None, 'kind': None}) if t.path == target.path else t for t in item.targets]
                item.arguments.pop('device_id', None)
                copies.append(item)
        mapping[index] = list(range(len(expanded), len(expanded) + len(copies)))
        for item in copies:
            item.depends_on = [step for dep in original.depends_on for step in mapping[dep]]
            expanded.append(item)
        if len(expanded) > 48:
            raise ValueError('Kế hoạch quá dài; tối đa 48 thao tác mỗi lần.')
    # Public interpretation schema caps user intents at 12; expanded plan may be larger.
    result = interpretation.model_copy(deep=True)
    result.intents = expanded
    return result


def compile_plan(interpretation, reviews):
    steps, mapping = [], {}
    for index, (intent, review) in enumerate(zip(interpretation.intents, reviews)):
        capability = CAPABILITIES.get(review.capability)
        if review.status != 'ready_for_review':
            raise ValueError('Chưa giải quyết đầy đủ yêu cầu; không tạo kế hoạch một phần.')
        if capability and capability.name != 'search_knowledge':
            dependencies = [mapping[dep] for dep in intent.depends_on if dep in mapping]
            mapping[index] = len(steps)
            expected = {}
            for path, source in review.provenance.items():
                if path.startswith('parameters.') and isinstance(source, dict) and 'previous' in source:
                    expected.setdefault(review.arguments['device_id'], {})[path.split('.')[1]] = source['previous']
            steps.append({'tool': capability.name, 'arguments': deepcopy(review.arguments),
                          'depends_on': dependencies, 'expected_state': expected})
    return steps
