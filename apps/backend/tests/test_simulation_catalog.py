import ast
from pathlib import Path
import re
import json
import os
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from homate.infrastructure.postgres import household
from homate.infrastructure.postgres.connection import connect
from homate.modules.home.domain.defaults import default_devices
from homate.modules.home.domain.simulation_catalog import BINDINGS, ROOMS
from test_software import client, admin


def test_bound_devices_identify_real_scene_objects():
    scene = Path(__file__).resolve().parents[3] / 'apps/unity-sim/Assets/Scenes/CASA.unity'
    text = scene.read_text(encoding='utf-8')
    blocks = {re.search(r'&(\d+)', b)[1]: b for b in re.split(r'^--- ', text, flags=re.M) if b.startswith('!u!')}

    def decode(value):
        return ast.literal_eval(value) if value.startswith('"') else value

    def prefab_name(block):
        return decode(re.search(r'propertyPath: m_Name\s+value: (.*)', block)[1])

    devices = {d.id: d for d in default_devices()}
    assert len(devices) == 37
    assert {d.room for d in devices.values()} == {r[0] for r in ROOMS}
    assert len({ref for _, _, ref, _ in BINDINGS}) == len(BINDINGS) == 27
    assert sum(kind == 'light' for *_, kind in BINDINGS) == 13
    assert sum(kind == 'curtain' for *_, kind in BINDINGS) == 5
    for identifier, name, source_ref, _ in BINDINGS:
        assert identifier in devices
        kind, ref = source_ref.split(':')
        block = blocks[ref]
        if kind == 'prefab_instance':
            assert block.startswith('!u!1001 ')
            actual_name = prefab_name(block)
        else:
            assert block.startswith('!u!1 ')
            named = re.search(r'^  m_Name: (.+)', block, re.M)
            if named:
                actual_name = decode(named[1])
            else:
                instance = re.search(r'm_PrefabInstance: \{fileID: (\d+)\}', block)[1]
                actual_name = prefab_name(blocks[instance])
        assert actual_name == name, (identifier, actual_name, name)


def test_authenticated_catalog_distinguishes_mapping_from_state_sync(client, admin):
    assert client.get('/api/dashboard/simulation').status_code == 401
    result = client.get('/api/dashboard/simulation', headers=admin).json()
    assert result['scene_id'] == 'casa' and result['device_sync'] is False
    assert len(result['devices']) == 37
    assert sum(d['model_status'] == 'mapped' for d in result['devices']) == 27
    ac = next(d for d in result['devices'] if d['device_id'] == 'ac-living')
    assert ac['model_status'] == 'unmapped' and ac['source_ref'] is None
    aliases = household.load_device_aliases(client.app.state.database_url)
    assert 'rèm' not in aliases['curtain']
    assert 'đèn phòng khách' not in aliases['light-living']


def test_legacy_migration_preserves_state_history_and_references():
    url = os.environ.get('TEST_DATABASE_URL')
    if not url: pytest.skip('Set TEST_DATABASE_URL to a disposable PostgreSQL test server')
    database = 'homate_test_casa_' + uuid4().hex
    scoped = make_url(url).set(database=database).render_as_string(hide_password=False)
    base_dsn = url.replace('postgresql+psycopg://', 'postgresql://')
    with psycopg.connect(base_dsn, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(database)))
    previous = os.environ.get('DATABASE_URL')
    os.environ['DATABASE_URL'] = scoped
    try:
        command.upgrade(Config('alembic.ini'), '0005')
        snapshot = json.loads((Path(__file__).parents[1] / 'migrations/data/0006_casa_catalog.json').read_text(encoding='utf-8'))
        with connect(scoped) as conn:
            household._seed(conn)
            legacy = snapshot['legacy_devices']
            conn.execute('DELETE FROM devices WHERE id <> ALL(%s)', ([d['id'] for d in legacy],))
            conn.execute("INSERT INTO rooms(id,home_id,label) VALUES ('office',%s,'Office'),('balcony',%s,'Balcony')", (household.HOME_ID, household.HOME_ID))
            for device in legacy:
                conn.execute('UPDATE devices SET name=%s,room_id=%s WHERE id=%s', (device['name'], device['room'], device['id']))
            conn.execute("UPDATE devices SET state=%s,mqtt_topic='home/office/light/light-office' WHERE id='light-office'", (json.dumps({'power': True, 'brightness': 81}),))
            conn.execute("UPDATE devices SET name='Custom sofa light' WHERE id='light-living'")
            conn.execute("INSERT INTO device_aliases(id,device_id,alias) VALUES ('custom-alias','light-office','custom desk alias')")
            for table, period in [('energy_daily', "local_date"), ('energy_hourly', 'bucket_start')]:
                value = '2026-01-01' if period == 'local_date' else '2026-01-01T00:00:00Z'
                conn.execute(f'''INSERT INTO {table}(home_id,device_id,room_id,{period},energy_wh,updated_at)
                    VALUES (%s,'light-office','office',%s,123.5,now())''', (household.HOME_ID, value))
            conn.execute('''INSERT INTO scene_steps(id,scene_id,sort_order,device_id,action,parameters)
                SELECT 'migration-step',id,100,'light-office','turn_on','{}' FROM scenes LIMIT 1''')
            conn.execute('''INSERT INTO schedules(id,home_id,name,schedule_type,target_type,device_id,action,
                created_by,run_at,next_run_at,created_at,updated_at)
                VALUES ('migration-schedule',%s,'Preserved schedule','once','device_action','light-office',
                'turn_on','minh-duc',now()+interval '1 year',now()+interval '1 year',now(),now())''', (household.HOME_ID,))
        command.upgrade(Config('alembic.ini'), 'head')
        household.init_and_seed(scoped)
        household.init_and_seed(scoped)
        with connect(scoped) as conn:
            assert {r['id'] for r in conn.execute('SELECT id FROM rooms')} == {'living', 'bed', 'kitchen', 'bath'}
            assert conn.execute('SELECT count(*) AS n FROM devices').fetchone()['n'] == 37
            assert conn.execute('SELECT count(*) AS n FROM device_simulation_bindings').fetchone()['n'] == 27
            row = conn.execute("SELECT * FROM devices WHERE id='light-office'").fetchone()
            assert row['room_id'] == 'living' and row['name'] == 'Đèn phòng khách 4'
            assert json.loads(row['state'])['brightness'] == 81
            assert row['mqtt_topic'] == 'home/living/light/light-office'
            assert conn.execute("SELECT name FROM devices WHERE id='light-living'").fetchone()['name'] == 'Custom sofa light'
            assert conn.execute("SELECT 1 FROM device_aliases WHERE alias='custom desk alias'").fetchone()
            for table in ('energy_daily', 'energy_hourly'):
                row = conn.execute(f"SELECT energy_wh,room_id FROM {table} WHERE device_id='light-office' AND energy_wh=123.5").fetchone()
                assert row['energy_wh'] == 123.5 and row['room_id'] == 'living'
            assert conn.execute("SELECT device_id FROM scene_steps WHERE id='migration-step'").fetchone()['device_id'] == 'light-office'
            assert conn.execute("SELECT device_id FROM schedules WHERE id='migration-schedule'").fetchone()['device_id'] == 'light-office'
            backup = json.loads(conn.execute('SELECT backup FROM simulation_catalog_migrations').fetchone()['backup'])
            assert len(backup['rooms']) == 6 and len(backup['devices']) == 22
    finally:
        if previous is None: os.environ.pop('DATABASE_URL', None)
        else: os.environ['DATABASE_URL'] = previous
        with psycopg.connect(base_dsn, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(database)))
