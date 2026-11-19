"""Explicit cancellation/approval vocabulary and evidence carried between user turns."""


CANCEL = {'huy', 'huy di', 'thoi huy', 'huy yeu cau', 'huy ke hoach', 'bo qua yeu cau nay'}
APPROVE = {'dong y', 'xac nhan', 'ok', 'co', 'lam di', 'thuc hien di'}


def history_evidence(interpretation):
    result = interpretation.model_copy(deep=True)
    for intent in result.intents:
        for item in [*intent.targets, *intent.evidence, *intent.adjustments]:
            if item.source == 'utterance':
                item.source = 'history'
    return result
