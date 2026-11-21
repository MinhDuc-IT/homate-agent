"""Legacy multi-turn interpretation evaluator (disabled for native tool-loop chat)."""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4
import httpx

DEFAULT_CASES = Path(__file__).resolve().parents[1] / 'apps/ai-service/evals/conversations.json'


def assess_turn(case, payload, saved, previous_plan, previous_task=None):
    errors = []
    analysis = payload.get('analysis', {})
    decision = analysis.get('interpretation', {}).get('dialogue') or {}
    reviews = analysis.get('reviews', [])
    plans = payload.get('pending_actions', [])
    if any(p['status'] in {'executing', 'executed'} for p in plans):
        errors.append('Unexpected execution without approval')
    if 'relation' in case and decision.get('relation') not in case['relation']:
        errors.append('Wrong relationship to conversation')
    if 'plan' in case and bool(plans) != case['plan']:
        errors.append('Unexpected presence/absence of pending plan')
    if case.get('draft') and not saved['state'].get('draft'):
        errors.append('Missing active task')
    if case.get('preserve_task'):
        if decision.get('task_action') != 'preserve':
            errors.append('Side question did not preserve active task')
        if previous_plan and not any(p['id'] == previous_plan for p in plans):
            errors.append('Pending plan was lost during side question')
        if previous_task and saved['state'].get('draft') != previous_task:
            errors.append('Active task changed during side question')
    if case.get('replace_plan') and previous_plan and any(p['id'] == previous_plan for p in plans):
        errors.append('Correction did not replace old plan')
    if case.get('device_id') and not any(r['arguments'].get('device_id') == case['device_id'] for r in reviews):
        errors.append('Wrong write target')
    if 'temperature' in case and not any(r['arguments'].get('parameters', {}).get('temperature') == case['temperature'] for r in reviews):
        errors.append('Wrong absolute temperature')
    if case.get('capability') and not any(r['capability'] == case['capability'] and r['status'] == 'ready_for_review' for r in reviews):
        errors.append('Expected ready read capability missing')
    if case.get('read_device'):
        if not any(r.get('read_context', {}).get('entities', {}).get('device_id') == case['read_device']
                   and r['status'] == 'ready_for_review' for r in reviews):
            errors.append('Wrong or unresolved contextual read target')
        observations = saved['state'].get('conversation', {}).get('observations', [])
        devices = [device for item in observations for device in item.get('result', {}).get('devices', [])]
        if {device['id'] for device in devices} != {case['read_device']}:
            errors.append('Read result was not scoped to the referenced device')
        if case.get('read_fields') and not any(set(case['read_fields']) <= set(d.get('state', {})) for d in devices):
            errors.append('Requested backend fields missing')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', type=Path, default=DEFAULT_CASES)
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--ai-url', default='http://127.0.0.1:8010')
    parser.add_argument('--backend-url', default='http://127.0.0.1:8000')
    args = parser.parse_args()
    parser.error('This legacy evaluator expects interpretation labels. Native chat can execute routine actions; migrate the evaluator before running its corpus.')
    token = os.environ.get('HOMATE_ACCESS_TOKEN')
    if not token:
        parser.error('Set HOMATE_ACCESS_TOKEN; never put tokens in reports.')
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    if args.only:
        if set(args.only) - {c['id'] for c in cases}:
            parser.error('Unknown conversation ID')
        cases = [c for c in cases if c['id'] in args.only]
    results = []
    with httpx.Client(base_url=args.ai_url, timeout=180, headers={'Authorization': f'Bearer {token}'}) as ai, \
            httpx.Client(base_url=args.backend_url, timeout=30, headers={'Authorization': f'Bearer {token}'}) as backend:
        for case in cases:
            conversation, version, previous_plan, previous_task = None, None, None, None
            turns = []
            try:
                for number, turn in enumerate(case['turns']):
                    response = ai.post('/api/ai/chat', json={'request_id': str(uuid4()), 'text': turn['text'],
                        'conversation_id': conversation, 'conversation_version': version})
                    response.raise_for_status()
                    payload = response.json()
                    conversation, version = payload['conversation_id'], payload['conversation_version']
                    saved = backend.get('/api/dashboard/agent/conversations/' + conversation)
                    saved.raise_for_status()
                    errors = assess_turn(turn, payload, saved.json(), previous_plan, previous_task)
                    turns.append({'turn': number + 1, 'passed': not errors, 'errors': errors, 'response': payload})
                    plans = payload.get('pending_actions', [])
                    previous_plan = plans[0]['id'] if plans else None
                    previous_task = saved.json()['state'].get('draft')
                    print(f'{case["id"]} turn {number + 1}: {"PASS" if not errors else "FAIL"}', flush=True)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
                diagnostic = {'error_type': type(error).__name__}
                if isinstance(error, httpx.HTTPStatusError):
                    diagnostic['http_status'] = error.response.status_code
                    provider_status = error.response.headers.get('X-Provider-Status', '')
                    if provider_status.isdigit() and 100 <= int(provider_status) <= 599:
                        diagnostic['provider_status'] = int(provider_status)
                    code = error.response.headers.get('X-Agent-Error')
                    if code in {'agent_unavailable', 'interpreter_schema_invalid', 'provider_http_error', 'provider_response_invalid', 'provider_timeout', 'provider_rate_limited'}:
                        diagnostic['agent_error_code'] = code
                turns.append({'passed': False, 'errors': ['HTTP or response error'], **diagnostic})
            finally:
                if conversation:
                    cleanup = backend.delete('/api/dashboard/agent/conversations/' + conversation)
                    cleanup.raise_for_status()
            passed = len(turns) == len(case['turns']) and all(t['passed'] for t in turns)
            results.append({'id': case['id'], 'passed': passed, 'turns': turns})
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{sum(r["passed"] for r in results)}/{len(results)} conversations passed')
    return 0 if all(r['passed'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
