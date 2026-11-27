import importlib.util
import json
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import paho.mqtt.client as mqtt
import pytest

from homate.infrastructure.mqtt import MqttTransport
from homate.modules.home.application.devices import DeviceStore
from homate.modules.home.application.gateway import DeviceTransportError
from homate.modules.home.domain.defaults import default_devices

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
