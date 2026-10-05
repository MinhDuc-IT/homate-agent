"""Application facade for household configuration and member management."""
from typing import Any, Protocol
from homate.modules.home.domain.actions import action_writes
from homate.modules.home.domain.device import Device
from homate.modules.home.application.devices import DeviceStore

HOME_ID = "home-michelin-bois"


class HouseholdRepository(Protocol):
    def load_home(self) -> dict: ...
    def load_devices(self) -> list[Device]: ...
    def get_user(self, user_id: str) -> dict | None: ...
    def list_users(self, home_id: str) -> list[dict]: ...
    def create_user(self, home_id: str, data: dict) -> dict: ...
    def update_user(self, home_id: str, user_id: str, data: dict) -> dict: ...
    def deactivate_user(self, home_id: str, user_id: str) -> None: ...
    def list_scenes(self, home_id: str) -> list[dict]: ...
    def get_scene(self, home_id: str, scene_id: str) -> dict: ...
    def create_scene(self, home_id: str, **data: Any) -> dict: ...
    def update_scene(self, home_id: str, scene_id: str, **data: Any) -> dict: ...
    def delete_scene(self, home_id: str, scene_id: str) -> None: ...
    def get_home_settings(self, home_id: str) -> dict: ...
    def update_home_settings(self, home_id: str, data: dict) -> dict: ...
    def list_command_logs(self, home_id: str, **filters: Any) -> list[dict]: ...
    def append_command_log(self, home_id: str, **data: Any) -> dict: ...
    def list_hitl_policies(self, home_id: str) -> list[dict]: ...
    def replace_hitl_policies(self, home_id: str, data: list[dict]) -> list[dict]: ...
    def load_rooms_ambient(self, home_id: str) -> list[dict]: ...
    def set_room_mock(self, home_id: str, room_id: str, **data: Any) -> dict: ...


class HouseholdService:
    def __init__(self, repository: HouseholdRepository):
        self.repository = repository

    def load_home(self): return self.repository.load_home()
    def get_user(self, user_id): return self.repository.get_user(user_id)
    def list_users(self, home_id): return self.repository.list_users(home_id)
    def create_user(self, home_id, data):
        data = {**data, "name": data["name"].strip()}
        if not data["name"]: raise ValueError("Tên thành viên không được trống")
        return self.repository.create_user(home_id, data)
    def update_user(self, home_id, user_id, data):
        if "name" in data:
            data = {**data, "name": (data["name"] or "").strip()}
            if not data["name"]: raise ValueError("Tên thành viên không được trống")
        return self.repository.update_user(home_id, user_id, data)
    def deactivate_user(self, home_id, user_id): return self.repository.deactivate_user(home_id, user_id)
    def list_scenes(self, home_id): return self.repository.list_scenes(home_id)
    def get_scene(self, home_id, scene_id): return self.repository.get_scene(home_id, scene_id)
    def _validate_steps(self, home_id, steps):
        room_ids = {r["id"] for r in self.repository.load_rooms_ambient(home_id)}
        devices = {d.id: d for d in self.repository.load_devices() if d.room in room_ids}
        for step in steps:
            device = devices.get(step["device_id"])
            if device is None: raise ValueError("Thiết bị không thuộc ngôi nhà này")
            sandbox = DeviceStore([device])
            for key, value in action_writes(device, step["action"], step.get("parameters") or {}):
                sandbox.apply_action(device.id, key, value)
    def create_scene(self, home_id, **data):
        self._validate_steps(home_id, data.get("steps") or [])
        return self.repository.create_scene(home_id, **data)
    def update_scene(self, home_id, scene_id, **data):
        self._validate_steps(home_id, data.get("steps") or [])
        return self.repository.update_scene(home_id, scene_id, **data)
    def delete_scene(self, home_id, scene_id): return self.repository.delete_scene(home_id, scene_id)
    def get_home_settings(self, home_id): return self.repository.get_home_settings(home_id)
    def update_home_settings(self, home_id, data): return self.repository.update_home_settings(home_id, data)
    def list_command_logs(self, home_id, **filters): return self.repository.list_command_logs(home_id, **filters)
    def append_command_log(self, home_id, **data): return self.repository.append_command_log(home_id, **data)
    def list_hitl_policies(self, home_id): return self.repository.list_hitl_policies(home_id)
    def replace_hitl_policies(self, home_id, data): return self.repository.replace_hitl_policies(home_id, data)
    def load_rooms_ambient(self, home_id): return self.repository.load_rooms_ambient(home_id)
    def set_room_mock(self, home_id, room_id, **data): return self.repository.set_room_mock(home_id, room_id, **data)
