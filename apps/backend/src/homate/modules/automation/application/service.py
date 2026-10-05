from __future__ import annotations
from typing import Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homate.modules.automation.domain.recurrence import calculate_next_run
from homate.modules.home.domain.actions import action_writes
from homate.modules.home.application.devices import DeviceStore


class ScheduleRepository(Protocol):
    def list(self, home_id, **filters) -> list[dict]: ...
    def get(self, home_id, identifier) -> dict: ...
    def create(self, home_id, user_id, data) -> dict: ...
    def update(self, home_id, identifier, data) -> dict: ...
    def delete(self, home_id, identifier) -> None: ...
    def runs(self, home_id, identifier) -> list[dict]: ...
    def execute_due(self, now=None) -> int: ...
    def drain_execution_events(self) -> list[dict]: ...


class ScheduleService:
    def __init__(self, repository: ScheduleRepository, household, devices):
        self.repository = repository
        self.household = household
        self.devices = devices

    def _validate(self, home_id, data):
        try: ZoneInfo(data["timezone"])
        except (ZoneInfoNotFoundError, ValueError, TypeError): raise ValueError("Múi giờ không hợp lệ") from None
        if not (data.get("name") or "").strip(): raise ValueError("Tên lịch không được trống")
        if data["target_type"] == "scene":
            self.household.get_scene(home_id, data["scene_id"])
            data.update(device_id=None, action=None, parameters={})
        else:
            device = self.devices.get(data["device_id"])
            data["scene_id"] = None
            if device.room not in {r["id"] for r in self.household.load_rooms_ambient(home_id)}:
                raise ValueError("Thiết bị không thuộc ngôi nhà này")
            sandbox = DeviceStore([device])
            for key, value in action_writes(device, data["action"], data.get("parameters") or {}):
                sandbox.apply_action(device.id, key, value)
        if data["schedule_type"] == "once":
            if not data.get("run_at"): raise ValueError("Lịch một lần cần thời điểm chạy")
            data["recurrence_rule"] = None
        else:
            rule = data.get("recurrence_rule") or {}
            if rule.get("frequency") not in {"daily", "weekly"}: raise ValueError("Kiểu lặp không hợp lệ")
            days = rule.get("days_of_week") or []
            if rule["frequency"] == "weekly" and not days: raise ValueError("Chọn ít nhất một ngày trong tuần")
            if any(not isinstance(d, int) or not 0 <= d <= 6 for d in days): raise ValueError("Ngày trong tuần không hợp lệ")
            data["run_at"] = None
        calculate_next_run(**{k: data.get(k) for k in ("schedule_type", "timezone", "run_at", "recurrence_rule")})
        return data

    def list(self, home_id, **filters): return self.repository.list(home_id, **filters)
    def get(self, home_id, identifier): return self.repository.get(home_id, identifier)
    def create(self, home_id, user_id, data): return self.repository.create(home_id, user_id, self._validate(home_id, dict(data)))
    def update(self, home_id, identifier, data):
        merged = {**self.repository.get(home_id, identifier), **data}
        return self.repository.update(home_id, identifier, self._validate(home_id, merged))
    def delete(self, home_id, identifier): return self.repository.delete(home_id, identifier)
    def runs(self, home_id, identifier): return self.repository.runs(home_id, identifier)
    def execute_due(self, now=None): return self.repository.execute_due(now)
    def drain_execution_events(self): return self.repository.drain_execution_events()
