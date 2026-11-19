"""Choose a user-facing next step from deterministic validation results."""
import re

LABELS = {'device_id': 'thiết bị', 'scene_id': 'kịch bản', 'schedule_id': 'lịch',
          'name': 'tên', 'voice_keyword': 'từ khóa', 'run_at': 'ngày và giờ chạy',
          'recurrence_rule': 'thời gian lặp', 'temperature': 'nhiệt độ', 'brightness': 'độ sáng',
          'speed': 'tốc độ', 'volume': 'âm lượng', 'action': 'hành động', 'days_of_week': 'ngày trong tuần'}


def question_for(issue):
    if issue.code == 'ambiguous_target':
        names = [str(c.get('name') or 'thiết bị chưa đặt tên') for c in issue.candidates]
        if len(names) > 4:
            return 'Có nhiều thiết bị phù hợp. Bạn muốn chọn thiết bị ở phòng nào?'
        return 'Bạn muốn chọn ' + ' hay '.join(names) + '?'
    field = issue.path.split('.')[-1]
    if not field:
        match = re.search(r"'([^']+)' is a required property", issue.message)
        field = match.group(1) if match else ''
    if issue.code == 'missing_parameter' and field in LABELS:
        return 'Bạn cho biết ' + LABELS[field] + ' mong muốn nhé.'
    if issue.code == 'unverified_parameter':
        return 'Bạn muốn đặt ' + LABELS.get(field, 'giá trị') + ' là bao nhiêu?' if field in {'temperature', 'brightness', 'speed', 'volume'} else 'Bạn cho biết rõ ' + LABELS.get(field, 'yêu cầu') + ' nhé?'
    if issue.code == 'invalid_value':
        return LABELS.get(field, 'Thông tin yêu cầu').capitalize() + ' chưa hợp lệ với thiết bị hoặc lịch đã chọn.'
    if issue.code == 'invalid_read_scope':
        return 'Bạn muốn tra cứu thông tin của thiết bị, phòng hay kịch bản nào?'
    if issue.code in {'forbidden', 'permission_denied'}:
        return 'Bạn chưa có quyền thực hiện thao tác này.'
    if issue.code in {'target_not_found', 'missing_target', 'unverified_target', 'unresolved_reference'}:
        return 'Bạn muốn thao tác với ' + LABELS.get(field, 'thiết bị') + ' nào?'
    if issue.code == 'unsupported_condition':
        return 'Tôi chưa hỗ trợ tự động chạy theo điều kiện cảm biến.'
    if issue.code == 'unsupported_capability':
        return 'Tôi chưa hỗ trợ yêu cầu này.'
    return 'Bạn nói rõ thao tác muốn thực hiện nhé?'


def clarification_reply(report):
    if any(review.status == 'forbidden' for review in report.reviews):
        return 'Bạn chưa có quyền thực hiện thao tác này.'
    issues = [issue for review in report.reviews for issue in review.issues]
    # Ask about the blocking target before values that depend on that target.
    priority = {'unsupported_condition': 0, 'ambiguous_target': 1,
                'unresolved_reference': 2, 'missing_target': 2, 'target_not_found': 2,
                'unverified_target': 2, 'missing_parameter': 3, 'invalid_value': 4,
                'unverified_parameter': 5}
    if issues:
        issue = min(issues, key=lambda item: priority.get(item.code, 6))
        if all(not getattr(review, 'requires_confirmation', True) for review in report.reviews) and issue.code in {
                'unverified_target', 'missing_target', 'unresolved_reference'}:
            return 'Bạn muốn xem thông tin của ' + LABELS.get(issue.path.split('.')[-1], 'đối tượng') + ' nào?'
        return question_for(issue)
    return 'Bạn muốn tôi giúp việc gì?'


def planning_reply(error):
    prefix = 'Không xác định được đối tượng cần loại trừ: '
    if error.startswith(prefix):
        return 'Bạn muốn loại trừ thiết bị nào ở “' + error[len(prefix):] + '” ?'
    return 'Tôi chưa thể xử lý các thao tác này cùng nhau. Bạn muốn làm thao tác nào trước?'
