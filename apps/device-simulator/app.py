"""Standalone virtual MQTT lights. No backend, database or agent dependency."""
import json
import math
import os
from pathlib import Path
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID, uuid4

import paho.mqtt.client as mqtt


class Devices:
    def __init__(self, path, identifiers, publish):
        self.path, self.publish = Path(path), publish
        self.lock = threading.RLock()
        self.modes = {identifier: {'mode': 'normal', 'delay_ms': 0} for identifier in identifiers}
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {'boot_id': str(uuid4()), 'devices': {}, 'receipts': {}}
        templates = json.loads(Path(__file__).with_name('devices.json').read_text())
        for identifier in identifiers:
            self.data['devices'].setdefault(identifier, {'state': templates[identifier], 'revision': 0})
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data))
        os.replace(temporary, self.path)

    def report(self, identifier):
        return {'device_id': identifier, 'boot_id': self.data['boot_id'], **self.data['devices'][identifier]}

    def emit(self, identifier):
        self.publish(f'homate/devices/{identifier}/state', self.report(identifier), True)

    def validated(self, identifier, state):
        previous = self.data['devices'][identifier]['state']
        if not isinstance(state, dict) or state.keys() != previous.keys() or type(state.get('power')) is not bool:
            raise ValueError('invalid_state')
        if 'brightness' in state:
            value = state['brightness']
            if type(value) not in (int, float) or not math.isfinite(value) or not 1 <= value <= 100:
                raise ValueError('invalid_brightness')
        return state

    def physical(self, identifier, patch):
        with self.lock:
            if not isinstance(patch, dict) or not patch.keys() <= self.data['devices'][identifier]['state'].keys():
                raise ValueError('invalid_state')
            state = self.validated(identifier, {**self.data['devices'][identifier]['state'], **patch})
            self.data['devices'][identifier]['state'] = state
            self.data['devices'][identifier]['revision'] += 1
            self.save()
            self.emit(identifier)
            return self.report(identifier)

    def command(self, identifier, packet):
        try:
            command_id = str(UUID(packet['command_id']))
            if packet['device_id'] != identifier or identifier not in self.modes:
                return
            with self.lock:
                mode = dict(self.modes[identifier])
            if mode['mode'] == 'silent':
                return
            time.sleep(mode['delay_ms'] / 1000)
            with self.lock:
                # Never apply queued commands after their deadline.
                if type(packet['expires_at']) not in (int, float) or not math.isfinite(packet['expires_at']) or time.time() >= packet['expires_at']:
                    reply = {'device_id': identifier, 'command_id': command_id, 'status': 'expired'}
                elif command_id in self.data['receipts']:
                    old = self.data['receipts'][command_id]
                    reply = old['reply'] if old['desired'] == packet['desired_state'] and old['reply']['device_id'] == identifier else {'device_id': identifier, 'command_id': command_id, 'status': 'id_collision'}
                elif mode['mode'] == 'reject':
                    reply = {'device_id': identifier, 'command_id': command_id, 'status': 'rejected'}
                else:
                    state = self.validated(identifier, packet['desired_state'])
                    self.data['devices'][identifier]['state'] = state
                    self.data['devices'][identifier]['revision'] += 1
                    reply = {**self.report(identifier), 'command_id': command_id, 'status': 'succeeded'}
                    self.data['receipts'][command_id] = {'desired': state, 'reply': reply}
                    if len(self.data['receipts']) > 1000:
                        del self.data['receipts'][next(iter(self.data['receipts']))]
                    self.save()
                    self.emit(identifier)
                self.publish(f'homate/devices/{identifier}/ack', reply, False)
        except (KeyError, ValueError, TypeError):
            return


def main():
    identifiers = [identifier.strip() for identifier in os.environ.get('MQTT_SIMULATED_DEVICE_IDS', 'light-living').split(',') if identifier.strip()]
    if not identifiers or any(not identifier.startswith('light-') or not all(c.isalnum() or c == '-' for c in identifier) for identifier in identifiers):
        raise ValueError('Configure light IDs only')
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='homate-mqtt-device-simulator')
    client.will_set('homate/simulator/availability', 'offline', qos=1, retain=True)
    client.reconnect_delay_set(1, 5)
    inbox = queue.Queue(maxsize=64)
    devices = Devices(os.environ.get('STATE_FILE', '/data/devices.json'), identifiers,
        lambda topic, payload, retain: client.publish(topic, json.dumps(payload), qos=1, retain=retain))

    def connected(client, userdata, flags, reason, properties):
        if reason.is_failure:
            return
        client.subscribe([(f'homate/devices/{identifier}/set', 1) for identifier in identifiers])
        client.publish('homate/simulator/availability', 'online', qos=1, retain=True)
        with devices.lock:
            for identifier in identifiers:
                devices.emit(identifier)

    def message(client, userdata, msg):
        if msg.retain or len(msg.payload) > 8192:
            return
        try:
            identifier = msg.topic.split('/')[2]
            if identifier in devices.modes:
                inbox.put_nowait((identifier, json.loads(msg.payload)))
        except (ValueError, IndexError, queue.Full):
            pass

    def work():
        while True:
            identifier, packet = inbox.get()
            devices.command(identifier, packet)

    class HTTP(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def respond(self, status, body):
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def do_GET(self):
            if self.path == '/health':
                return self.respond(200 if client.is_connected() else 503, {'mqtt_connected': client.is_connected()})
            if self.path == '/devices':
                with devices.lock:
                    return self.respond(200, [devices.report(identifier) for identifier in identifiers])
            self.respond(404, {'error': 'not_found'})
        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 8192:
                    raise ValueError('invalid_payload')
                payload = json.loads(self.rfile.read(size))
                _, group, identifier, action = self.path.split('/')
                if group != 'devices' or identifier not in devices.modes:
                    return self.respond(404, {'error': 'not_found'})
                if action == 'state':
                    return self.respond(200, devices.physical(identifier, payload))
                if action == 'mode':
                    if not isinstance(payload, dict) or set(payload) - {'mode', 'delay_ms'} or payload.get('mode') not in {'normal', 'silent', 'reject'} or type(payload.get('delay_ms', 0)) is not int or not 0 <= payload.get('delay_ms', 0) <= 10000:
                        raise ValueError('invalid_mode')
                    with devices.lock:
                        devices.modes[identifier] = {'mode': payload['mode'], 'delay_ms': payload.get('delay_ms', 0)}
                    return self.respond(200, devices.modes[identifier])
                self.respond(404, {'error': 'not_found'})
            except (ValueError, KeyError, TypeError):
                self.respond(400, {'error': 'invalid_request'})

    client.on_connect, client.on_message = connected, message
    threading.Thread(target=work, daemon=True).start()
    client.connect_async(os.environ.get('MQTT_HOST', 'mqtt'), int(os.environ.get('MQTT_PORT', '1883')), keepalive=15)
    client.loop_start()
    try:
        ThreadingHTTPServer(('0.0.0.0', 9040), HTTP).serve_forever()
    finally:
        client.disconnect()
        client.loop_stop()


if __name__ == '__main__':
    main()
