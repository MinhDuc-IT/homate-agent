"""Device transports and durable command receipts."""
from alembic import op

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        CREATE TABLE homate.device_connections (
            device_id TEXT PRIMARY KEY REFERENCES homate.devices(id) ON DELETE CASCADE,
            adapter TEXT NOT NULL DEFAULT 'simulator',
            settings JSONB NOT NULL DEFAULT '{}'
        );
        INSERT INTO homate.device_connections(device_id) SELECT id FROM homate.devices;
        CREATE TABLE homate.device_commands (
            id UUID PRIMARY KEY,
            device_id TEXT NOT NULL REFERENCES homate.devices(id) ON DELETE CASCADE,
            adapter TEXT NOT NULL,
            desired_state JSONB NOT NULL,
            reported_state JSONB,
            status TEXT NOT NULL CHECK(status IN ('processing','succeeded','failed','interrupted')),
            error TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ
        );
        CREATE INDEX device_commands_device_created ON homate.device_commands(device_id, created_at DESC);
    ''')


def downgrade():
    op.execute('DROP TABLE homate.device_commands; DROP TABLE homate.device_connections;')
