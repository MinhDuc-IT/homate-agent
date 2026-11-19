"""Evaluate the configured live provider in observation or conversation mode.

Requires a running AI service and HOMATE_ACCESS_TOKEN. This uses paid LLM calls.
Reports are written only when --output is supplied; tokens are never serialized.
Conversation mode creates and then cancels pending plans; never confirms them.
"""
import argparse
import json
import os
from pathlib import Path
from uuid import uuid4
import httpx

DEFAULT_CASES = Path(__file__).resolve().parents[1] / 'apps/ai-service/evals/natural_language.json'


def assess(case, report):
    errors = []
    if report.get('executable') is not False or report.get('mode') != 'observe':
        errors.append('Response is not observation mode')
    if report.get('decision') not in case['expected_decisions']:
        errors.append('Unexpected decision: ' + str(report.get('decision')))
    reviews = report.get('reviews', [])
    if len(reviews) < case.get('min_intents', 0):
        errors.append('Missing request components')
    capabilities = {review.get('capability') for review in reviews}
    if not set(case.get('expected_capabilities', [])) <= capabilities:
        errors.append('Expected capabilities missing')
    issue_codes = {issue['code'] for review in reviews for issue in review['issues']}
    if case.get('expected_issues') and not issue_codes.intersection(case['expected_issues']):
        errors.append('Expected clarification/unsupported issue missing')
    for path, expected in case.get('expected_arguments', {}).items():
        parts = path.split('.')
        try:
            actual = reviews[int(parts[0])]['arguments']
            for part in parts[1:]:
                actual = actual[int(part)] if isinstance(actual, list) else actual[part]
            if actual != expected:
                errors.append('Unexpected argument: ' + path)
        except (KeyError, IndexError, TypeError, ValueError):
            errors.append('Missing argument: ' + path)
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ai-url', default='http://127.0.0.1:8010')
    parser.add_argument('--backend-url', default='http://127.0.0.1:8000')
    parser.add_argument('--mode', choices=['analyze', 'chat'], default='analyze')
    parser.add_argument('--cases', type=Path, default=DEFAULT_CASES)
    parser.add_argument('--only', nargs='*', help='Run only these case IDs')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    token = os.environ.get('HOMATE_ACCESS_TOKEN')
    if not token:
        parser.error('Set HOMATE_ACCESS_TOKEN to an authenticated user token.')
    cases = json.loads(args.cases.read_text(encoding='utf-8'))
    if args.only:
        requested = set(args.only)
        if requested - {case['id'] for case in cases}:
            parser.error('Unknown case ID')
        cases = [case for case in cases if case['id'] in requested]
    results = []
    headers = {'Authorization': f'Bearer {token}'}
    with httpx.Client(base_url=args.ai_url, timeout=180, headers=headers) as client, httpx.Client(base_url=args.backend_url, timeout=30, headers=headers) as backend:
        for case in cases:
            conversation_id, version = None, None
            try:
                if args.mode == 'chat':
                    for message in case.get('history', []):
                        if message['role'] != 'user': continue
                        seed = client.post('/api/ai/chat', json={'request_id': str(uuid4()), 'text': message['content'],
                            'conversation_id': conversation_id, 'conversation_version': version})
                        seed.raise_for_status()
                        conversation_id, version = seed.json()['conversation_id'], seed.json()['conversation_version']
                response = client.post('/api/ai/' + args.mode, json={
                    'request_id': str(uuid4()), 'text': case['text'], 'history': case.get('history', []) if args.mode == 'analyze' else [],
                    'conversation_id': conversation_id, 'conversation_version': version})
                if response.status_code in (401, 403):
                    raise SystemExit('Authentication failed; check HOMATE_ACCESS_TOKEN.')
                response.raise_for_status()
                payload = response.json()
                report = payload['analysis'] if args.mode == 'chat' else payload
                expected = dict(case)
                if args.mode == 'chat':
                    conversation_id = payload['conversation_id']
                    if case['id'] in {'ordered-chain', 'exclude-device'}:
                        expected['expected_decisions'] = ['ready_for_review']
                        expected.pop('expected_issues', None)
                errors = assess(expected, report)
                if args.mode == 'chat' and report['decision'] == 'ready_for_review' and any(r['requires_confirmation'] for r in report['reviews']) and not payload.get('pending_actions'):
                    errors.append('Validated write did not produce a pending plan')
                if any(action.get('status') in {'executed', 'executing'} for action in payload.get('pending_actions', [])):
                    errors.append('An action executed without an explicit decision')
                results.append({'id': case['id'], 'passed': not errors, 'errors': errors, 'report': report})
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
                results.append({'id': case['id'], 'passed': False,
                                'errors': ['HTTP or response error'], **diagnostic})
            finally:
                if conversation_id:
                    cleanup = backend.delete('/api/dashboard/agent/conversations/' + conversation_id)
                    if not cleanup.is_success:
                        raise SystemExit('Could not close an evaluation conversation; inspect pending plans before continuing.')
            print(f'{case["id"]}: {"PASS" if results[-1]["passed"] else "FAIL"}')
    print(f'{sum(result["passed"] for result in results)}/{len(results)} passed')
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if all(result['passed'] for result in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
