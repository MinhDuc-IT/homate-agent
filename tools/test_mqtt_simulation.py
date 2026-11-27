"""Run against local Docker. No LLM calls; restores device state and test modes."""
import asyncio
import json
import time

import httpx
import websockets


async def main():
    backend, simulator = 'http://127.0.0.1:8000', 'http://127.0.0.1:9040'
    device = 'light-living'
    async with httpx.AsyncClient(timeout=20) as client:
        auth = await client.post(backend+'/api/dashboard/auth/login', json={'user_id': 'minh-duc', 'pin': '1234'})
        auth.raise_for_status()
        token = auth.json()['access_token']
        headers = {'Authorization': 'Bearer '+token}
        path = backend+f'/api/dashboard/devices/{device}'
        original = (await client.get(path, headers=headers)).json()['state']
        async def mode(name, delay_ms=0):
            response = await client.post(simulator+f'/devices/{device}/mode', json={'mode': name, 'delay_ms': delay_ms})
            response.raise_for_status()
        async def wait_state(expected):
            for _ in range(50):
                response = await client.get(path, headers=headers)
                response.raise_for_status()
                if response.json()['state'] == expected:
                    return
                await asyncio.sleep(.1)
            raise AssertionError('Backend did not reconcile MQTT state')
        try:
            await mode('normal')
            response = await client.post(path+'/actions', headers=headers, json={'key': 'power', 'value': not original['power']})
            response.raise_for_status()
            expected = response.json()['device']['state']
            receipts = (await client.get(path+'/commands', headers=headers)).json()
            assert receipts[0]['adapter'] == 'mqtt' and receipts[0]['status'] == 'succeeded'
            assert receipts[0]['reported_state'] == expected
            print('PASS: device ack and durable MQTT receipt')
            # A device-originated switch event must reach the existing WebSocket.
            async with websockets.connect(f'ws://127.0.0.1:8000/ws/devices?token={token}') as socket:
                await socket.recv()
                expected = {**expected, 'power': original['power']}
                physical = await client.post(simulator+f'/devices/{device}/state', json=expected)
                physical.raise_for_status()
                while True:
                    event = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
                    if event.get('type') == 'device.updated' and event.get('device_id') == device:
                        assert event['state'] == expected
                        break
            await wait_state(expected)
            print('PASS: physical switch -> MQTT -> backend -> WebSocket')
            for name, delay in [('reject', 0), ('silent', 0), ('normal', 6500)]:
                await mode(name, delay)
                pending = asyncio.create_task(client.post(path+'/actions', headers=headers, json={'key': 'power', 'value': not expected['power']}))
                await asyncio.sleep(.25)
                started = time.monotonic()
                health = await client.get(backend+'/health')
                assert health.status_code == 200 and time.monotonic()-started < 2
                response = await pending
                assert response.status_code == 503
                if delay:
                    await asyncio.sleep(2)
                assert (await client.get(path, headers=headers)).json()['state'] == expected
                receipt = (await client.get(path+'/commands', headers=headers)).json()[0]
                assert receipt['status'] == 'failed' and receipt['reported_state'] is None
                print('PASS:', name, delay, 'no false success; health responsive')
        finally:
            await mode('normal')
            response = await client.post(simulator+f'/devices/{device}/state', json=original)
            response.raise_for_status()
            await wait_state(original)
    print('MQTT integration checks passed; original state restored.')


if __name__ == '__main__':
    asyncio.run(main())
