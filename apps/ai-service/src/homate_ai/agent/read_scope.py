"""Resolve read descriptions against authenticated entities before fetching facts."""
from homate_ai.agent.grounding import ground, has_evidence, normalize
from homate_ai.agent.interpretation import Issue


def resolve_read_scope(intent, snapshot, schedules, text, history, contextual=False):
    selections, proof, issues = [], {}, []
    collections = {'device': snapshot['devices'], 'room': snapshot['rooms'], 'scene': snapshot['scenes']}
    for target in intent.read_focus:
        if intent.capability != 'get_home_snapshot' or target.entity not in collections or target.path != target.entity + '_id':
            issues.append(Issue(code='invalid_read_scope', path='read_focus', message='Đối tượng tra cứu không phù hợp chức năng đọc.'))
            continue
        if not contextual and not has_evidence(target.source, target.quote, text, history):
            issues.append(Issue(code='unverified_target', path=target.path, message='Cần xác định đối tượng từ lời người dùng.'))
            continue
        targets = [target]
        if target.scope == 'all':
            scope_proof = target.scope_evidence
            if not contextual and (not scope_proof or scope_proof.path != 'scope' or not has_evidence(scope_proof.source, scope_proof.quote, text, history)):
                # Missing set evidence means the read description is unresolved,
                # not permission to broaden the request to every device.
                selector = intent.model_copy(update={'arguments': {}, 'targets': [target.model_copy(
                    update={'scope': 'single', 'exclusions': []})], 'adjustments': []})
                _, _, errors = ground(selector, snapshot, schedules, text, history)
                issues.extend(errors or [Issue(code='unresolved_reference', path=target.path,
                    message='Cần làm rõ phạm vi đối tượng tra cứu.')])
                continue
            if target.reference:
                issues.append(Issue(code='unresolved_reference', path=target.path, message='Cần xác định phạm vi tra cứu.'))
                continue
            candidates = list(collections[target.entity])
            if target.name:
                candidates = [c for c in candidates if normalize(target.name) in {normalize(c['id']), normalize(c['name'])}]
            if target.kind:
                candidates = [c for c in candidates if c.get('kind') == target.kind]
            if target.room:
                room_ids = {r['id'] for r in snapshot['rooms'] if normalize(target.room) in {normalize(r['id']), normalize(r['name'])}}
                candidates = [c for c in candidates if c.get('room') in room_ids]
            for exclusion in target.exclusions:
                room_ids = {r['id'] for r in snapshot['rooms'] if normalize(exclusion) in {normalize(r['id']), normalize(r['name'])}}
                excluded = [c for c in candidates if c.get('room') in room_ids or normalize(exclusion) in {normalize(c['id']), normalize(c['name'])}]
                if not excluded:
                    issues.append(Issue(code='unresolved_reference', path=target.path, message='Không xác định được đối tượng loại trừ.'))
                candidates = [c for c in candidates if c not in excluded]
            targets = [target.model_copy(update={'scope': 'single', 'exclusions': [], 'name': c['id'], 'room': None, 'kind': None}) for c in candidates]
            if not targets:
                issues.append(Issue(code='target_not_found', path=target.path, message='Không tìm thấy đối tượng phù hợp.'))
        for selected in targets:
            selector = intent.model_copy(update={'arguments': {}, 'targets': [selected], 'adjustments': []})
            bound, evidence, errors = ground(selector, snapshot, schedules, text, history, contextual=contextual)
            issues.extend(errors)
            if bound and not errors:
                if bound not in selections:
                    selections.append(bound)
                if len(intent.read_focus) == 1 and target.scope == 'single':
                    proof.update(evidence)
    return {'entities': selections[0] if len(selections) == 1 else {}, 'selections': selections,
            'provenance': proof, 'requested_fields': intent.requested_fields}, issues
