"""CRUD use cases depend only on a repository port and domain rules."""
from typing import Any, Protocol
from uuid import UUID, uuid4

from homate.modules.catalog.domain import CatalogError, require_same_home, validate_timezone


class CatalogRepository(Protocol):
    def list(self, kind: str, home_id: UUID | None = None) -> list[dict]: ...
    def get(self, kind: str, identifier: UUID) -> dict | None: ...
    def save(self, kind: str, identifier: UUID, values: dict, create: bool) -> dict: ...
    def delete(self, kind: str, identifier: UUID) -> None: ...


class CatalogService:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    def list(self, kind: str, home_id: UUID | None = None):
        return self.repository.list(kind, home_id)

    def get(self, kind: str, identifier: UUID):
        value = self.repository.get(kind, identifier)
        if value is None:
            raise CatalogError("Không tìm thấy dữ liệu.", 404)
        return value

    def save(self, kind: str, values: dict[str, Any], identifier: UUID | None = None):
        current = self.get(kind, identifier) if identifier else None
        if current and kind != "homes" and current["home_id"] != values["home_id"]:
            raise CatalogError("Không thể chuyển dữ liệu sang nhà khác.")
        if kind == "homes":
            validate_timezone(values["timezone"])
        else:
            self.get("homes", values["home_id"])
        if kind == "devices":
            room = self.get("rooms", values["room_id"])
            require_same_home(room["home_id"], values["home_id"])
        if kind == "scenes":
            for step in values["steps"]:
                device = self.get("devices", step["device_id"])
                require_same_home(device["home_id"], values["home_id"])
                if step["action"] not in device["capabilities"]:
                    raise CatalogError(f"Thiết bị {device['name']} không hỗ trợ {step['action']}.")
        if kind == "devices" and current:
            for scene in self.list("scenes", values["home_id"]):
                if any(s["device_id"] == identifier and s["action"] not in values["capabilities"] for s in scene["steps"]):
                    raise CatalogError("Capability đang được scene sử dụng.", 409)
        return self.repository.save(kind, identifier or uuid4(), values, create=current is None)

    def delete(self, kind: str, identifier: UUID):
        self.get(kind, identifier)
        self.repository.delete(kind, identifier)
