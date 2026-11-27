"""Simulate a physical switch: python control.py light-living power true."""
import json
import sys
import urllib.request

identifier, key, raw = sys.argv[1:]
action = 'mode' if key in {'mode', 'delay_ms'} else 'state'
payload = {'mode': raw} if key == 'mode' else {'mode': 'normal', 'delay_ms': int(raw)} if key == 'delay_ms' else {key: json.loads(raw)}
request = urllib.request.Request(f'http://127.0.0.1:9040/devices/{identifier}/{action}',
    data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=5) as response:
    print(response.read().decode())
