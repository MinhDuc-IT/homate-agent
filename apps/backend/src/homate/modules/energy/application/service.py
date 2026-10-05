from typing import Protocol


class EnergyRepository(Protocol):
    def report(self, **filters) -> dict: ...
    def record(self, device, **options) -> None: ...
    def record_all(self, devices) -> None: ...
    def aggregate_daily_and_cleanup(self, **options) -> dict: ...


class EnergyService:
    def __init__(self, repository: EnergyRepository): self.repository = repository
    def report(self, **filters): return self.repository.report(**filters)
    def record(self, device, **options): return self.repository.record(device, **options)
    def record_all(self, devices): return self.repository.record_all(devices)
    def aggregate_daily_and_cleanup(self, **options): return self.repository.aggregate_daily_and_cleanup(**options)
