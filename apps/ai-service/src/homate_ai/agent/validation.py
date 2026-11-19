"""Deterministic preflight checks. Backend remains the execution authority."""
from copy import deepcopy
from datetime import date, datetime
import math
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from jsonschema import Draft202012Validator
from homate_ai.agent.capabilities import CAPABILITIES
from homate_ai.agent.grounding import has_evidence
from homate_ai.agent.interpretation import IntentReview, Issue


def leaves(value, prefix=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from leaves(item, f'{prefix}.{key}' if prefix else key)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from leaves(item, f'{prefix}.{index}')
    elif value is not None:
        yield prefix, value


def validate_device(command, devices, add, prefix=''):
    device = next((d for d in devices if d['id'] == command.get('device_id')), None)
    action, parameters = command.get('action'), command.get('parameters', {})
    if not device or not isinstance(action, str) or not isinstance(parameters, dict):
        return
    controls = {c['key']: c for c in device['controls']}
    writes = []
    if action in {'turn_on', 'turn_off'}:
        if controls.get('power', {}).get('type') == 'toggle':
            writes = [('power', action == 'turn_on')]
        else:
            level = next((c for c in controls.values() if c['type'] == 'level'
                          and 0 in c['levels'] and any(v > 0 for v in c['levels'])), None)
            if level:
                writes = [(level['key'], 0 if action == 'turn_off' else min(v for v in level['levels'] if v > 0))]
    elif action in {'open', 'close'}:
        if 'preset' in controls:
            writes.append(('preset', 'open' if action == 'open' else 'closed'))
        if 'position' in controls:
            writes.append(('position', 100 if action == 'open' else 0))
    elif action in {'start_recording', 'stop_recording'} and 'recording' in controls:
        writes = [('recording', action == 'start_recording')]
    elif action.startswith('set_') and action[4:] in controls:
        key = action[4:]
        if key not in parameters:
            add('missing_parameter', prefix + 'parameters.' + key, f'Bạn muốn đặt giá trị {key} là bao nhiêu?')
            return
        if key in {'brightness', 'temperature', 'volume'} and 'power' in controls:
            writes.append(('power', True))
        writes.append((key, parameters[key]))
    elif action in controls:
        writes = [(action, True)]
    if not writes:
        add('unsupported_action', prefix + 'action', f'{device["name"]} không hỗ trợ hành động {action}.')
        return
    allowed = {action[4:]} if action.startswith('set_') else set()
    if set(parameters) - allowed:
        add('invalid_value', prefix + 'parameters', 'Có tham số không được hành động này sử dụng.')
    state = deepcopy(device.get('state', {}))
    for key, value in writes:
        control = controls[key]
        if any(state.get(k) != v for k, v in (control.get('when') or {}).items()):
            add('precondition_failed', prefix + 'action', f'Điều kiện của control {key} chưa thỏa mãn.')
        kind = control['type']
        valid = True
        if kind in {'range', 'step', 'level'}:
            valid = type(value) in (int, float) and math.isfinite(value)
            if valid:
                valid = value in control['levels'] if kind == 'level' else control['min'] <= value <= control['max']
        elif kind == 'enum':
            valid = value in [option['value'] for option in control['options']]
        elif kind == 'toggle':
            valid = type(value) is bool
        if not valid:
            add('invalid_value', prefix + 'parameters.' + key, f'Giá trị {key} không thuộc phạm vi/giá trị control hỗ trợ.')
        state[key] = value
    return writes


def validate_schedule(data, devices, add, prefix=''):
    try:
        ZoneInfo(data.get('timezone', ''))
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        add('invalid_value', prefix + 'timezone', 'Múi giờ không hợp lệ.')
    target = data.get('target_type')
    if target == 'device_action':
        for field in ('device_id', 'action'):
            if not data.get(field):
                add('missing_parameter', prefix + field, f'Cần xác định {field} cho lịch thiết bị.')
        validate_device(data, devices, add, prefix)
    elif target == 'scene' and not data.get('scene_id'):
        add('missing_parameter', prefix + 'scene_id', 'Bạn muốn chạy kịch bản nào?')
    if data.get('schedule_type') == 'once':
        try:
            run_at = datetime.fromisoformat(data.get('run_at') or '')
            if run_at.utcoffset() is None or run_at <= datetime.now(run_at.tzinfo):
                raise ValueError('Schedule must be in the future with timezone')
        except (ValueError, TypeError):
            add('missing_parameter' if not data.get('run_at') else 'invalid_value', prefix + 'run_at',
                'Lịch một lần cần thời điểm tương lai đầy đủ ngày giờ và múi giờ.')
    elif data.get('schedule_type') == 'recurring':
        rule = data.get('recurrence_rule') or {}
        if not isinstance(rule, dict):
            return
        if rule.get('frequency') not in {'daily', 'weekly'} or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', str(rule.get('time', ''))):
            add('missing_parameter', prefix + 'recurrence_rule', 'Cần lịch lặp hằng ngày/hằng tuần và giờ HH:MM hợp lệ.')
        if rule.get('frequency') == 'weekly' and not rule.get('days_of_week'):
            add('missing_parameter', prefix + 'recurrence_rule.days_of_week', 'Bạn muốn lặp vào những ngày nào?')


def review_intent(intent, arguments, provenance, issues, snapshot, schedules, user, text, history, current=None, allow_plan=False):
    issues = list(issues)
    arguments, provenance = deepcopy(arguments), deepcopy(provenance)

    def add(code, path, message):
        if not any(i.code == code and i.path == path for i in issues):
            issues.append(Issue(code=code, path=path, message=message))

    capability = CAPABILITIES.get(intent.capability)
    if not capability:
        if intent.capability is None and (intent.missing or intent.unresolved or intent.indirect):
            add('unresolved_meaning', 'capability', 'Cần làm rõ mong muốn trước khi chọn chức năng phù hợp.')
        else:
            add('unsupported_capability', 'capability', 'Yêu cầu này chưa có tool phù hợp trong hệ thống.')
    else:
        if capability.role == 'admin' and user['role'] != 'admin':
            add('permission_denied', 'capability', 'Chỉ quản trị viên được quản lý kịch bản và lịch.')
        if intent.capability == 'create_schedule' and 'timezone' not in arguments:
            arguments['timezone'] = 'Asia/Ho_Chi_Minh'
            provenance['timezone'] = {'source': 'system_default', 'value': arguments['timezone']}
        # An empty parameters object does not supply any missing set_* value.
        if intent.capability == 'control_device' and 'parameters' not in arguments:
            arguments['parameters'] = {}
        for error in Draft202012Validator(capability.schema).iter_errors(arguments):
            path = '.'.join(str(part) for part in error.absolute_path)
            add('missing_parameter' if error.validator == 'required' else 'invalid_value', path,
                'Tham số chưa đầy đủ hoặc không đúng hợp đồng tool: ' + error.message[:300])
        known = {'device_id': {d['id'] for d in snapshot['devices']},
                 'room_id': {r['id'] for r in snapshot['rooms']},
                 'scene_id': {s['id'] for s in snapshot['scenes']},
                 'schedule_id': {s['id'] for s in schedules}}
        for path, value in leaves(arguments):
            key = path.split('.')[-1]
            if key in known and value not in known[key]:
                add('target_not_found', path, 'Không tìm thấy mã đối tượng trong dữ liệu nhà hiện tại.')
        # Provenance must come from user text or grounded selectors, never model confidence.
        evidence = {e.path: e for e in intent.evidence}
        for path, value in leaves(arguments):
            if path in provenance:
                continue
            item = evidence.get(path)
            if item and has_evidence(item.source, item.quote, text, history):
                provenance[path] = {'source': item.source, 'quote': item.quote, 'value': value}
            elif capability.effect == 'write' and not allow_plan:
                add('unverified_parameter', path, 'Tham số chưa có bằng chứng rõ từ lời người dùng: ' + path)
        if intent.capability == 'control_device':
            validate_device(arguments, snapshot['devices'], add)
        if intent.capability in {'create_scene', 'update_scene'}:
            data = arguments if intent.capability == 'create_scene' else arguments.get('changes', {})
            if isinstance(data, dict) and isinstance(data.get('steps'), list):
                for index, step in enumerate(data['steps']):
                    if isinstance(step, dict):
                        prefix = ('changes.' if intent.capability == 'update_scene' else '') + f'steps.{index}.'
                        validate_device(step, snapshot['devices'], add, prefix)
        if intent.capability in {'create_schedule', 'update_schedule'}:
            changes = arguments.get('changes', {})
            if intent.capability == 'create_schedule':
                validate_schedule(arguments, snapshot['devices'], add)
            elif current is not None and isinstance(changes, dict):
                validate_schedule({**current, **changes}, snapshot['devices'], add, 'changes.')
            elif current is None:
                add('backend_data_required', 'schedule_id', 'Cần đọc lịch hiện tại trước khi kiểm tra thay đổi.')
        if intent.capability == 'execute_scene':
            scene = next((s for s in snapshot['scenes'] if s['id'] == arguments.get('scene_id')), None)
            if scene and not scene.get('is_enabled', True):
                add('precondition_failed', 'scene_id', 'Kịch bản đang tắt; cần làm rõ trước khi chạy.')
        if intent.capability == 'get_energy_report':
            if arguments.get('anchor'):
                try:
                    date.fromisoformat(arguments['anchor'])
                except (ValueError, TypeError):
                    add('invalid_value', 'anchor', 'Ngày tham chiếu phải có dạng YYYY-MM-DD.')
            if arguments.get('room_id') and arguments.get('device_id'):
                device = next((d for d in snapshot['devices'] if d['id'] == arguments['device_id']), None)
                if device and device['room'] != arguments['room_id']:
                    add('conflicting_target', 'device_id', 'Thiết bị không thuộc phòng đã chọn.')
    if intent.indirect:
        add('indirect_request', 'goal', 'Bạn muốn tôi thực hiện thao tác cụ thể nào?')
    for field in intent.missing:
        add('missing_parameter', field, 'Cần bổ sung thông tin: ' + field)
    for question in intent.unresolved:
        add('unresolved_meaning', 'goal', question)
    if intent.conditions:
        add('unsupported_condition', 'conditions', 'Chưa hỗ trợ tự động hóa theo điều kiện cảm biến; không chuyển thành lệnh tức thời.')
    if intent.depends_on and not allow_plan:
        add('plan_required', 'depends_on', 'Cần lập kế hoạch và quản lý phụ thuộc trước khi thực hiện chuỗi này.')
    codes = {issue.code for issue in issues}
    if 'permission_denied' in codes:
        status = 'forbidden'
    elif codes & {'unsupported_capability', 'unsupported_action', 'unsupported_condition'}:
        status = 'unsupported'
    elif codes & {'plan_required', 'backend_data_required'}:
        status = 'needs_data'
    elif issues:
        status = 'needs_clarification'
    else:
        status = 'ready_for_review'
    return IntentReview(goal=intent.goal, capability=intent.capability, status=status,
                        arguments=arguments, provenance=provenance, issues=issues,
                        requires_confirmation=bool(capability and capability.effect == 'write'))
