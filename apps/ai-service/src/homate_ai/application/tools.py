"""Provider-neutral JSON schemas; backend remains the validation authority."""


def tool(name, description, properties, required):
    return {'type': 'function', 'function': {'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}}}


TOOLS = [
    tool('search_knowledge', 'Tìm hướng dẫn sử dụng, thông số, bảo trì trong tài liệu của nhà. Không dùng cho trạng thái hiện tại. Có thể lọc theo device_id lấy từ snapshot. Trả đoạn nguồn để trích dẫn.', {
        'query': {'type':'string','minLength':1,'maxLength':2000},
        'device_id': {'type':['string','null']}}, ['query']),
    tool('get_home_snapshot', 'Đọc phòng, thiết bị, controls và kịch bản hiện tại. Luôn dùng để tìm ID chính xác trước khi điều khiển.', {}, []),
    tool('get_energy_report', 'Đọc điện năng theo kỳ, phòng, thiết bị và ngày tham chiếu. Lấy ID từ snapshot, không đoán ID.', {
        'period': {'type':'string','enum':['today','7days','30days','3months','week','month','year']},
        'room_id': {'type':['string','null']}, 'device_id': {'type':['string','null']},
        'anchor': {'type':['string','null'],'description':'Ngày tham chiếu YYYY-MM-DD; bỏ trống để dùng hôm nay.'}}, []),
    tool('control_device', 'Đề xuất điều khiển một thiết bị; backend trả yêu cầu xác nhận, chưa thực thi.', {
        'device_id': {'type':'string'}, 'action': {'type':'string', 'description':'turn_on, turn_off, unlock, lock, open, close, set_brightness, set_temperature, set_speed...'},
        'parameters': {'type':'object', 'description':'Giá trị theo tên control, ví dụ brightness: 60.'}}, ['device_id','action','parameters']),
    tool('execute_scene', 'Đề xuất chạy kịch bản có sẵn, cần xác nhận.', {'scene_id': {'type':'string'}}, ['scene_id']),
    tool('create_schedule', 'Đề xuất tạo lịch, chỉ admin được phép; cần xác nhận.', {
        'name': {'type':'string'}, 'schedule_type': {'type':'string','enum':['once','recurring']},
        'target_type': {'type':'string','enum':['device_action','scene']}, 'device_id': {'type':['string','null']},
        'action': {'type':['string','null']}, 'parameters': {'type':'object'}, 'scene_id': {'type':['string','null']},
        'timezone': {'type':'string'}, 'run_at': {'type':['string','null'], 'description':'ISO datetime có timezone, lịch một lần'},
        'recurrence_rule': {'type':['object','null'], 'properties': {'frequency': {'type':'string','enum':['daily','weekly']}, 'time': {'type':'string'}, 'days_of_week': {'type':'array','items': {'type':'integer','minimum':0,'maximum':6}}}},
        'enabled': {'type':'boolean'}}, ['name','schedule_type','target_type','timezone']),
]

SCENE_PROPERTIES = {
    'name': {'type':'string','minLength':1,'maxLength':80},
    'voice_keyword': {'type':'string','minLength':1,'maxLength':80},
    'is_enabled': {'type':'boolean'},
    'steps': {'type':'array','items':{'type':'object','additionalProperties':False,'properties':{
        'device_id':{'type':'string'},'action':{'type':'string'},'parameters':{'type':'object'}},
        'required':['device_id','action','parameters']}},
}
SCHEDULE_PROPERTIES = next(t['function']['parameters']['properties'] for t in TOOLS if t['function']['name'] == 'create_schedule')

TOOLS += [
    tool('list_scenes','Liệt kê kịch bản hiện có, kể cả kịch bản đang tắt.',{},[]),
    tool('get_scene','Đọc chi tiết kịch bản và các bước.',{'scene_id':{'type':'string'}},['scene_id']),
    tool('create_scene','Đề xuất tạo kịch bản. Chỉ admin, cần xác nhận.',SCENE_PROPERTIES,['name','voice_keyword','steps']),
    tool('update_scene','Đề xuất sửa kịch bản; changes chỉ chứa trường muốn thay đổi. steps thay toàn bộ danh sách. Đọc kịch bản trước khi sửa.',{
        'scene_id':{'type':'string'},'changes':{'type':'object','additionalProperties':False,'minProperties':1,'properties':SCENE_PROPERTIES}},['scene_id','changes']),
    tool('delete_scene','Đề xuất xóa kịch bản, cần xác nhận. Kịch bản được lịch tham chiếu có thể không xóa được.',{'scene_id':{'type':'string'}},['scene_id']),
    tool('set_scene_enabled','Đề xuất bật/tắt kịch bản, cần xác nhận.',{'scene_id':{'type':'string'},'enabled':{'type':'boolean'}},['scene_id','enabled']),
    tool('list_schedules','Liệt kê lịch; lọc phòng/kịch bản, include_finished=true để gồm lịch hoàn tất.',{
        'room_id':{'type':['string','null']},'scene_id':{'type':['string','null']},'include_finished':{'type':'boolean'}},[]),
    tool('get_schedule','Đọc chi tiết một lịch.',{'schedule_id':{'type':'string'}},['schedule_id']),
    tool('update_schedule','Đề xuất sửa lịch; đọc lịch trước, changes chỉ chứa trường muốn thay đổi.',{
        'schedule_id':{'type':'string'},'changes':{'type':'object','additionalProperties':False,'minProperties':1,'properties':SCHEDULE_PROPERTIES}},['schedule_id','changes']),
    tool('delete_schedule','Đề xuất xóa lịch, cần xác nhận.',{'schedule_id':{'type':'string'}},['schedule_id']),
    tool('set_schedule_enabled','Đề xuất bật/tắt lịch, cần xác nhận.',{'schedule_id':{'type':'string'},'enabled':{'type':'boolean'}},['schedule_id','enabled']),
    tool('get_schedule_runs','Đọc lịch sử chạy của một lịch.',{'schedule_id':{'type':'string'}},['schedule_id']),
]
