"""Export standalone MQTT profiles from the canonical device catalog.

Run with the backend installed, e.g. .venv/Scripts/python.exe tools/export_simulator_catalog.py.
Does not read the database, credentials or runtime device states.
"""
import json
from pathlib import Path

from homate.modules.home.domain.defaults import default_devices


def export():
    profiles, devices = {}, {}
    for device in default_devices():
        controls = {control.key: control.model_dump() for control in device.controls}
        fields = {}
        for key, value in device.state.items():
            control = controls.get(key)
            if control:
                kind = control['type']
                field = {'type': {'toggle': 'boolean', 'enum': 'string', 'level': 'integer'}.get(kind, 'number')}
                if kind in {'range', 'step'}: field.update(min=control['min'], max=control['max'])
                if kind == 'enum': field['enum'] = [option['value'] for option in control['options']]
                if kind == 'level': field['enum'] = control['levels']
            elif key == 'locked' and {'lock', 'unlock'} & controls.keys():
                field = {'type': 'boolean'}
            else:
                field = {'type': 'string' if isinstance(value, str) else 'boolean' if isinstance(value, bool) else 'number', 'const': value}
            fields[key] = field
        profile = {'kind': device.kind, 'fields': fields}
        name = next((name for name, old in profiles.items() if old == profile), None)
        if name is None:
            name = device.kind
            suffix = 2
            while name in profiles:
                name = f'{device.kind}_{suffix}'
                suffix += 1
            profiles[name] = profile
        state = dict(device.state)
        for key in ('power', 'recording'):
            if key in state: state[key] = False
        if 'speed' in state: state['speed'] = 0
        if 'locked' in state: state['locked'] = True
        if 'position' in state: state.update(position=0, preset='closed')
        devices[device.id] = {'profile': name, 'state': state}
    return profiles, devices


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1] / 'apps/device-simulator'
    profiles, devices = export()
    for name, content in [('profiles.json', profiles), ('devices.json', devices)]:
        (root / name).write_text(json.dumps(content, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Exported {len(devices)} devices and {len(profiles)} profiles')
