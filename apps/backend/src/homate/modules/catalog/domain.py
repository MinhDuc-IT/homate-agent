"""Framework-independent catalog rules."""
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class CatalogError(Exception):
    def __init__(self, message: str, status: int = 422):
        self.message = message
        self.status = status


def validate_timezone(value: str) -> None:
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError):
        raise CatalogError("Múi giờ không hợp lệ.") from None


def require_same_home(actual, expected) -> None:
    if actual != expected:
        raise CatalogError("Phòng và thiết bị trong scene phải thuộc cùng một nhà.")
