import importlib.util
import sys
import json
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import paho.mqtt.client as mqtt
import pytest

from homate.infrastructure.mqtt import MqttTransport, validated_report
from homate.modules.home.application.devices import DeviceStore
from homate.modules.home.application.gateway import DeviceTransportError
from homate.modules.home.domain.defaults import default_devices

sys.path.insert(0, str(Path(__file__).parents[2] / 'device-simulator'))
spec = importlib.util.spec_from_file_location('mock_devices', Path(__file__).parents[2] / 'device-simulator/app.py')
mock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mock)


def make_transport():
    device = next(device for device in default_devices() if device.id == 'light-living')
    transport = MqttTransport('localhost', 1883, [device], timeout=0.02)
    transport.ready.set()
    return transport, device


def deliver(transport, identifier, payload, suffix='ack', retain=False):
    transport._message(None, None, SimpleNamespace(topic=f'homate/devices/{identifier}/{suffix}', payload=json.dumps(payload).encode(), retain=retain))


def test_broker_puback_is_not_a_device_ack():
    transport, desired = make_transport()
    transport.client.publish = lambda *args, **kwargs: SimpleNamespace(rc=mqtt.MQTT_ERR_SUCCESS)
    with pytest.raises(DeviceTransportError, match='mqtt_timeout'):
        transport.execute(desired, {'_command_id': str(uuid4())})
    assert not transport.pending


def test_availability_heartbeat_expiry_and_last_will(monkeypatch):
    transport, device = make_transport()
    now = time.time()
    monkeypatch.setattr('homate.infrastructure.mqtt.time.time', lambda: now)
    def announce(online, stamp=None):
        packet = {'device_ids': [device.id], 'online': online, 'sent_at': stamp}
        transport._message(None, None, SimpleNamespace(topic='homate/availability/test', payload=json.dumps(packet).encode(), retain=True))
    assert transport.connectivity(device.id)['status'] == 'unknown'
    announce(True, now - 60)  # Stale retained online cannot resurrect a device.
    assert transport.connectivity(device.id)['status'] == 'offline'
    announce(True, now)
    assert transport.connectivity(device.id)['status'] == 'online'
    now += 36
    assert transport.connectivity(device.id)['status'] == 'offline'
    with pytest.raises(DeviceTransportError, match='device_offline'):
        transport.execute(device, {'_command_id': str(uuid4())})
    announce(True, now)
    assert transport.connectivity(device.id)['status'] == 'online'
    announce(False)
    assert transport.connectivity(device.id) == {'status': 'offline', 'last_seen_at': now}
    announce(True, now)
    transport._disconnect(None, None, None, None, None)
    assert transport.connectivity(device.id)['status'] == 'offline'


def test_ack_requires_matching_command_device_and_nonretained_valid_state():
    transport, desired = make_transport()
    command_id = str(uuid4())
    payload = dict(device_id=desired.id, command_id=command_id, state=desired.state, revision=1, boot_id=str(uuid4()), status='succeeded')
    def publish(*args, **kwargs):
        item = transport.pending[command_id]
        deliver(transport, desired.id, {**payload, 'command_id': str(uuid4())})
        deliver(transport, desired.id, {**payload, 'device_id': 'light-bed'})
        deliver(transport, desired.id, payload, retain=True)
        deliver(transport, desired.id, {**payload, 'state': {**desired.state, 'power': 'true'}})
        assert not item.event.is_set()
        deliver(transport, desired.id, payload)
        return SimpleNamespace(rc=0)
    transport.client.publish = publish
    assert transport.execute(desired, {'_command_id': command_id}).state == desired.state


def test_old_reports_cannot_overwrite_new_command_ack_or_new_boot():
    transport, device = make_transport()
    boot, next_boot = str(uuid4()), str(uuid4())
    report = dict(device_id=device.id, boot_id=boot, revision=1, state=device.state)
    deliver(transport, device.id, report, 'state')
    newer = {**report, 'revision': 2, 'state': {**device.state, 'power': False}}
    deliver(transport, device.id, newer, 'state')
    store = DeviceStore([device])
    assert store.set_state(device.id, report['state'], accept_if=lambda: transport.is_current(report)) is None
    assert transport.is_current(newer)
    new_boot = {**newer, 'boot_id': next_boot, 'revision': 0}
    deliver(transport, device.id, new_boot, 'state')
    deliver(transport, device.id, {**newer, 'revision': 999}, 'state')
    assert transport.is_current(new_boot)


def test_simulator_deduplicates_persists_and_expires_commands(tmp_path):
    sent = []
    path = tmp_path / 'devices.json'
    devices = mock.Devices(path, ['light-living'], lambda *args: sent.append(args))
    packet = dict(device_id='light-living', command_id=str(uuid4()), desired_state={'power': True, 'brightness': 40}, expires_at=time.time()+10)
    devices.command('light-living', packet)
    assert devices.report('light-living')['revision'] == 1
    devices.command('light-living', packet)
    assert devices.report('light-living')['revision'] == 1
    reloaded = mock.Devices(path, ['light-living'], lambda *args: sent.append(args))
    reloaded.command('light-living', packet)
    assert reloaded.report('light-living')['revision'] == 1
    reloaded.command('light-living', {**packet, 'command_id': str(uuid4()), 'expires_at': time.time()-1, 'desired_state': {'power': False, 'brightness': 40}})
    assert reloaded.report('light-living')['state']['power'] is True
    assert sent[-1][1]['status'] == 'expired'
    assert all(retain is False for topic, payload, retain in sent if topic.endswith('/ack'))


def test_physical_switch_emits_state_without_backend_command(tmp_path):
    sent = []
    devices = mock.Devices(tmp_path / 'state.json', ['light-living'], lambda *args: sent.append(args))
    devices.physical('light-living', {'power': True})
    assert sent[-1][0] == 'homate/devices/light-living/state'
    assert sent[-1][2] is True
    assert not devices.data['receipts']
    with pytest.raises(ValueError):
        devices.physical('light-living', {'brightness': 200})


@pytest.mark.parametrize('device', default_devices(), ids=lambda device: device.id)
def test_every_catalog_device_accepts_backend_controls_and_reports(device, tmp_path):
    sent = []
    devices = mock.Devices(tmp_path / 'state.json', [device.id], lambda *args: sent.append(args))
    for control in device.controls:
        # Preconditions belong to the backend. Reports may include state whose
        # control is hidden while off, so validate the complete state each time.
        current = device.model_copy(deep=True)
        if control.when: current.state.update(control.when)
        store = DeviceStore([current])
        if control.type == 'action': value = True
        elif control.type == 'toggle': value = not current.state[control.key]
        elif control.type == 'enum': value = control.options[-1].value
        elif control.type == 'level': value = control.levels[-1]
        else: value = control.min + (control.max - control.min) / 2
        desired = store.apply_action(device.id, control.key, value).device
        packet = dict(device_id=device.id, command_id=str(uuid4()), desired_state=desired.state, expires_at=time.time() + 10)
        devices.command(device.id, packet)
        ack = sent[-1][1]
        assert ack['status'] == 'succeeded'
        assert ack['state'] == desired.state
        assert validated_report(device, ack)['state'] == desired.state
    restarted = mock.Devices(tmp_path / 'state.json', [device.id], lambda *args: None)
    assert restarted.report(device.id) == devices.report(device.id)


@pytest.mark.parametrize(('identifier', 'patch'), [
    ('door', {'locked': 1}), ('cam-bed', {'recording': 'true'}),
    ('fan-bath', {'speed': 3}), ('fan-bed', {'speed': True}),
    ('ac-living', {'mode': 'heat'}), ('ac-living', {'fan': 'turbo'}),
    ('ac-bed', {'fan': 'high'}), ('ac-bed', {'temperature': 100}),
    ('heater-bath', {'temperature': 24}), ('speaker-living', {'volume': float('nan')}),
    ('curtain', {'position': 100, 'preset': 'closed'}), ('tv-living', {'volume': 20}),
])
def test_invalid_states_are_rejected_without_changing_device(identifier, patch, tmp_path):
    sent = []
    devices = mock.Devices(tmp_path / 'state.json', [identifier], lambda *args: sent.append(args))
    original = json.loads(json.dumps(devices.report(identifier)))
    state = {**original['state'], **patch}
    packet = dict(device_id=identifier, command_id=str(uuid4()), desired_state=state, expires_at=time.time() + 10)
    devices.command(identifier, packet)
    assert sent[-1][1]['status'] == 'invalid_state'
    assert devices.report(identifier) == original
    template = next(device for device in default_devices() if device.id == identifier)
    with pytest.raises(ValueError):
        validated_report(template, {**original, 'state': state})


def test_curtain_physical_controls_normalize_position_and_preset(tmp_path):
    devices = mock.Devices(tmp_path / 'state.json', ['curtain'], lambda *args: None)
    assert devices.physical('curtain', {'preset': 'open'})['state'] == {'preset': 'open', 'position': 100}
    assert devices.physical('curtain', {'position': 31})['state'] == {'preset': 'ajar', 'position': 31}
    assert devices.physical('curtain', {'preset': 'closed'})['state'] == {'preset': 'closed', 'position': 0}


def test_simulator_catalog_covers_backend_and_selection_is_explicit():
    catalog = mock.Catalog()
    assert set(catalog.select('all')) == {device.id for device in default_devices()}
    assert catalog.select('door,ac-bed,curtain') == ['door', 'ac-bed', 'curtain']
    with pytest.raises(ValueError): catalog.select('missing-device')
    with pytest.raises(ValueError): catalog.select('door,door')
