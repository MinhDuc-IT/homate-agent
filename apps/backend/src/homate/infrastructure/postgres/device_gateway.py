import json
from uuid import uuid4
from homate.infrastructure.postgres.connection import connect
from homate.modules.home.application.gateway import DeviceTransportError


class PostgresCommandRepository:
    def __init__(self, database_url):
        self.database_url = database_url

    def connection(self, device_id):
        with connect(self.database_url) as conn:
            row = conn.execute('SELECT adapter, settings FROM device_connections WHERE device_id=%s', (device_id,)).fetchone()
        if not row:
            raise DeviceTransportError('missing_connection')
        return row['adapter'], json.loads(row['settings'])

    def begin(self, desired, adapter):
        identifier = str(uuid4())
        with connect(self.database_url) as conn:
            conn.execute('''INSERT INTO device_commands(id, device_id, adapter, desired_state, status)
                VALUES (%s,%s,%s,%s,'processing')''', (identifier, desired.id, adapter, json.dumps(desired.state)))
        return identifier

    def succeed(self, identifier, reported):
        payload = json.dumps(reported.state)
        with connect(self.database_url) as conn:
            conn.execute('UPDATE devices SET state=%s, last_seen_at=now(), updated_at=now() WHERE id=%s', (payload, reported.id))
            conn.execute("UPDATE device_commands SET status='succeeded', reported_state=%s, completed_at=now() WHERE id=%s", (payload, identifier))

    def fail(self, identifier, reason):
        with connect(self.database_url) as conn:
            conn.execute("UPDATE device_commands SET status='failed', error=%s, completed_at=now() WHERE id=%s", (reason, identifier))

    def recover(self):
        # Single backend worker, same deployment restriction as DeviceStore.
        with connect(self.database_url) as conn:
            conn.execute('''INSERT INTO device_connections(device_id) SELECT id FROM devices ON CONFLICT DO NOTHING''')
            conn.execute("UPDATE device_commands SET status='interrupted', error='backend_restarted', completed_at=now() WHERE status='processing'")

    def list(self, home_id, device_id):
        with connect(self.database_url) as conn:
            rows = conn.execute('''SELECT c.* FROM device_commands c JOIN devices d ON d.id=c.device_id
                WHERE d.home_id=%s AND c.device_id=%s ORDER BY c.created_at DESC LIMIT 20''', (home_id, device_id)).fetchall()
        return [{**row, 'desired_state': json.loads(row['desired_state']),
                 'reported_state': json.loads(row['reported_state']) if row['reported_state'] is not None else None} for row in rows]
