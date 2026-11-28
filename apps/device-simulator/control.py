"""Simulate a physical switch: python control.py light-living power true."""
import json
import sys
import urllib.request

arguments = sys.argv[1:]
if arguments and arguments[0] == '--fault':
    _, identifier, key, raw = arguments
    action = 'mode'
    if key not in {'mode', 'delay_ms'}:
        raise ValueError('Use --fault DEVICE mode normal|silent|reject or --fault DEVICE delay_ms NUMBER')
    payload = {'mode': raw} if key == 'mode' else {'mode': 'normal', 'delay_ms': int(raw)}
else:
    identifier, key, raw = arguments
    # Legacy fault syntax remains accepted only for fault names. Device mode
    # (cool/dry/fan) is an ordinary state field, not the fault injection mode.
    action = 'mode' if key == 'delay_ms' or key == 'mode' and raw in {'normal', 'silent', 'reject'} else 'state'
    if action == 'mode':
        payload = {'mode': raw} if key == 'mode' else {'mode': 'normal', 'delay_ms': int(raw)}
    else:
        try: value = json.loads(raw)
        except json.JSONDecodeError: value = raw
        payload = {key: value}
request = urllib.request.Request(f'http://127.0.0.1:9040/devices/{identifier}/{action}',
    data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=5) as response:
    print(response.read().decode())
