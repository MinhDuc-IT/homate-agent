"""Validated agent tool use cases, independent of HTTP and persistence adapters."""
from pydantic import BaseModel, ConfigDict, Field
from homate.modules.home.domain.actions import action_writes
from homate.modules.home.application.devices import DeviceStore


class DeviceCommand(BaseModel):
    model_config = ConfigDict(extra='forbid')
    device_id: str
    action: str
    parameters: dict = Field(default_factory=dict)


ACTION_LABELS = {'turn_on':'Bật', 'turn_off':'Tắt', 'unlock':'Mở khóa', 'lock':'Khóa',
    'open':'Mở', 'close':'Đóng', 'set_brightness':'Đặt độ sáng', 'set_temperature':'Đặt nhiệt độ',
    'set_speed':'Đặt tốc độ', 'start_recording':'Bắt đầu ghi hình', 'stop_recording':'Dừng ghi hình'}


def schedule_review(household, store, home_id, data):
    target = household.get_scene(home_id,data['scene_id'])['name'] if data['target_type'] == 'scene' else store.get(data['device_id']).name
    rule = data.get('recurrence_rule') or {}
    timing = data['run_at'] if data['schedule_type'] == 'once' else f"{'Hằng ngày' if rule['frequency'] == 'daily' else 'Hằng tuần'} lúc {rule['time']}"
    if rule.get('frequency') == 'weekly':
        days = ['Thứ hai','Thứ ba','Thứ tư','Thứ năm','Thứ sáu','Thứ bảy','Chủ nhật']
        timing += ' — ' + ', '.join(days[day] for day in rule['days_of_week'])
    return [f"Đối tượng: {target}", f"Hành động: {ACTION_LABELS.get(data.get('action'), 'Chạy kịch bản')}",
        f"Tham số: {', '.join(str(value) for value in (data.get('parameters') or {}).values()) or 'Mặc định'}",
        f"Thời điểm: {timing}", f"Múi giờ: {data['timezone']}", f"Trạng thái: {'Bật' if data['enabled'] else 'Tắt'}"]


def prepare(household, store, schedules, user, tool, args):
    if tool in {'create_scene','update_scene','delete_scene','set_scene_enabled','update_schedule','delete_schedule','set_schedule_enabled'}:
        if user['role'] != 'admin': raise PermissionError('Chỉ quản trị viên được quản lý kịch bản và lịch')
        if 'scene' in tool:
            current = None if tool == 'create_scene' else household.get_scene(user['home_id'], args['scene_id'])
            data = dict(args.get('changes') or {}) if tool == 'update_scene' else dict(args) if tool == 'create_scene' else {}
            if tool == 'set_scene_enabled': data = {'is_enabled':args['enabled']}
            if current and tool != 'delete_scene':
                data = {**{key:current[key] for key in ('name','voice_keyword','is_enabled','steps')}, **data}
            if tool != 'delete_scene':
                data['steps'] = [{key:step[key] for key in ('device_id','action','parameters')} for step in data['steps']]
                household.validate_scene_steps(user['home_id'], data['steps'])
            label = {'create_scene':'Tạo kịch bản','update_scene':'Sửa kịch bản','delete_scene':'Xóa kịch bản','set_scene_enabled':'Bật kịch bản' if args.get('enabled') else 'Tắt kịch bản'}[tool]
            name = data.get('name') or current['name']
            review = [f"Từ khóa: {data['voice_keyword']}"] if tool != 'delete_scene' else ['Kịch bản sẽ bị xóa sau khi xác nhận.']
            review += [f"{store.get(step['device_id']).name}: {ACTION_LABELS.get(step['action'],step['action'])}" +
                (f" ({', '.join(str(value) for value in step['parameters'].values())})" if step['parameters'] else '') for step in data.get('steps',[])]
        else:
            current = schedules.get(user['home_id'],args['schedule_id'])
            data = dict(args['changes']) if tool == 'update_schedule' else {'enabled':args['enabled']} if tool == 'set_schedule_enabled' else {}
            validated = schedules.validate(user['home_id'], {**current, **data}) if tool != 'delete_schedule' else None
            label = {'update_schedule':'Sửa lịch','delete_schedule':'Xóa lịch','set_schedule_enabled':'Bật lịch' if args.get('enabled') else 'Tắt lịch'}[tool]
            name = data.get('name') or current['name']
            review = schedule_review(household,store,user['home_id'],validated) if validated else ['Lịch sẽ bị xóa sau khi xác nhận.']
        return {'data':data,'expected':current,'review':review}, f'{label}: {name}'
    if tool == 'create_schedule':
        if user['role'] != 'admin': raise PermissionError('Chỉ quản trị viên được tạo lịch')
        data = schedules.validate(user['home_id'], dict(args))
        data['review'] = schedule_review(household,store,user['home_id'],data)
        return data, f"Tạo lịch: {data['name']}"
    if tool == 'execute_scene':
        if set(args) != {'scene_id'}: raise ValueError('Cần scene_id')
        scene = household.get_scene(user['home_id'], args['scene_id'])
        if not scene['is_enabled']: raise ValueError('Kịch bản đang tắt')
        commands = [DeviceCommand.model_validate(s).model_dump() for s in [
            {key: step[key] for key in ('device_id', 'action', 'parameters')} for step in scene['steps']]]
        summary = f"Chạy kịch bản: {scene['name']}"
    else:
        commands = [DeviceCommand.model_validate(args).model_dump()]
        scene = None
        summary = f"{store.get(commands[0]['device_id']).name}: {ACTION_LABELS.get(commands[0]['action'], commands[0]['action'])}"
    room_ids = {room['id'] for room in household.load_rooms_ambient(user['home_id'])}
    sandbox = DeviceStore(store.list())
    writes = []
    for command in commands:
        device = sandbox.get(command['device_id'])
        if device.room not in room_ids: raise PermissionError('Thiết bị không thuộc nhà của bạn')
        for key, value in action_writes(device, command['action'], command['parameters']):
            sandbox.apply_action(device.id, key, value)
            writes.append({'device_id': device.id, 'key': key, 'value': value})
    review = [f"{store.get(command['device_id']).name}: {ACTION_LABELS.get(command['action'], command['action'])}" +
              (f" ({', '.join(str(value) for value in command['parameters'].values())})" if command['parameters'] else '') for command in commands]
    return {'commands': commands, 'writes': writes, 'scene': scene, 'review': review}, summary


def execute(household, store, schedules, user, changed, tool, args):
    if tool in {'create_scene','update_scene','delete_scene','set_scene_enabled','update_schedule','delete_schedule','set_schedule_enabled'}:
        if user['role'] != 'admin': raise PermissionError('Bạn không còn quyền quản lý kịch bản và lịch')
        expected, data = args['expected'], args['data']
        if 'scene' in tool:
            if expected and household.get_scene(user['home_id'],expected['id']) != expected: raise ValueError('Kịch bản đã thay đổi; hãy gửi yêu cầu mới')
            if tool == 'create_scene': result = household.create_scene(user['home_id'],created_by=user['id'],**data)
            elif tool == 'delete_scene':
                household.delete_scene(user['home_id'],expected['id'])
                result = {'id':expected['id'],'deleted':True}
            else: result = household.update_scene(user['home_id'],expected['id'],**data)
        else:
            if schedules.get(user['home_id'],expected['id']) != expected: raise ValueError('Lịch đã thay đổi; hãy gửi yêu cầu mới')
            if tool == 'delete_schedule':
                schedules.delete(user['home_id'],expected['id'])
                result = {'id':expected['id'],'deleted':True}
            else: result = schedules.update(user['home_id'],expected['id'],data)
    elif tool == 'create_schedule':
        if user['role'] != 'admin': raise PermissionError('Bạn không còn quyền tạo lịch')
        result = schedules.create(user['home_id'], user['id'], {key:value for key,value in args.items() if key != 'review'})
    else:
        if args['scene']:
            current = household.get_scene(user['home_id'], args['scene']['id'])
            if current != args['scene']: raise ValueError('Kịch bản đã thay đổi; hãy gửi yêu cầu mới')
        # Revalidate every command before performing any device write.
        for command in args['commands']: prepare(household, store, schedules, user, 'control_device', command)
        for write in args['writes']:
            changed.append(store.apply_action(write['device_id'], write['key'], write['value']).device)
        result = {'device_ids': list(dict.fromkeys(d.id for d in changed))}
    household.append_command_log(user['home_id'], utterance=f'Agent: {tool}', intent=tool, result='success', user_id=user['id'])
    return result
