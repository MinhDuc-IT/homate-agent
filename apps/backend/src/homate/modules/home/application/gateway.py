"""Transport boundary. Validation and conflict policy run before this module.

The first adapter acknowledges immediately. Physical transports must return an
actual device report, not treat a successful send as successful execution.
"""
from typing import Protocol
from homate.modules.home.domain.device import Device


class DeviceTransportError(RuntimeError):
    pass


class DeviceAdapter(Protocol):
    def execute(self, desired: Device, settings: dict) -> Device: ...


class CommandRepository(Protocol):
    def connection(self, device_id: str) -> tuple[str, dict]: ...
    def begin(self, desired: Device, adapter: str) -> str: ...
    def succeed(self, command_id: str, reported: Device) -> None: ...
    def fail(self, command_id: str, reason: str) -> None: ...


class SimulatorAdapter:
    """Deterministic virtual device: apply and acknowledge the requested state."""
    def execute(self, desired: Device, settings: dict) -> Device:
        return desired.model_copy(deep=True)


class DeviceGateway:
    def __init__(self, repository: CommandRepository, adapters: dict[str, DeviceAdapter]):
        self.repository = repository
        self.adapters = dict(adapters)

    def execute(self, desired: Device) -> Device:
        adapter_name, settings = self.repository.connection(desired.id)
        identifier = self.repository.begin(desired, adapter_name)
        adapter = self.adapters.get(adapter_name)
        try:
            if adapter is None:
                raise DeviceTransportError('unsupported_transport')
            reported = adapter.execute(desired.model_copy(deep=True), {**settings, '_command_id': identifier})
            if reported.id != desired.id or reported.state != desired.state:
                raise DeviceTransportError('state_not_acknowledged')
            # State and success receipt commit together. Never publish before this.
            self.repository.succeed(identifier, reported)
        except Exception as error:
            reason = str(error) if isinstance(error, DeviceTransportError) else 'transport_failed'
            self.repository.fail(identifier, reason)
            raise DeviceTransportError(reason) from error
        return reported
