"""Home-scoped document knowledge and local vector embeddings."""
from alembic import op

revision = '0004'
down_revision = '0003'
branch_labels = depends_on = None


def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public')
    op.execute('''
    CREATE TABLE homate.knowledge_documents (
        id UUID PRIMARY KEY, home_id TEXT NOT NULL REFERENCES homate.homes(id),
        title TEXT NOT NULL, filename TEXT NOT NULL, storage_key TEXT NOT NULL,
        model TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES homate.users(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    CREATE TABLE homate.device_documents (
        device_id TEXT NOT NULL REFERENCES homate.devices(id) ON DELETE CASCADE,
        document_id UUID NOT NULL REFERENCES homate.knowledge_documents(id) ON DELETE CASCADE,
        PRIMARY KEY(device_id, document_id)
    );
    CREATE TABLE homate.knowledge_chunks (
        id UUID PRIMARY KEY,
        document_id UUID NOT NULL REFERENCES homate.knowledge_documents(id) ON DELETE CASCADE,
        ordinal INTEGER NOT NULL, content TEXT NOT NULL,
        metadata JSONB NOT NULL DEFAULT '{}', embedding public.vector(384) NOT NULL,
        UNIQUE(document_id, ordinal)
    );
    CREATE INDEX knowledge_home ON homate.knowledge_documents(home_id);
    ''')


def downgrade():
    op.execute('DROP TABLE homate.knowledge_chunks, homate.device_documents, homate.knowledge_documents')
