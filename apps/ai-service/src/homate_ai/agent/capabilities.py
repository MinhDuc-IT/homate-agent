"""The existing tool schemas plus policy and data acquisition metadata."""
from copy import deepcopy
from dataclasses import dataclass
from homate_ai.agent.tools import TOOLS


READ_TOOLS = frozenset({
    'get_home_snapshot', 'get_energy_report', 'list_scenes', 'get_scene',
    'list_schedules', 'get_schedule', 'get_schedule_runs', 'search_knowledge',
})
ADMIN_TOOLS = frozenset({
    'create_scene', 'update_scene', 'delete_scene', 'set_scene_enabled',
    'create_schedule', 'update_schedule', 'delete_schedule', 'set_schedule_enabled',
})
LIMITS = [
    'Chỉ hỗ trợ thiết bị, controls, kịch bản và lịch có trong dữ liệu backend.',
    'Lịch hỗ trợ một lần hoặc lặp hằng ngày/hằng tuần; chưa hỗ trợ trigger cảm biến.',
    'Có lịch sử hội thoại theo phiên; chưa có memory sở thích hoặc vị trí hiện tại của người dùng.',
    'Workflow chat hỗ trợ nhiều đối tượng và phụ thuộc theo thứ tự; endpoint analyze chỉ quan sát, không tạo kế hoạch.',
    'search_knowledge chỉ tra tài liệu; trạng thái hiện tại phải lấy từ backend.',
]


@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    schema: dict
    effect: str
    role: str
    reads: tuple[str, ...]

    def public(self):
        return {
            'name': self.name, 'description': self.description,
            'parameters': deepcopy(self.schema), 'effect': self.effect,
            'required_role': self.role, 'requires_confirmation': self.effect == 'write',
            'parameter_sources': ['utterance', 'history', 'backend', 'system_default'],
            'read_tools': list(self.reads),
            'preconditions': [
                'IDs phải thuộc dữ liệu nhà được backend trả về.',
                'Hành động và giá trị phải phù hợp controls của thiết bị.',
                'Các điều kiện when phải thỏa mãn theo thứ tự ghi của hành động.',
                'Backend kiểm tra lại quyền và dữ liệu tại thời điểm xác nhận.',
            ] if self.effect == 'write' else ['Dữ liệu được giới hạn theo quyền người dùng.'],
            'defaults': {'timezone': 'Asia/Ho_Chi_Minh'} if self.name == 'create_schedule' else {},
            'limitations': ['Chưa hỗ trợ sensor triggers hoặc điều kiện tùy ý.'] if 'schedule' in self.name else [],
        }


def _capability(function):
    name = function['name']
    reads = ['get_home_snapshot']
    if 'schedule' in name and name != 'create_schedule':
        reads.append('list_schedules')
    if name == 'update_scene':
        reads.append('get_scene')
    if name == 'update_schedule':
        reads.append('get_schedule')
    return Capability(name, function['description'], deepcopy(function['parameters']),
                      'read' if name in READ_TOOLS else 'write',
                      'admin' if name in ADMIN_TOOLS else 'member', tuple(reads))


CAPABILITIES = {item['function']['name']: _capability(item['function']) for item in TOOLS}


def catalog():
    return {'capabilities': [cap.public() for cap in CAPABILITIES.values()], 'limits': list(LIMITS)}
