"""Occupancy mock helpers — vacancy timing, per-room device state, snapshot assembly."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from homate.modules.home.application.devices import DeviceStore
from homate.modules.home.domain.ambient import AmbientSnapshot, RoomAmbient, WeatherSnapshot


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def vacant_minutes(occupancy_changed_at: str | None, *, now: datetime | None = None) -> int:
    """Minutes since a room was last marked vacant. 0 if occupied or unknown."""
    changed = _parse_iso(occupancy_changed_at)
    if changed is None:
        return 0
    now = now or datetime.now(UTC)
    delta = now - changed
    return max(0, int(delta.total_seconds() // 60))


def cooldown_active(last_suggested_at: str | None, cooldown_minutes: int, *, now: datetime | None = None) -> bool:
    suggested = _parse_iso(last_suggested_at)
    if suggested is None:
        return False
    now = now or datetime.now(UTC)
    return (now - suggested).total_seconds() < cooldown_minutes * 60


def devices_on_in_room(store: DeviceStore, room_id: str) -> list[str]:
    """IDs of devices in a room whose `power` state is true. Devices without
    a power field (curtains, fans driven by `speed`, …) aren't tracked here —
    good enough for the vacancy nudge, not a full occupancy sensor."""
    return [
        device.id
        for device in store.list()
        if device.room == room_id and device.state.get("power") is True
    ]


def part_of_day(hour: int) -> str:
    if 5 <= hour < 11:
        return "morning"
    if 11 <= hour < 14:
        return "noon"
    if 14 <= hour < 18:
        return "afternoon"
    if 18 <= hour < 22:
        return "evening"
    return "night"


def build_ambient_snapshot(
    *,
    rooms: list[dict],
    store: DeviceStore,
    weather: WeatherSnapshot | None,
    tz_name: str,
) -> AmbientSnapshot:
    now_utc = datetime.now(UTC)
    try:
        local_now = now_utc.astimezone(ZoneInfo(tz_name))
    except Exception:
        local_now = now_utc

    room_ambients = [
        RoomAmbient(
            id=room["id"],
            label=room["label"],
            occupied=room["occupied"],
            vacant_minutes=0 if room["occupied"] else vacant_minutes(room["occupancy_changed_at"], now=now_utc),
            indoor_temp_c=room["indoor_temp_c"],
            indoor_humidity=room["indoor_humidity"],
            devices_on=devices_on_in_room(store, room["id"]),
        )
        for room in rooms
    ]
    return AmbientSnapshot(
        ts=now_utc.isoformat(),
        local_time=local_now.strftime("%H:%M"),
        part_of_day=part_of_day(local_now.hour),
        weather=weather,
        rooms=room_ambients,
    )
