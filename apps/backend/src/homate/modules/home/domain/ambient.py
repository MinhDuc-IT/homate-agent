"""Ambient context schemas — weather (mocked room temp) + occupancy mock."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WeatherSnapshot(BaseModel):
    temp_c: float
    feels_like_c: float
    humidity: int
    condition: str = ""
    description: str = ""
    wind_ms: float = 0.0
    fetched_at: str = ""
    stale: bool = False


class RoomAmbient(BaseModel):
    id: str
    label: str
    occupied: bool
    vacant_minutes: int = 0
    indoor_temp_c: float | None = None
    indoor_humidity: float | None = None
    devices_on: list[str] = Field(default_factory=list)


class AmbientSnapshot(BaseModel):
    ts: str
    local_time: str = ""
    part_of_day: str = ""
    weather: WeatherSnapshot | None = None
    rooms: list[RoomAmbient] = Field(default_factory=list)


class RoomMockPatch(BaseModel):
    """Tab Mock write — set occupancy/indoor temp, or backdate for a demo."""

    occupied: bool | None = None
    indoor_temp_c: float | None = Field(default=None, ge=0, le=60)
    indoor_humidity: float | None = Field(default=None, ge=0, le=100)
    vacant_minutes: int | None = Field(default=None, ge=0, le=1440)
