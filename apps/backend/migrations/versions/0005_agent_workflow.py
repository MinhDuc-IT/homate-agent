"""Durable dialogue turns and versioned execution plans."""
from alembic import op

revision = '0005'
down_revision = '0004'
branch_labels = depends_on = None


def upgrade():
    op.execute('''
    CREATE TABLE homate.agent_sessions (
        id UUID PRIMARY KEY, home_id TEXT NOT NULL REFERENCES homate.homes(id),
        user_id TEXT NOT NULL REFERENCES homate.users(id), version INTEGER NOT NULL DEFAULT 0,
        plan_version INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'idle' CHECK(status IN ('idle','clarifying','pending','executing')),
        state JSONB NOT NULL DEFAULT '{}', messages JSONB NOT NULL DEFAULT '[]',
        busy_request UUID, busy_lease UUID, busy_until TIMESTAMPTZ, expires_at TIMESTAMPTZ NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE INDEX agent_sessions_owner ON homate.agent_sessions(user_id,home_id);
    CREATE TABLE homate.agent_turns (
        request_id UUID NOT NULL, user_id TEXT NOT NULL REFERENCES homate.users(id),
        session_id UUID NOT NULL REFERENCES homate.agent_sessions(id), input_hash TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('processing','completed','failed')),
        base_version INTEGER NOT NULL, response JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(user_id,request_id)
    );
    CREATE TABLE homate.agent_plans (
        id UUID PRIMARY KEY, session_id UUID NOT NULL REFERENCES homate.agent_sessions(id),
        version INTEGER NOT NULL, summary TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN
          ('pending','executing','executed','failed','rejected','expired','superseded','cancelled')),
        expires_at TIMESTAMPTZ NOT NULL, result JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE(session_id,version)
    );
    CREATE TABLE homate.agent_plan_steps (
        plan_id UUID NOT NULL REFERENCES homate.agent_plans(id), ordinal INTEGER NOT NULL,
        tool TEXT NOT NULL, arguments JSONB NOT NULL, prepared JSONB NOT NULL,
        summary TEXT NOT NULL, depends_on JSONB NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','running','succeeded','failed','skipped')),
        result JSONB, updated_at TIMESTAMPTZ NOT NULL DEFAULT now(), PRIMARY KEY(plan_id,ordinal)
    );
    ''')


def downgrade():
    op.execute('DROP TABLE homate.agent_plan_steps, homate.agent_plans, homate.agent_turns, homate.agent_sessions')
