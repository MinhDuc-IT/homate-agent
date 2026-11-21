"""Declared conflict rules evaluated against actual device state."""


class DeviceConflictError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__('; '.join(issue['message'] for issue in issues))


def active(device):
    if 'power' in device.state:
        value = device.state['power']
        return value if isinstance(value, bool) else None
    if device.kind == 'fan':
        value = device.state.get('speed')
        return value > 0 if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return None


def conflicts_for(device, devices, rules):
    if active(device) is False:
        return []
    issues, seen = [], set()
    ordered = sorted(((left, rule) for left, peers in rules.items() for rule in peers),
        key=lambda item: {'reject': 0, 'ask': 1, 'auto_off_other': 2}.get(item[1]['on_conflict'], 0))
    for left, rule in ordered:
        right = rule['device_id']
        if device.id not in (left, right):
            continue
        peer_id = right if device.id == left else left
        if peer_id in seen or peer_id not in devices:
            continue
        peer = devices[peer_id]
        if rule['scope'] == 'same_room' and device.room != peer.room:
            continue
        seen.add(peer_id)
        if active(peer) is False:
            continue
        unknown = active(device) is None or active(peer) is None
        mode = rule['on_conflict']
        message = (f'Chưa xác định được trạng thái của {device.name} hoặc {peer.name}.' if unknown else
            f'{device.name} và {peer.name} không được chạy cùng lúc. ' +
            ('Bạn muốn dùng thiết bị nào? Muốn chuyển thiết bị thì cần tắt thiết bị đang chạy trước.' if mode == 'ask' else
             'Cần tắt thiết bị đang chạy trước.'))
        issues.append({'code': 'device_conflict', 'device_id': device.id, 'conflicts_with': peer.id,
            'policy': mode, 'unknown_state': unknown, 'message': message})
    return issues


def off_control(device):
    keys = {c.key: c for c in device.controls}
    if 'power' in keys:
        return 'power', False
    if device.kind == 'fan' and 0 in getattr(keys.get('speed'), 'levels', []):
        return 'speed', 0
    raise ValueError(f'Không có thao tác tắt được hỗ trợ cho {device.name}')
