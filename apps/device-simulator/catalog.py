"""Device profiles for the standalone simulator; no backend/DB dependencies."""
import json
import math
from pathlib import Path


class Catalog:
    def __init__(self):
        root = Path(__file__).parent
        self.devices = json.loads((root / 'devices.json').read_text(encoding='utf-8'))
        self.profiles = json.loads((root / 'profiles.json').read_text(encoding='utf-8'))

    def select(self, selection):
        identifiers = list(self.devices) if selection.strip() == 'all' else [value.strip() for value in selection.split(',') if value.strip()]
        if not identifiers or len(identifiers) != len(set(identifiers)) or any(identifier not in self.devices for identifier in identifiers):
            raise ValueError('Select all or unique device IDs from devices.json')
        return identifiers

    def fields(self, identifier):
        return self.profiles[self.devices[identifier]['profile']]['fields']

    def validate(self, identifier, state):
        fields = self.fields(identifier)
        if not isinstance(state, dict) or state.keys() != fields.keys():
            raise ValueError('invalid_state_keys')
        for key, value in state.items():
            field = fields[key]
            kind = field['type']
            if kind == 'boolean' and type(value) is not bool:
                raise ValueError('invalid_boolean')
            if kind == 'string' and type(value) is not str:
                raise ValueError('invalid_string')
            if kind in {'number', 'integer'}:
                if type(value) not in (int, float) or not math.isfinite(value) or kind == 'integer' and type(value) is not int:
                    raise ValueError('invalid_number')
                if not field.get('min', -math.inf) <= value <= field.get('max', math.inf):
                    raise ValueError('out_of_range')
            if 'enum' in field and value not in field['enum']:
                raise ValueError('invalid_option')
            if 'const' in field and value != field['const']:
                raise ValueError('read_only_field')
        if {'preset', 'position'} <= state.keys():
            expected = 'closed' if state['position'] == 0 else 'open' if state['position'] == 100 else 'ajar'
            if state['preset'] != expected:
                raise ValueError('inconsistent_position')
        return dict(state)

    def patch(self, identifier, previous, patch):
        if not isinstance(patch, dict) or not patch or not patch.keys() <= previous.keys():
            raise ValueError('invalid_patch')
        state = {**previous, **patch}
        if {'preset', 'position'} <= state.keys():
            if 'position' in patch and type(state['position']) in (int, float):
                state['preset'] = 'closed' if state['position'] == 0 else 'open' if state['position'] == 100 else 'ajar'
            elif 'preset' in patch:
                if state['preset'] == 'closed': state['position'] = 0
                elif state['preset'] == 'open': state['position'] = 100
                elif state['preset'] == 'ajar' and not 0 < state['position'] < 100: state['position'] = 50
        return self.validate(identifier, state)
