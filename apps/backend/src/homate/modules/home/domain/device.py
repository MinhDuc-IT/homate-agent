"""Device schemas — aligned with frontend/src/types/device.ts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ---- Shared types ----

DeviceStateValue = bool | int | float | str
DeviceState = dict[str, DeviceStateValue]

DeviceIconKind = Literal[
    "bulb",
    "snowflake",
    "flame",
    "lock",
    "curtain",
    "speaker",
    "tv",
    "fan",
    "plug",
    "camera",
    "droplet",
]

RoomId = Literal["living", "bed", "kitchen", "bath", "office", "balcony"]

ActionVariant = Literal["primary", "danger"]


# ---- Controls (discriminated union on `type`) ----


class EnumOption(BaseModel):
    value: str
    label: str


class ToggleControl(BaseModel):
    type: Literal["toggle"] = "toggle"
    key: str
    label: str
    when: DeviceState | None = None


class RangeControl(BaseModel):
    type: Literal["range"] = "range"
    key: str
    label: str
    min: float
    max: float
    step: float | None = None
    unit: str | None = None
    when: DeviceState | None = None


class StepControl(BaseModel):
    type: Literal["step"] = "step"
    key: str
    label: str
    min: float
    max: float
    step: float | None = None
    unit: str | None = None
    when: DeviceState | None = None


class EnumControl(BaseModel):
    type: Literal["enum"] = "enum"
    key: str
    label: str
    options: list[EnumOption]
    when: DeviceState | None = None


class LevelControl(BaseModel):
    type: Literal["level"] = "level"
    key: str
    label: str
    levels: list[int]
    labels: list[str]
    when: DeviceState | None = None


class ActionControl(BaseModel):
    type: Literal["action"] = "action"
    key: str
    label: str
    variant: ActionVariant | None = None
    sensitive: bool = False
    when: DeviceState | None = None


DeviceControl = Annotated[
    ToggleControl
    | RangeControl
    | StepControl
    | EnumControl
    | LevelControl
    | ActionControl,
    Field(discriminator="type"),
]


# ---- Device ----


class Device(BaseModel):
    id: str
    name: str
    room: RoomId
    kind: DeviceIconKind
    state: DeviceState
    controls: list[DeviceControl]


# ---- REST action ----


class DeviceActionRequest(BaseModel):
    """Apply a control change to a device.

    For toggle/range/step/enum/level: provide `key` + `value`.
    For action controls (e.g. unlock): `key` only; `value` optional.
    """

    key: str = Field(..., min_length=1, description="Control key, e.g. power, brightness")
    value: DeviceStateValue | None = Field(
        default=None,
        description="New state value; optional for action-type controls",
    )


class DeviceActionResponse(BaseModel):
    device: Device
    changed_key: str
    previous_value: DeviceStateValue | None = None
    new_value: DeviceStateValue | None = None


# ---- WebSocket messages ----


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WsSnapshotMessage(BaseModel):
    type: Literal["snapshot"] = "snapshot"
    devices: list[Device]
    ts: datetime = Field(default_factory=utc_now)


class WsDeviceUpdatedMessage(BaseModel):
    type: Literal["device.updated"] = "device.updated"
    device_id: str
    state: DeviceState
    ts: datetime = Field(default_factory=utc_now)


class WsPingMessage(BaseModel):
    type: Literal["ping"] = "ping"
    ts: datetime = Field(default_factory=utc_now)


WsMessage = WsSnapshotMessage | WsDeviceUpdatedMessage | WsPingMessage
