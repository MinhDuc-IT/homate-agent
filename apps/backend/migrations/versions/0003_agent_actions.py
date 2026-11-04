"""Durable, user-bound agent confirmations and execution receipts."""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = depends_on = None


def upgrade():
    op.execute("""CREATE TABLE homate.agent_actions (
        id UUID PRIMARY KEY, home_id TEXT NOT NULL REFERENCES homate.homes(id),
        user_id TEXT NOT NULL REFERENCES homate.users(id),
        request_id UUID NOT NULL, tool TEXT NOT NULL, arguments JSONB NOT NULL,
        summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending'
          CHECK(status IN ('pending','executing','executed','rejected','expired','failed')),
        expires_at TIMESTAMPTZ NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        result JSONB, UNIQUE(user_id, request_id))""")


def downgrade():
    op.execute("DROP TABLE homate.agent_actions")
