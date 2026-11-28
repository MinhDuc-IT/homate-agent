"""Exercise all MQTT device controls against local Docker; no LLM calls.

Temporarily selects MQTT in DB. Restores adapters, backend states and virtual
hardware states in finally. Simulator must run with MQTT_SIMULATED_DEVICE_IDS=all.
"""
import asyncio
import json
from pathlib import Path
import subprocess

import httpx
import websockets


def sql(query):
    result = subprocess.run(['docker', 'compose', 'exec', '-T', 'db', 'sh', '-c',
        'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At'],
        input=query, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def literal(value):
    return "'" + value.replace("'", "''") + "'"


async def main():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000', timeout=20) as client, httpx.AsyncClient(base_url='http://127.0.0.1:9040', timeout=20) as hardware:
        auth = await client.post('/api/dashboard/auth/login', json={'user_id': 'minh-duc', 'pin': '1234'})
        auth.raise_for_status()
        token = auth.json()['access_token']
        client.headers['Authorization'] = 'Bearer ' + token
        async def get(path):
            response = await client.get('/api/dashboard' + path)
            response.raise_for_status()
            return response.json()
        async def physical(identifier, state):
            response = await hardware.post(f'/devices/{identifier}/state', json=state)
            response.raise_for_status()
            return response.json()['state']
        async def wait_state(identifier, expected):
            for _ in range(60):
                if (await get('/devices/' + identifier))['state'] == expected: return
                await asyncio.sleep(.1)
            raise AssertionError('State did not reconcile: ' + identifier)
        async def action(identifier, key, value):
            response = await client.post(f'/api/dashboard/devices/{identifier}/actions', json={'key': key, 'value': value})
            assert response.status_code == 200, (identifier, key, response.status_code, response.text)
            receipt = (await get(f'/devices/{identifier}/commands'))[0]
            assert receipt['adapter'] == 'mqtt' and receipt['status'] == 'succeeded'
            assert receipt['reported_state'] == response.json()['device']['state']
            return response.json()['device']['state']

        original_devices = await get('/devices')
        response = await hardware.get('/devices')
        response.raise_for_status()
        original_hardware = {device['device_id']: device['state'] for device in response.json()}
        assert {device['id'] for device in original_devices} == original_hardware.keys(), 'Run simulator with all catalog devices'
        connections = json.loads(sql("SELECT json_agg(json_build_object('device_id', device_id, 'adapter', adapter, 'settings', settings)) FROM homate.device_connections;"))
        identifiers = ','.join(literal(device['id']) for device in original_devices)
        backup = Path('.work/mqtt-catalog-backup.json')
        backup.parent.mkdir(exist_ok=True)
        backup.write_text(json.dumps({'devices': original_devices, 'hardware': original_hardware, 'connections': connections}), encoding='utf-8')
        count = 0
        try:
            sql(f"UPDATE homate.device_connections SET adapter='mqtt' WHERE device_id IN ({identifiers});")
            for _ in range(60):
                availability = await get('/device-connectivity')
                if all(availability[device['id']]['status'] == 'online' for device in original_devices): break
                await asyncio.sleep(.2)
            else: raise AssertionError('Not all MQTT devices online')
            # Start with powered devices off to keep conflict policy tests valid.
            for device in original_devices:
                state = dict(original_hardware[device['id']])
                if 'power' in state: state['power'] = False
                await physical(device['id'], state)
                await wait_state(device['id'], state)
            for device in original_devices:
                identifier = device['id']
                for control in device['controls']:
                    for key, value in (control.get('when') or {}).items():
                        current = (await get('/devices/' + identifier))['state']
                        if current[key] != value: await action(identifier, key, value)
                    kind, key = control['type'], control['key']
                    current = (await get('/devices/' + identifier))['state']
                    if kind == 'toggle': value = not current[key]
                    elif kind == 'action': value = True
                    elif kind == 'enum': value = control['options'][-1]['value']
                    elif kind == 'level': value = control['levels'][-1]
                    else: value = control['min'] + (control['max'] - control['min']) / 2
                    await action(identifier, key, value)
                    count += 1
                current = (await get('/devices/' + identifier))['state']
                if 'power' in current:
                    await physical(identifier, {'power': False})
                    await wait_state(identifier, {**current, 'power': False})
            print(f'PASS: {count} controls across {len(original_devices)} devices acknowledged over MQTT')

            for identifier, patch in [('curtain-living', {'position': 43}), ('cam-bed', {'recording': True}),
                                      ('fan-bath', {'speed': 1}), ('door', {'locked': True})]:
                receipts = await get(f'/devices/{identifier}/commands')
                async with websockets.connect(f'ws://127.0.0.1:8000/ws/devices?token={token}') as socket:
                    await socket.recv()
                    current = (await get('/devices/' + identifier))['state']
                    # Ensure this is an actual change, not an idempotent report.
                    key = next(iter(patch))
                    if current[key] == patch[key]:
                        patch[key] = not patch[key] if type(patch[key]) is bool else 17 if key == 'position' else 0
                    expected = await physical(identifier, patch)
                    while True:
                        event = json.loads(await asyncio.wait_for(socket.recv(), timeout=8))
                        if event.get('type') == 'device.updated' and event.get('device_id') == identifier:
                            assert event['state'] == expected
                            break
                await wait_state(identifier, expected)
                assert await get(f'/devices/{identifier}/commands') == receipts
            print('PASS: curtain, camera, fan and lock physical state reaches WebSocket without redispatch')
        finally:
            for device in original_devices:
                await physical(device['id'], device['state'])
                await wait_state(device['id'], device['state'])
            queries = [f"UPDATE homate.device_connections SET adapter={literal(item['adapter'])}, settings={literal(json.dumps(item['settings']))}::jsonb WHERE device_id={literal(item['device_id'])};" for item in connections]
            sql('BEGIN;\n' + '\n'.join(queries) + '\nCOMMIT;')
            for identifier, state in original_hardware.items():
                await physical(identifier, state)
            for device in original_devices:
                await wait_state(device['id'], device['state'])
            print('Original adapters, backend states and hardware states restored')


if __name__ == '__main__':
    asyncio.run(main())
