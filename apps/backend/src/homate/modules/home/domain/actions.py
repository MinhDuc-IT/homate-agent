from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from homate.modules.home.domain.device import ActionControl, Device, DeviceControl, EnumControl, LevelControl, RangeControl, StepControl, ToggleControl

def level_off_control(device: Device) -> LevelControl | None:
    """First level control where 0 means off and a positive level exists."""
    for control in device.controls:
        if isinstance(control, LevelControl) and 0 in control.levels and any((level > 0 for level in control.levels)):
            return control
    return None

def has_power_toggle(device: Device) -> bool:
    return any((isinstance(control, ToggleControl) and control.key == 'power' for control in device.controls))

def resolve_turn_on_off(device: Device, action: str) -> tuple[str, Any] | None:
    """Map turn_on/turn_off to a concrete state write.

    Power-toggle devices flip ``power``. Level-off devices (fans with nút 0/1/2…)
    use the level key: off→0, on→lowest positive level.
    """
    if action not in {'turn_on', 'turn_off'}:
        return None
    if has_power_toggle(device):
        return ('power', action == 'turn_on')
    control = level_off_control(device)
    if control is None:
        return None
    if action == 'turn_off':
        return (control.key, 0)
    positive = min((level for level in control.levels if level > 0))
    return (control.key, positive)


def action_writes(device: Device, action: str, parameters: dict) -> list[tuple[str, Any]]:
    """Map configured scene/schedule actions to concrete device controls."""
    keys = {control.key for control in device.controls}
    if action in {"turn_on", "turn_off"}:
        mapped = resolve_turn_on_off(device, action)
        if mapped is None: raise ValueError(f"{device.name} không hỗ trợ {action}")
        return [mapped]
    if action in {"lock", "unlock"} and action in keys: return [(action, True)]
    if action in {"open", "close"}:
        writes = []
        if "preset" in keys: writes.append(("preset", "open" if action == "open" else "closed"))
        if "position" in keys: writes.append(("position", 100 if action == "open" else 0))
        if writes: return writes
    if action in {"start_recording", "stop_recording"} and "recording" in keys:
        return [("recording", action == "start_recording")]
    if action.startswith("set_"):
        key = action[4:]
        if key in keys:
            defaults = {"brightness": 60, "temperature": 26, "speed": 1}
            value = parameters.get(key, defaults.get(key))
            if value is None: raise ValueError(f"Hành động {action} cần tham số {key}")
            writes = [("power", True)] if key in {"brightness", "temperature", "volume"} and "power" in keys else []
            return writes + [(key, value)]
    if action in keys: return [(action, True)]
    raise ValueError(f"{device.name} không hỗ trợ {action}")
