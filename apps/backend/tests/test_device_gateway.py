import json
import pytest
from homate.modules.home.application.devices import DeviceStore, InvalidDeviceActionError
from homate.modules.home.application.gateway import DeviceGateway, SimulatorAdapter, DeviceTransportError
from homate.modules.home.domain.defaults import default_devices
from homate.infrastructure.postgres.connection import connect
from homate.infrastructure.postgres.device_gateway import PostgresCommandRepository
from test_software import client, admin


def test_connectivity_is_authenticated_and_uses_database_adapter(client, admin):
    from types import SimpleNamespace
    assert client.get('/api/dashboard/device-connectivity').status_code == 401
    result = client.get('/api/dashboard/device-connectivity', headers=admin).json()
    assert result['light-living'] == {'adapter': 'simulator', 'status': 'online', 'last_seen_at': None}
    original = client.app.state.mqtt_transport
    try:
        with connect(client.app.state.database_url) as conn:
            conn.execute("UPDATE device_connections SET adapter='mqtt' WHERE device_id='light-living'")
        client.app.state.mqtt_transport = SimpleNamespace(connectivity=lambda identifier: {'status': 'offline', 'last_seen_at': 100})
        result = client.get('/api/dashboard/device-connectivity', headers=admin).json()
        assert result['light-living'] == {'adapter': 'mqtt', 'status': 'offline', 'last_seen_at': 100}
    finally:
        client.app.state.mqtt_transport = original
        with connect(client.app.state.database_url) as conn:
            conn.execute("UPDATE device_connections SET adapter='simulator' WHERE device_id='light-living'")


def test_manual_command_is_acknowledged_and_persisted_atomically(client, admin):
    response = client.post('/api/dashboard/devices/light-living/actions', headers=admin, json={'key': 'power', 'value': True})
    assert response.status_code == 200
    with connect(client.app.state.database_url) as conn:
        receipt = conn.execute("SELECT * FROM device_commands WHERE device_id='light-living' ORDER BY created_at DESC LIMIT 1").fetchone()
        state = conn.execute("SELECT state FROM devices WHERE id='light-living'").fetchone()
    assert receipt['status'] == 'succeeded'
    assert receipt['adapter'] == 'simulator'
    assert json.loads(receipt['desired_state']) == json.loads(receipt['reported_state']) == json.loads(state['state'])
    assert receipt['completed_at'] is not None
    history = client.get('/api/dashboard/devices/light-living/commands', headers=admin)
    assert history.status_code == 200
    assert history.json()[0]['reported_state'] == response.json()['device']['state']
    assert client.get('/api/dashboard/devices/light-living/commands').status_code == 401


def test_unsupported_transport_does_not_change_or_broadcast_state(client, admin):
    before = client.app.state.device_store.get('light-living').state
    with connect(client.app.state.database_url) as conn:
        conn.execute("UPDATE device_connections SET adapter='not-installed' WHERE device_id='light-living'")
    try:
        response = client.post('/api/dashboard/devices/light-living/actions', headers=admin, json={'key': 'power', 'value': not before['power']})
        assert response.status_code == 503
        assert client.app.state.device_store.get('light-living').state == before
        with connect(client.app.state.database_url) as conn:
            receipt = conn.execute("SELECT * FROM device_commands WHERE device_id='light-living' ORDER BY created_at DESC LIMIT 1").fetchone()
            state = conn.execute("SELECT state FROM devices WHERE id='light-living'").fetchone()
        assert receipt['status'] == 'failed'
        assert receipt['reported_state'] is None
        assert json.loads(state['state']) == before
    finally:
        with connect(client.app.state.database_url) as conn:
            conn.execute("UPDATE device_connections SET adapter='simulator' WHERE device_id='light-living'")


def test_validation_runs_before_transport_and_reports_do_not_send_commands():
    calls = []
    def dispatch(device):
        calls.append(device)
        return device
    store = DeviceStore(default_devices(), on_command=dispatch)
    with pytest.raises(InvalidDeviceActionError):
        store.apply_action('light-living', 'brightness', 101)
    assert not calls
    store.set_state('light-living', {'power': True})
    assert not calls
    store.apply_action('light-living', 'brightness', 30)
    assert calls[0].state['brightness'] == 30


def test_adapter_failure_and_unacknowledged_states_are_not_published(client):
    class SilentAdapter:
        def execute(self, desired, settings):
            desired.state['power'] = not desired.state['power']
            return desired
    repository = PostgresCommandRepository(client.app.state.database_url)
    gateway = DeviceGateway(repository, {'simulator': SilentAdapter()})
    original = client.app.state.device_store.get('light-living')
    with pytest.raises(DeviceTransportError, match='state_not_acknowledged'):
        gateway.execute(original)
    with connect(client.app.state.database_url) as conn:
        state = conn.execute("SELECT state FROM devices WHERE id='light-living'").fetchone()
    assert json.loads(state['state']) == original.state


def test_restart_interrupts_unfinished_commands_without_replaying(client):
    repository = PostgresCommandRepository(client.app.state.database_url)
    original = client.app.state.device_store.get('light-living')
    identifier = repository.begin(original, 'simulator')
    repository.recover()
    with connect(client.app.state.database_url) as conn:
        row = conn.execute('SELECT status FROM device_commands WHERE id=%s', (identifier,)).fetchone()
    assert row['status'] == 'interrupted'
    assert client.app.state.device_store.get('light-living') == original


def test_startup_preserves_database_adapter_settings(client, monkeypatch):
    from fastapi.testclient import TestClient
    from homate.software_bootstrap import create_app
    from homate.config import get_settings

    repository = PostgresCommandRepository(client.app.state.database_url)
    original = {identifier: repository.connection(identifier) for identifier in ('light-living', 'light-balcony')}
    try:
        with connect(client.app.state.database_url) as conn:
            conn.execute("UPDATE device_connections SET adapter='simulator',settings='{}' WHERE device_id='light-living'")
            conn.execute("""UPDATE device_connections SET adapter='mqtt',settings='{"managed_by":"mqtt-demo"}' WHERE device_id='light-balcony'""")
        configuration = get_settings().model_copy(update={'mqtt_host': ''})
        monkeypatch.setattr('homate.software_bootstrap.get_settings', lambda: configuration)
        # Old demo environment variables must not select or reset adapters.
        monkeypatch.setenv('MQTT_SIMULATED_DEVICE_IDS', 'light-living')
        with TestClient(create_app(client.app.state.database_url, start_workers=False)):
            assert repository.connection('light-living') == ('simulator', {})
            assert repository.connection('light-balcony') == ('mqtt', {'managed_by': 'mqtt-demo'})
    finally:
        with connect(client.app.state.database_url) as conn:
            for identifier, (adapter, settings) in original.items():
                conn.execute('UPDATE device_connections SET adapter=%s,settings=%s WHERE device_id=%s', (adapter, json.dumps(settings), identifier))
