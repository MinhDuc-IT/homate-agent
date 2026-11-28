"""MQTT command acknowledgements and authoritative device reports.

Network callbacks never call DeviceStore or PostgreSQL: a command holds the
store lock while waiting for its ack. Unsolicited reports are reconciled later.
"""
import json
import math
import queue
import threading
import time
from dataclasses import dataclass, field
from uuid import UUID, uuid4

import paho.mqtt.client as mqtt

from homate.modules.home.application.devices import DeviceStore
from homate.modules.home.application.gateway import DeviceTransportError


@dataclass
class Pending:
    device: object
    event: threading.Event = field(default_factory=threading.Event)
    report: dict | None = None
    error: str | None = None


def validated_report(device, payload):
    if not isinstance(payload, dict) or payload.get('device_id') != device.id:
        raise ValueError('wrong_device')
    UUID(payload['boot_id'])
    if type(payload.get('revision')) is not int or payload['revision'] < 0:
        raise ValueError('invalid_revision')
    state = payload['state']
    if not isinstance(state, dict) or state.keys() != device.state.keys():
        raise ValueError('invalid_state_keys')
    controls = {c.key: c for c in device.controls}
    for key, value in state.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('invalid_number')
        if key in controls:
            DeviceStore._coerce_and_validate(controls[key], value)
        elif key == 'locked' and any(control.type == 'action' and control.key in {'lock', 'unlock'} for control in device.controls):
            if type(value) is not bool:
                raise ValueError('invalid_lock_state')
        elif type(value) is not type(device.state[key]) or value != device.state[key]:
            # A catalog may include read-only fields without a control (e.g.
            # ac-bed fan). Preserve known metadata rather than accepting writes.
            raise ValueError('unsupported_report_key')
    normalized = device.model_copy(deep=True, update={'state': dict(state)})
    DeviceStore._synchronize_position_state(normalized, set(state))
    if normalized.state != state:
        raise ValueError('inconsistent_position_state')
    return payload


class MqttTransport:
    def __init__(self, host, port, devices, timeout=5):
        self.devices = {device.id: device for device in devices}
        self.timeout = timeout
        self.host, self.port = host, port
        self.ready = threading.Event()
        self.lock = threading.RLock()
        self.pending = {}
        self.latest = {}
        self.presence = {}
        self.retired_boots = {identifier: set() for identifier in self.devices}
        self.reports = queue.Queue(maxsize=256)
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='homate-backend-' + uuid4().hex[:12])
        self.client.on_connect = self._connect
        self.client.on_subscribe = lambda client, userdata, mid, reasons, properties: self.ready.set() if all(not r.is_failure for r in reasons) else None
        self.client.on_disconnect = self._disconnect
        self.client.on_message = self._message
        self.client.reconnect_delay_set(1, 5)
        self.client.max_queued_messages_set(64)

    def start(self):
        self.client.connect_async(self.host, self.port, keepalive=15)
        self.client.loop_start()

    def stop(self):
        self.client.disconnect()
        self.client.loop_stop()
        self._disconnect(None, None, None, None, None)

    def _connect(self, client, userdata, flags, reason, properties):
        if reason.is_failure:
            return
        topics = [('homate/availability/+', 1)] + [(f'homate/devices/{identifier}/{suffix}', 1) for identifier in self.devices for suffix in ('state', 'ack')]
        if topics:
            client.subscribe(topics)

    def _disconnect(self, client, userdata, flags, reason, properties):
        self.ready.clear()
        with self.lock:
            for item in self.pending.values():
                item.error = 'mqtt_disconnected'
                item.event.set()

    def _remember(self, report):
        identifier, boot, revision = report['device_id'], report['boot_id'], report['revision']
        previous = self.latest.get(identifier)
        if boot in self.retired_boots[identifier]:
            return False
        if previous:
            if previous[0] == boot and revision < previous[1]:
                return False
            if previous[0] != boot:
                self.retired_boots[identifier].add(previous[0])
        self.latest[identifier] = (boot, revision)
        return True

    def is_current(self, report):
        with self.lock:
            return self.latest.get(report['device_id']) == (report['boot_id'], report['revision'])

    def connectivity(self, identifier):
        with self.lock:
            entry = self.presence.get(identifier)
            if not self.ready.is_set():
                status = 'offline'
            elif entry is None:
                status = 'unknown'
            else:
                status = 'online' if entry['online'] and time.time() - entry['seen'] < 35 else 'offline'
            return {'status': status, 'last_seen_at': entry['seen'] if entry else None}

    def _message(self, client, userdata, message):
        if len(message.payload) > 8192:
            return
        try:
            parts = message.topic.split('/')
            if len(parts) == 3 and parts[:2] == ['homate', 'availability']:
                payload = json.loads(message.payload)
                if type(payload.get('online')) is not bool or not isinstance(payload.get('device_ids'), list):
                    return
                stamp = payload.get('sent_at')
                if payload['online'] and (type(stamp) not in (float, int) or not math.isfinite(stamp) or stamp > time.time() + 5):
                    return
                with self.lock:
                    for identifier in payload['device_ids']:
                        if isinstance(identifier, str) and identifier in self.devices:
                            previous = self.presence.get(identifier)
                            if payload['online'] and previous and previous['seen'] is not None and stamp < previous['seen']:
                                continue
                            self.presence[identifier] = {'online': payload['online'], 'seen': stamp if payload['online'] else previous['seen'] if previous else None}
                            if not payload['online'] or time.time() - stamp >= 35:
                                for pending in self.pending.values():
                                    if pending.device.id == identifier:
                                        pending.error = 'device_offline'
                                        pending.event.set()
                return
            if len(parts) != 4 or parts[:2] != ['homate', 'devices'] or parts[2] not in self.devices:
                return
            payload = json.loads(message.payload)
            device = self.devices[parts[2]]
            with self.lock:
                if parts[3] == 'ack':
                    # Retained/old acks never complete another request.
                    item = self.pending.get(payload.get('command_id'))
                    if message.retain or item is None or item.device.id != device.id:
                        return
                    if payload.get('device_id') != device.id:
                        return
                    if payload.get('status') != 'succeeded':
                        item.error = 'device_rejected'
                    else:
                        validated_report(device, payload)
                        if not self._remember(payload):
                            return
                        item.report = payload
                    item.event.set()
                elif parts[3] == 'state':
                    validated_report(device, payload)
                    if not self._remember(payload):
                        return
                    try:
                        self.reports.put_nowait(payload)
                    except queue.Full:
                        self.reports.get_nowait()
                        self.reports.put_nowait(payload)
        except (ValueError, TypeError, KeyError, AttributeError):
            # Invalid packets do not kill the MQTT network thread.
            return

    def execute(self, desired, settings):
        if desired.id not in self.devices:
            raise DeviceTransportError('mqtt_device_not_configured')
        if not self.ready.wait(self.timeout):
            raise DeviceTransportError('mqtt_unavailable')
        if self.connectivity(desired.id)['status'] == 'offline':
            raise DeviceTransportError('device_offline')
        identifier = settings['_command_id']
        item = Pending(desired)
        with self.lock:
            self.pending[identifier] = item
        try:
            packet = {'command_id': identifier, 'device_id': desired.id,
                      'expires_at': time.time() + self.timeout, 'desired_state': desired.state}
            info = self.client.publish(f'homate/devices/{desired.id}/set', json.dumps(packet), qos=1, retain=False)
            if info.rc != mqtt.MQTT_ERR_SUCCESS:
                raise DeviceTransportError('mqtt_publish_failed')
            # MQTT PUBACK only confirms delivery to broker. Wait for device ack.
            if not item.event.wait(self.timeout):
                raise DeviceTransportError('mqtt_timeout')
            if item.error:
                raise DeviceTransportError(item.error)
            if not item.report:
                raise DeviceTransportError('mqtt_missing_report')
            return desired.model_copy(update={'state': item.report['state']}, deep=True)
        finally:
            with self.lock:
                self.pending.pop(identifier, None)
