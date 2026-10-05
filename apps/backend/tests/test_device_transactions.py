import pytest
from homate.modules.home.application.devices import DeviceStore


def test_failed_persistence_does_not_publish_new_device_state():
    def fail(device): raise RuntimeError("Database unavailable")
    store = DeviceStore(on_change=fail)
    before = store.get("light-living").state
    with pytest.raises(RuntimeError): store.apply_action("light-living", "power", not before["power"])
    assert store.get("light-living").state == before
    with pytest.raises(RuntimeError): store.set_state("light-living", {"brightness": 90})
    assert store.get("light-living").state == before
