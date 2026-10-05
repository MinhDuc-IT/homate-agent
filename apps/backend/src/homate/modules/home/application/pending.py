"""Short-lived confirmations for occupancy energy-saving suggestions."""
from __future__ import annotations
from dataclasses import dataclass
import time
import uuid

@dataclass
class PendingAmbientSuggestion:
    request_id: str
    room_id: str
    room_label: str
    device_ids: list[str]
    message: str
    expires_at: float

class PendingAmbientSuggestions:
    def __init__(self, ttl_seconds: int = 60) -> None:
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, PendingAmbientSuggestion] = {}

    def create(self, *, room_id: str, room_label: str, device_ids: list[str], message: str) -> PendingAmbientSuggestion:
        self.purge()
        request_id = str(uuid.uuid4())
        item = PendingAmbientSuggestion(request_id, room_id, room_label, list(device_ids), message, time.time() + self.ttl_seconds)
        self._items[request_id] = item
        return item

    def pop(self, request_id: str) -> PendingAmbientSuggestion | None:
        self.purge()
        return self._items.pop(request_id, None)

    def get(self, request_id: str) -> PendingAmbientSuggestion | None:
        self.purge()
        return self._items.get(request_id)

    def purge(self) -> None:
        now = time.time()
        for request_id in [key for key, item in self._items.items() if item.expires_at <= now]:
            self._items.pop(request_id, None)

pending_ambient = PendingAmbientSuggestions(ttl_seconds=60)
