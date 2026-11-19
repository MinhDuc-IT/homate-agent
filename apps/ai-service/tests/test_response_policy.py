from types import SimpleNamespace
from homate_ai.agent.interpretation import Issue
from homate_ai.agent.policy import clarification_reply


def report(*issues, status='needs_clarification'):
    return SimpleNamespace(reviews=[SimpleNamespace(status=status, issues=list(issues))])


def test_clarification_asks_for_target_before_values_without_exposing_schema_errors():
    result = clarification_reply(report(
        Issue(code='invalid_value', path='', message="'device_id' is a required property"),
        Issue(code='missing_parameter', path='parameters.temperature', message='internal parameter error'),
        Issue(code='ambiguous_target', path='device_id', message='internal candidate resolution error',
              candidates=[{'id': 'living', 'name': 'Đèn phòng khách'}, {'id': 'bed', 'name': 'Đèn phòng ngủ'}])))
    assert result.count('?') == 1 and '\n' not in result
    assert 'Đèn phòng khách' in result and 'Đèn phòng ngủ' in result
    assert 'temperature' not in result and 'device_id' not in result and 'internal' not in result


def test_permission_failure_is_not_hidden_behind_a_parameter_question():
    result = clarification_reply(report(
        Issue(code='missing_parameter', path='name', message='missing name'), status='forbidden'))
    assert 'quyền' in result and 'tên' not in result
