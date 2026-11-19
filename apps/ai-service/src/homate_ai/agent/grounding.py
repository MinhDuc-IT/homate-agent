"""Resolve named entities against authenticated backend data; never guess an ID."""
from copy import deepcopy
import re
import unicodedata
from homate_ai.agent.interpretation import Issue


def normalize(text):
    text = unicodedata.normalize('NFD', text.casefold().replace('đ', 'd'))
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())


def has_evidence(source, quote, text, history):
    if source == 'assumption' or not quote.strip():
        return False
    corpus = [text] if source == 'utterance' else [m['content'] for m in history if m['role'] == 'user']
    return any(normalize(quote) in normalize(item) for item in corpus)


def set_path(data, path, value, text, history):
    parts = path.split('.')
    current = data
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    if not isinstance(current, dict):
        raise ValueError('Target path must name an object field')
    existing = current.get(parts[-1])
    if existing is not None and existing != value:
        # Model-produced IDs are not authoritative. Preserve a conflicting ID
        # only if the user actually supplied that literal ID; otherwise the
        # uniquely matched backend entity is the source of truth.
        literal_id = isinstance(existing, str) and (
            has_evidence('utterance', existing, text, history)
            or has_evidence('history', existing, text, history))
        if literal_id:
            raise ValueError('Explicit identifier conflicts with the named target')
    current[parts[-1]] = value
    return existing


def ground(intent, snapshot, schedules, text, history, contextual=False):
    arguments, provenance, issues = deepcopy(intent.arguments), {}, []
    rooms = snapshot['rooms']
    collections = {'device': snapshot['devices'], 'room': rooms,
                   'scene': snapshot['scenes'], 'schedule': schedules}
    used_paths = set()
    for target in intent.targets:
        def issue(code, message, candidates=None):
            issues.append(Issue(code=code, path=target.path, message=message, candidates=candidates or []))
        if target.path in used_paths:
            issue('conflicting_target', 'Có nhiều mô tả cho cùng một tham số; cần xác định lại đối tượng.')
            continue
        used_paths.add(target.path)
        valid_path = re.fullmatch(r'(?:changes\.)?(?:device_id|room_id|scene_id|schedule_id|steps\.(?:0|[1-9]\d*)\.device_id)', target.path)
        if not valid_path or target.path.split('.')[-1] != target.entity + '_id':
            issue('invalid_target_path', 'Đường dẫn đối tượng không khớp loại tham số.')
            continue
        if not contextual and not has_evidence(target.source, target.quote, text, history):
            issue('unverified_target', 'Mô tả đối tượng chưa có bằng chứng trong lời người dùng.')
            continue
        if target.scope == 'all' or target.exclusions:
            issue('plan_required', 'Yêu cầu tập hợp/ngoại lệ cần bước lập kế hoạch; chưa tạo từng thao tác riêng.')
            continue
        if target.reference and not ((target.source == 'history' and target.name) or contextual and (target.name or target.room or target.kind)):
            issue('unresolved_reference', f'Bạn muốn nói đến đối tượng nào: {target.reference}?')
            continue
        if not any((target.name, target.room, target.kind)):
            issue('missing_target', 'Bạn muốn thao tác với đối tượng nào?')
            continue
        candidates = list(collections[target.entity])
        if target.room:
            room_ids = {room['id'] for room in rooms
                        if normalize(target.room) in {normalize(room['id']), normalize(room['name'])}}
            if target.entity != 'device':
                issue('invalid_target_filter', 'Lọc theo phòng hiện chỉ dùng cho thiết bị.')
                continue
            candidates = [item for item in candidates if item['room'] in room_ids]
        if target.kind:
            candidates = [item for item in candidates if item.get('kind') == target.kind]
        if target.name:
            candidates = [item for item in candidates if normalize(target.name) in {
                normalize(item['id']), normalize(item['name']), normalize(item.get('voice_keyword', ''))}]
        public = [{key: item[key] for key in ('id', 'name', 'room', 'kind') if key in item}
                  for item in candidates]
        if len(candidates) != 1:
            issue('ambiguous_target' if candidates else 'target_not_found',
                  'Có nhiều đối tượng phù hợp; bạn muốn chọn đối tượng nào?' if candidates
                  else 'Không tìm thấy đối tượng phù hợp trong nhà.', public)
            continue
        try:
            previous = set_path(arguments, target.path, candidates[0]['id'], text, history)
        except (KeyError, IndexError, ValueError, TypeError):
            issue('conflicting_target', 'Không thể gắn đối tượng vào tham số; cần kiểm tra lại yêu cầu.')
            continue
        provenance[target.path] = {'source': 'backend', 'quote': target.quote,
                                   'selector_source': target.source, 'value': candidates[0]['id']}
        if previous is not None and previous != candidates[0]['id']:
            provenance[target.path]['discarded_model_value'] = previous
    for adjustment in intent.adjustments:
        device = next((d for d in snapshot['devices'] if d['id'] == arguments.get('device_id')), None)
        key = adjustment.path.removeprefix('parameters.')
        if intent.capability != 'control_device' or adjustment.path != 'parameters.' + key or arguments.get('action') != 'set_' + key or not device:
            issues.append(Issue(code='unresolved_meaning', path=adjustment.path, message='Cần xác định thiết bị và hành động trước khi tính thay đổi tương đối.'))
            continue
        previous = device['state'].get(key)
        if type(previous) not in (int, float) or not contextual and not has_evidence(adjustment.source, adjustment.quote, text, history):
            issues.append(Issue(code='unverified_parameter', path=adjustment.path, message='Chưa có trạng thái hiện tại hoặc số thay đổi rõ ràng.'))
            continue
        value = previous + (adjustment.amount if adjustment.operation == 'increase' else -adjustment.amount)
        parameters = arguments.setdefault('parameters', {})
        if not isinstance(parameters, dict):
            issues.append(Issue(code='invalid_value', path='parameters', message='Tham số điều khiển phải là object.'))
            continue
        parameters[key] = value
        provenance[adjustment.path] = {'source': 'backend', 'previous': previous, 'delta': adjustment.amount,
            'operation': adjustment.operation, 'quote': adjustment.quote, 'value': value}
    return arguments, provenance, issues
