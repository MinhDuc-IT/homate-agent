from __future__ import annotations
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

def _now():
    return datetime.now(UTC)

def calculate_next_run(*, schedule_type: str, timezone: str, run_at: str | None, recurrence_rule: dict[str, Any] | None, after: datetime | None=None) -> datetime | None:
    after = after or _now()
    if schedule_type == 'once':
        if not run_at:
            return None
        parsed = datetime.fromisoformat(run_at)
        return parsed.replace(tzinfo=ZoneInfo(timezone)).astimezone(UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
    rule = recurrence_rule or {}
    hour, minute = map(int, str(rule.get('time', '00:00')).split(':'))
    tz = ZoneInfo(timezone)
    local_after = after.astimezone(tz)
    frequency = rule.get('frequency', 'daily')
    days = set((int(day) for day in rule.get('days_of_week', [])))
    for offset in range(0, 15):
        candidate_date = local_after.date() + timedelta(days=offset)
        candidate = datetime.combine(candidate_date, time(hour, minute), tzinfo=tz)
        if candidate <= local_after:
            continue
        if frequency == 'weekly' and days and (candidate.weekday() not in days):
            continue
        return candidate.astimezone(UTC)
    return None
