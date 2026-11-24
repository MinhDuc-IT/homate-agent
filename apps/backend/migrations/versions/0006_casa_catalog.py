"""Align the demo house with CASA; preserve device IDs and historical records."""
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from alembic import op
from sqlalchemy import text

revision = '0006'
down_revision = '0005'
branch_labels = depends_on = None


def upgrade():
    conn = op.get_bind()
    op.execute('''
        ALTER TABLE homate.devices ADD CONSTRAINT devices_id_home_unique UNIQUE(id, home_id);
        CREATE TABLE homate.device_simulation_bindings (
            device_id TEXT PRIMARY KEY,
            home_id TEXT NOT NULL,
            scene_id TEXT NOT NULL,
            object_name TEXT NOT NULL,
            source_ref TEXT NOT NULL,
            binding_kind TEXT NOT NULL,
            FOREIGN KEY(device_id, home_id) REFERENCES homate.devices(id, home_id) ON DELETE CASCADE,
            UNIQUE(home_id, scene_id, source_ref)
        );
        CREATE TABLE homate.simulation_catalog_migrations (
            home_id TEXT NOT NULL REFERENCES homate.homes(id),
            revision TEXT NOT NULL, backup JSONB NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY(home_id, revision)
        );
    ''')
    # Immutable snapshot: later changes to runtime defaults must not change this migration.
    spec = json.loads((Path(__file__).parents[1] / 'data/0006_casa_catalog.json').read_text(encoding='utf-8'))
    home = spec['home_id']
    if not conn.execute(text('SELECT 1 FROM homate.homes WHERE id=:home'), {'home': home}).first():
        return  # A new installation is populated by the current seed after migrations.
    active = conn.execute(text('''SELECT 1 FROM homate.agent_plans p
        JOIN homate.agent_sessions s ON s.id=p.session_id
        WHERE s.home_id=:home AND p.status='executing' LIMIT 1'''), {'home': home}).first()
    if active:
        raise RuntimeError('Finish executing agent plans before changing the demo catalog.')
    conn.execute(text('''INSERT INTO homate.simulation_catalog_migrations(home_id,revision,backup)
        SELECT :home, '0006', jsonb_build_object(
            'rooms', (SELECT coalesce(jsonb_agg(to_jsonb(r)), '[]'::jsonb) FROM homate.rooms r WHERE home_id=:home),
            'devices', (SELECT coalesce(jsonb_agg(to_jsonb(d)), '[]'::jsonb) FROM homate.devices d WHERE home_id=:home),
            'aliases', (SELECT coalesce(jsonb_agg(to_jsonb(a)), '[]'::jsonb) FROM homate.device_aliases a
                JOIN homate.devices d ON d.id=a.device_id WHERE d.home_id=:home))'''), {'home': home})

    for identifier, label, order in spec['rooms']:
        conn.execute(text('''INSERT INTO homate.rooms(id,home_id,label,sort_order)
            VALUES (:id,:home,:label,:sort) ON CONFLICT(id,home_id)
            DO UPDATE SET label=EXCLUDED.label, sort_order=EXCLUDED.sort_order'''),
            {'id': identifier, 'home': home, 'label': label, 'sort': order})

    # Both old zones physically belong to the living area. Keep device identities and state.
    conn.execute(text('''UPDATE homate.devices SET room_id='living', updated_at=now(),
        mqtt_topic=CASE WHEN hardware_uid LIKE 'mock:%'
            THEN regexp_replace(mqtt_topic, '^home/(office|balcony)/', 'home/living/') ELSE mqtt_topic END
        WHERE home_id=:home AND room_id IN ('office','balcony')'''), {'home': home})
    for table in ('energy_hourly', 'energy_daily'):
        conn.execute(text(f'''UPDATE homate.{table} SET room_id='living'
            WHERE home_id=:home AND room_id IN ('office','balcony')'''), {'home': home})
    conn.execute(text("DELETE FROM homate.rooms WHERE home_id=:home AND id IN ('office','balcony')"), {'home': home})

    kinds = {'bulb':'light', 'snowflake':'ac', 'flame':'heater', 'droplet':'water_heater'}
    old = {d['id']: d for d in spec['legacy_devices']}
    for device in spec['devices']:
        identifier = device['id']
        params = dict(home=home, id=identifier, name=device['name'], room=device['room'], kind=device['kind'],
            device_type=kinds.get(device['kind'], device['kind']), state=json.dumps(device['state']),
            capabilities=json.dumps(device['controls']), hardware=f'mock:{identifier}')
        params['topic'] = f"home/{device['room']}/{params['device_type']}/{identifier}"
        conn.execute(text('''INSERT INTO homate.devices
            (id,home_id,room_id,hardware_uid,protocol,mqtt_topic,name,kind,device_type,capabilities,state,
             online,paired_at,last_seen_at,created_at,updated_at)
            VALUES (:id,:home,:room,:hardware,'mqtt',:topic,:name,:kind,:device_type,
                CAST(:capabilities AS JSONB),CAST(:state AS JSONB),1,now(),now(),now(),now())
            ON CONFLICT(id) DO NOTHING'''), params)
        if identifier in old and old[identifier]['name'] != device['name']:
            # Preserve custom names. Only replace the original demo names and their generated aliases.
            old_name = old[identifier]['name']
            changed = conn.execute(text('''UPDATE homate.devices SET name=:name,updated_at=now()
                WHERE id=:id AND home_id=:home AND name=:old'''), {**params, 'old': old_name})
            if changed.rowcount:
                conn.execute(text('''DELETE FROM homate.device_aliases
                    WHERE device_id=:id AND alias=:alias'''), {'id': identifier, 'alias': old_name.lower()})
        actual_name = conn.execute(text('SELECT name FROM homate.devices WHERE id=:id AND home_id=:home'), params).scalar_one()
        alias = actual_name.lower()
        conn.execute(text('''INSERT INTO homate.device_aliases(id,device_id,alias)
            SELECT :alias_id,:id,:alias WHERE NOT EXISTS
                (SELECT 1 FROM homate.device_aliases WHERE device_id=:id AND alias=:alias)'''),
            {'alias_id': str(uuid5(NAMESPACE_URL, f'homate:alias:{identifier}:{alias}')), 'id': identifier, 'alias': alias})

    for binding in spec['bindings']:
        conn.execute(text('''INSERT INTO homate.device_simulation_bindings
            (device_id,home_id,scene_id,object_name,source_ref,binding_kind)
            VALUES (:device_id,:home,:scene,:object_name,:source_ref,:binding_kind)'''),
            {**binding, 'home': home, 'scene': spec['scene_id']})
    # These aliases used to identify a single device. They are ambiguous now
    # that lights and blinds are represented as independent groups.
    for identifier, aliases in spec['removed_aliases'].items():
        for alias in aliases:
            conn.execute(text('''DELETE FROM homate.device_aliases WHERE device_id=:id AND alias=:alias
                AND device_id IN (SELECT id FROM homate.devices WHERE home_id=:home)'''),
                {'id': identifier, 'alias': alias, 'home': home})
    # Old pending confirmations may describe a different room or old device name.
    conn.execute(text('''UPDATE homate.agent_plans SET status='cancelled',updated_at=now(),
        result='{"code":"catalog_changed"}'::jsonb WHERE status='pending' AND session_id IN
        (SELECT id FROM homate.agent_sessions WHERE home_id=:home)'''), {'home': home})
    conn.execute(text('''UPDATE homate.agent_actions SET status='expired' WHERE home_id=:home AND status='pending' '''), {'home': home})


def downgrade():
    raise RuntimeError('This data migration is forward-only. Restore the pre-migration database backup to revert the catalog.')
