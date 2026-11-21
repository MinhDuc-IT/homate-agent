"""Conflict checks cover current state, ordered plans and late execution."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from homate.modules.home.application.devices import DeviceStore
from homate.modules.home.domain.defaults import default_devices
from homate.modules.home.domain.conflicts import DeviceConflictError


def store(policy='ask'):
    devices = default_devices()
    for device in devices:
        if device.id in {'ac-living', 'heater-living'}:
            device.state['power'] = False
    rules = {'ac-living': [{'device_id': 'heater-living', 'scope': 'same_room', 'on_conflict': policy}]}
    return DeviceStore(devices, conflict_rules=lambda: rules)


@pytest.mark.parametrize('policy', ['ask', 'reject'])
@pytest.mark.parametrize('first,second', [('ac-living', 'heater-living'), ('heater-living', 'ac-living')])
def test_declared_pair_is_symmetric_and_active_peer_blocks(policy, first, second):
    devices = store(policy)
    devices.apply_action(first, 'power', True)
    with pytest.raises(DeviceConflictError) as error:
        devices.apply_action(second, 'power', True)
    assert error.value.issues[0]['policy'] == policy
    assert devices.get(first).state['power'] is True
    assert devices.get(second).state['power'] is False


def test_off_then_on_is_allowed_and_fork_has_no_effect():
    devices = store()
    devices.apply_action('ac-living', 'power', True)
    sandbox = devices.fork()
    sandbox.apply_action('ac-living', 'power', False)
    sandbox.apply_action('heater-living', 'power', True)
    assert devices.get('ac-living').state['power'] is True
    assert devices.get('heater-living').state['power'] is False


def test_auto_off_other_persists_shutdown_before_activation():
    devices = store('auto_off_other')
    devices.apply_action('ac-living', 'power', True)
    writes = []
    devices.set_on_change(lambda d: writes.append((d.id, d.state['power'])))
    result = devices.apply_action('heater-living', 'power', True)
    assert writes == [('ac-living', False), ('heater-living', True)]
    assert [d.id for d in result.related_devices] == ['ac-living']


def test_failed_shutdown_never_activates_other():
    devices = store('auto_off_other')
    devices.apply_action('ac-living', 'power', True)
    def fail(device):
        raise RuntimeError('Persistence unavailable')
    devices.set_on_change(fail)
    with pytest.raises(RuntimeError):
        devices.apply_action('heater-living', 'power', True)
    assert devices.get('heater-living').state['power'] is False


def test_simultaneous_requests_cannot_both_activate():
    devices = store()
    def activate(identifier):
        try:
            devices.apply_action(identifier, 'power', True)
            return True
        except DeviceConflictError:
            return False
    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(activate, ['ac-living', 'heater-living'])) == 1


def test_unknown_peer_state_blocks_but_can_turn_off():
    devices = store()
    devices.set_state('ac-living', {'power': None})
    with pytest.raises(DeviceConflictError) as error:
        devices.apply_action('heater-living', 'power', True)
    assert error.value.issues[0]['unknown_state']
    devices.apply_action('heater-living', 'power', False)


def test_unconfigured_pair_is_not_invented():
    devices = DeviceStore(default_devices())
    devices.apply_action('ac-living', 'power', True)
    devices.apply_action('heater-living', 'power', True)


def test_same_room_scope_does_not_block_other_room_but_explicit_does():
    devices = default_devices()
    for device in devices:
        if device.id in {'ac-living', 'heater-living'}:
            device.state['power'] = False
        if device.id == 'heater-living':
            device.room = 'bed'
    rule = {'device_id': 'heater-living', 'scope': 'same_room', 'on_conflict': 'reject'}
    catalog = DeviceStore(devices, conflict_rules=lambda: {'ac-living': [rule]})
    catalog.apply_action('ac-living', 'power', True)
    catalog.apply_action('heater-living', 'power', True)
    catalog.apply_action('heater-living', 'power', False)
    rule['scope'] = 'explicit'
    with pytest.raises(DeviceConflictError):
        catalog.apply_action('heater-living', 'power', True)


def test_fan_uses_speed_when_no_power_control():
    devices = default_devices()
    rules = {'ac-bed': [{'device_id': 'fan-bed', 'scope': 'same_room', 'on_conflict': 'ask'}]}
    for device in devices:
        if device.id == 'ac-bed':
            device.state['power'] = False
    catalog = DeviceStore(devices, conflict_rules=lambda: rules)
    catalog.apply_action('fan-bed', 'speed', 1)
    with pytest.raises(DeviceConflictError):
        catalog.apply_action('ac-bed', 'power', True)
    catalog.apply_action('fan-bed', 'speed', 0)
    catalog.apply_action('ac-bed', 'power', True)
