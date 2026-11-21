"""Backend-owned confirmation policy; unknown effects require confirmation."""

SAFE_ACTIONS = {
    'bulb': {'turn_on', 'turn_off', 'set_brightness'},
    'fan': {'turn_on', 'turn_off', 'set_speed'},
    'snowflake': {'turn_on', 'turn_off', 'set_temperature', 'set_speed'},
    'curtain': {'open', 'close', 'set_position'},
    'tv': {'turn_on', 'turn_off', 'set_volume'},
    'speaker': {'turn_on', 'turn_off', 'set_volume'},
}


def confirmation_policy(steps, store):
    devices, commands = set(), []
    for step in steps:
        if step['tool'] not in {'control_device', 'execute_scene'}:
            return {'mode': 'require_confirmation', 'reason': 'management_or_unknown_operation'}
        commands.extend(step['prepared'].get('commands', []))
        commands.extend(step['prepared'].get('automatic_shutdowns', []))
    if not commands:
        return {'mode': 'require_confirmation', 'reason': 'unknown_effects'}
    for command in commands:
        device = store.get(command['device_id'])
        devices.add(device.id)
        if command['action'] not in SAFE_ACTIONS.get(device.kind, set()):
            return {'mode': 'require_confirmation', 'reason': 'sensitive_device_or_action'}
    if len(devices) > 3 or len(commands) > 5:
        return {'mode': 'require_confirmation', 'reason': 'large_scope'}
    return {'mode': 'auto_execute', 'reason': 'routine_actions'}
