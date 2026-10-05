"""Initial PostgreSQL catalog (immutable schema snapshot)."""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE homes (
            id UUID PRIMARY KEY, name VARCHAR(120) NOT NULL,
            timezone VARCHAR(80) NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE rooms (
            id UUID PRIMARY KEY, name VARCHAR(120) NOT NULL,
            home_id UUID NOT NULL REFERENCES homes(id) ON DELETE RESTRICT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(id, home_id), UNIQUE(home_id, name)
        );
        CREATE INDEX ix_rooms_home_id ON rooms(home_id);
        CREATE TABLE devices (
            id UUID PRIMARY KEY, name VARCHAR(120) NOT NULL,
            home_id UUID NOT NULL REFERENCES homes(id) ON DELETE RESTRICT,
            room_id UUID NOT NULL, kind VARCHAR(40) NOT NULL,
            capabilities JSONB NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            FOREIGN KEY(room_id, home_id) REFERENCES rooms(id, home_id) ON DELETE RESTRICT,
            UNIQUE(id, home_id), UNIQUE(home_id, name)
        );
        CREATE INDEX ix_devices_home_id ON devices(home_id);
        CREATE TABLE scenes (
            id UUID PRIMARY KEY, name VARCHAR(120) NOT NULL,
            home_id UUID NOT NULL REFERENCES homes(id) ON DELETE RESTRICT,
            is_enabled BOOLEAN NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(id, home_id), UNIQUE(home_id, name)
        );
        CREATE INDEX ix_scenes_home_id ON scenes(home_id);
        CREATE TABLE scene_steps (
            id UUID PRIMARY KEY, scene_id UUID NOT NULL, home_id UUID NOT NULL,
            device_id UUID NOT NULL, position INTEGER NOT NULL,
            action VARCHAR(80) NOT NULL, parameters JSONB NOT NULL,
            FOREIGN KEY(scene_id, home_id) REFERENCES scenes(id, home_id) ON DELETE CASCADE,
            FOREIGN KEY(device_id, home_id) REFERENCES devices(id, home_id) ON DELETE RESTRICT,
            UNIQUE(scene_id, position)
        );
    """)


def downgrade():
    for table in ("scene_steps", "scenes", "devices", "rooms", "homes"):
        op.drop_table(table)
