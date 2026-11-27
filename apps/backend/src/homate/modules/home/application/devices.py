from __future__ import annotations
import threading
from homate.modules.home.domain.conflicts import DeviceConflictError, conflicts_for, off_control
from collections.abc import Callable
from homate.modules.home.domain.defaults import default_devices, mvp_devices
from homate.modules.home.domain.device import (
    ActionControl,
    Device,
    DeviceActionResponse,
    DeviceControl,
    DeviceStateValue,
    EnumControl,
    LevelControl,
    RangeControl,
    StepControl,
    ToggleControl,
)

OnChangeCallback = Callable[[Device], None]

class DeviceNotFoundError(LookupError):
    """Raised when device id is unknown."""

    def __init__(self, device_id: str) -> None:
        self.device_id = device_id
        super().__init__(f"Device not found: {device_id}")

class InvalidDeviceActionError(ValueError):
    """Raised when action key/value is invalid for the device."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)

class DeviceStore:
    """In-memory device catalog with a lock around read/write mutations.

    Safe for concurrent access from the asyncio event loop and threadpool
    workers within a single process. Multi-worker / multi-process deploys
    still need an external shared store (Redis, DB, MQTT state, …).
    """

    def __init__(
        self,
        devices: list[Device] | None = None,
        on_change: OnChangeCallback | None = None,
        conflict_rules: Callable[[], dict] | None = None,
        on_command: Callable[[Device], Device] | None = None,
    ) -> None:
        source = devices if devices is not None else default_devices()
        self._devices: dict[str, Device] = {
            d.id: d.model_copy(deep=True) for d in source
        }
        self._on_change = on_change
        self._on_command = on_command
        self._lock = threading.RLock()
        self._conflict_rules = conflict_rules

    def conflict_rules(self):
        return self._conflict_rules() if self._conflict_rules else {}

    def fork(self):
        """A side-effect-free simulation with the same declared rules."""
        rules = self.conflict_rules()
        return DeviceStore(self.list(), conflict_rules=lambda: rules)

    def validate_commands(self, commands):
        """Validate ordered effects without changing live state."""
        from homate.modules.home.domain.actions import action_writes
        from homate.modules.home.domain.conflicts import active
        sandbox, desired = self.fork(), {}
        for command in commands:
            identifier = command['device_id']
            for key, value in action_writes(sandbox.get(identifier), command['action'], command.get('parameters') or {}):
                sandbox.apply_action(identifier, key, value)
            desired[identifier] = active(sandbox.get(identifier))
        if any(value is True and active(sandbox.get(identifier)) is not True for identifier, value in desired.items()):
            raise ValueError('Kịch bản yêu cầu giữ các thiết bị xung đột cùng bật. Hãy chọn thiết bị muốn dùng.')

    def set_on_change(self, callback: OnChangeCallback | None) -> None:
        with self._lock:
            self._on_change = callback

    def list(self) -> list[Device]:
        with self._lock:
            return [d.model_copy(deep=True) for d in self._devices.values()]

    def get(self, device_id: str) -> Device:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
            return device.model_copy(deep=True)

    def set_state(self, device_id: str, state: dict, *, accept_if: Callable[[], bool] | None = None) -> Device | None:
        """Merge device state keys. Returns None if nothing changed."""
        with self._lock:
            if accept_if is not None and not accept_if():
                return None
            device = self._devices.get(device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
            device = device.model_copy(deep=True)
            changed = False
            for key, value in state.items():
                if device.state.get(key) != value:
                    device.state[key] = value
                    changed = True
            changed = self._synchronize_position_state(device, set(state)) or changed
            if not changed:
                return None
            snapshot = device.model_copy(deep=True)
            if self._on_change is not None:
                self._on_change(snapshot)
            self._devices[device_id] = device

        return snapshot

    def apply_action(
        self,
        device_id: str,
        key: str,
        value: DeviceStateValue | None = None,
    ) -> DeviceActionResponse:
        with self._lock:
            device = self._devices.get(device_id)
            if device is None:
                raise DeviceNotFoundError(device_id)
            device = device.model_copy(deep=True)

            control = self._find_control(device, key)
            if control is None:
                raise InvalidDeviceActionError(
                    f"Unknown control key '{key}' for device '{device_id}'"
                )

            self._assert_when(device, control)

            if isinstance(control, ActionControl):
                changed_key, previous, new_value = self._apply_action_control(
                    device, control, value
                )
            else:
                if value is None:
                    raise InvalidDeviceActionError(
                        f"Control '{key}' requires a value"
                    )
                previous = device.state.get(key)
                new_value = self._coerce_and_validate(control, value)
                device.state[key] = new_value
                changed_key = key

            self._synchronize_position_state(device, {changed_key})
            issues = conflicts_for(device, self._devices, self.conflict_rules())
            blocked = [i for i in issues if i['policy'] != 'auto_off_other' or i['unknown_state']]
            if blocked:
                raise DeviceConflictError(blocked)
            # Validate every automatic shutdown before making the first change.
            shutdowns = [(i['conflicts_with'], off_control(self._devices[i['conflicts_with']])) for i in issues]
            sandbox = DeviceStore(list(self._devices.values()))
            for identifier, (off_key, off_value) in shutdowns:
                sandbox.apply_action(identifier, off_key, off_value)
            related = []
            for identifier, (off_key, off_value) in shutdowns:
                related.append(self.apply_action(identifier, off_key, off_value).device)
            snapshot = device.model_copy(deep=True)
            # Publish the new state only after the persistence callback succeeds.
            if self._on_command is not None:
                snapshot = self._on_command(snapshot)
                device = snapshot.model_copy(deep=True)
                new_value = snapshot.state.get(changed_key)
            elif self._on_change is not None:
                self._on_change(snapshot)
            self._devices[device_id] = device

        return DeviceActionResponse(
            device=snapshot,
            related_devices=related,
            changed_key=changed_key,
            previous_value=previous,
            new_value=new_value,
        )

    @staticmethod
    def _find_control(device: Device, key: str) -> DeviceControl | None:
        for control in device.controls:
            if control.key == key:
                return control
        return None

    @staticmethod
    def _synchronize_position_state(device: Device, changed_keys: set[str]) -> bool:
        """Keep a positional device's coarse preset consistent with its position."""
        if "position" not in device.state or "preset" not in device.state:
            return False

        position_control = next(
            (
                control
                for control in device.controls
                if control.key == "position"
                and isinstance(control, (RangeControl, StepControl))
            ),
            None,
        )
        preset_control = next(
            (
                control
                for control in device.controls
                if control.key == "preset" and isinstance(control, EnumControl)
            ),
            None,
        )
        if position_control is None or preset_control is None:
            return False
        minimum = position_control.min
        maximum = position_control.max
        presets = {option.value for option in preset_control.options}

        changed = False
        position = device.state.get("position")
        preset = device.state.get("preset")

        # A numeric position is authoritative when both fields arrive together.
        if (
            "position" in changed_keys
            and isinstance(position, (int, float))
            and not isinstance(position, bool)
        ):
            derived = (
                "closed"
                if position <= minimum
                else "open"
                if position >= maximum
                else "ajar"
            )
            if derived in presets and preset != derived:
                device.state["preset"] = derived
                changed = True
            return changed

        if "preset" not in changed_keys:
            return changed
        target = {"closed": minimum, "open": maximum}.get(str(preset))
        if preset == "ajar" and not (
            isinstance(position, (int, float))
            and not isinstance(position, bool)
            and minimum < position < maximum
        ):
            midpoint = (minimum + maximum) / 2
            target = int(midpoint) if midpoint.is_integer() else midpoint
        if target is not None and position != target:
            device.state["position"] = target
            changed = True
        return changed

    @staticmethod
    def _assert_when(device: Device, control: DeviceControl) -> None:
        when = control.when
        if not when:
            return
        for state_key, expected in when.items():
            actual = device.state.get(state_key)
            if actual != expected:
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' unavailable: "
                    f"requires {state_key}={expected!r}, got {actual!r}"
                )

    @staticmethod
    def _apply_action_control(
        device: Device,
        control: ActionControl,
        value: DeviceStateValue | None,
    ) -> tuple[str, DeviceStateValue | None, DeviceStateValue | None]:
        """Map action controls onto state fields (lock / unlock → locked)."""
        if control.key == "unlock":
            if value is not None and value is not True:
                raise InvalidDeviceActionError(
                    "unlock only accepts value=true or omitted"
                )
            previous = device.state.get("locked")
            device.state["locked"] = False
            return "locked", previous, False
        if control.key == "lock":
            if value is not None and value is not True:
                raise InvalidDeviceActionError(
                    "lock only accepts value=true or omitted"
                )
            previous = device.state.get("locked")
            device.state["locked"] = True
            return "locked", previous, True

        raise InvalidDeviceActionError(
            f"Action '{control.key}' is not implemented yet"
        )

    @staticmethod
    def _coerce_and_validate(
        control: DeviceControl,
        value: DeviceStateValue,
    ) -> DeviceStateValue:
        if isinstance(control, ToggleControl):
            if not isinstance(value, bool):
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' expects bool, got {type(value).__name__}"
                )
            return value

        if isinstance(control, (RangeControl, StepControl)):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' expects number, got {type(value).__name__}"
                )
            numeric = float(value)
            if numeric < control.min or numeric > control.max:
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' value {numeric} "
                    f"out of range [{control.min}, {control.max}]"
                )
            # Prefer int when step is int-like and value is whole
            if isinstance(value, int) or numeric.is_integer():
                return int(numeric)
            return numeric

        if isinstance(control, EnumControl):
            allowed = {opt.value for opt in control.options}
            if not isinstance(value, str) or value not in allowed:
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' expects one of {sorted(allowed)}, "
                    f"got {value!r}"
                )
            return value

        if isinstance(control, LevelControl):
            if not isinstance(value, int) or isinstance(value, bool):
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' expects int level, got {type(value).__name__}"
                )
            if value not in control.levels:
                raise InvalidDeviceActionError(
                    f"Control '{control.key}' expects one of {control.levels}, "
                    f"got {value}"
                )
            return value

        raise InvalidDeviceActionError(
            f"Unsupported control type for '{control.key}'"
        )
