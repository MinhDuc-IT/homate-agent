"""Privileged, one-shot schema setup; runtime uses a restricted role."""
import os
import psycopg
from psycopg import sql


def migrate(url, password, role="homate_rag"):
    with psycopg.connect(url.replace('postgresql+psycopg://','postgresql://',1)) as conn:
        conn.execute('SELECT pg_advisory_xact_lock(706072)')
        conn.execute('CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public')
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
            conn.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT').format(sql.Identifier(role)))
        conn.execute(sql.SQL('ALTER ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT PASSWORD {}').format(sql.Identifier(role),sql.Literal(password)))
        conn.execute(sql.SQL('CREATE SCHEMA IF NOT EXISTS rag AUTHORIZATION {}').format(sql.Identifier(role)))
        # Adopt the previous uncommitted implementation without re-embedding.
        for old, new in [('knowledge_documents','documents'), ('device_documents','document_devices'), ('knowledge_chunks','chunks')]:
            if conn.execute('SELECT to_regclass(%s)', ('homate.'+old,)).fetchone()[0]:
                if conn.execute('SELECT to_regclass(%s)', ('rag.'+new,)).fetchone()[0]:
                    raise RuntimeError('Both legacy and RAG tables exist; resolve before migration')
                conn.execute(sql.SQL('ALTER TABLE homate.{} SET SCHEMA rag').format(sql.Identifier(old)))
                conn.execute(sql.SQL('ALTER TABLE rag.{} RENAME TO {}').format(sql.Identifier(old),sql.Identifier(new)))
        conn.execute('''CREATE TABLE IF NOT EXISTS rag.documents (
            id UUID PRIMARY KEY, home_id TEXT NOT NULL, title TEXT NOT NULL, filename TEXT NOT NULL,
            storage_key TEXT NOT NULL, model TEXT NOT NULL, created_by TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now());
            CREATE TABLE IF NOT EXISTS rag.document_devices (
            device_id TEXT NOT NULL, document_id UUID NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,
            PRIMARY KEY(device_id,document_id));
            CREATE TABLE IF NOT EXISTS rag.chunks (
            id UUID PRIMARY KEY, document_id UUID NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, content TEXT NOT NULL, metadata JSONB NOT NULL DEFAULT '{}',
            embedding public.vector(384) NOT NULL, UNIQUE(document_id,ordinal));
            CREATE INDEX IF NOT EXISTS rag_document_home ON rag.documents(home_id);''')
        # Home/user/device ownership is checked through backend APIs, not cross-service FKs.
        constraints = conn.execute('''SELECT t.relname,c.conname FROM pg_constraint c
            JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            JOIN pg_class referenced ON referenced.oid=c.confrelid
            JOIN pg_namespace rn ON rn.oid=referenced.relnamespace
            WHERE c.contype='f' AND n.nspname='rag' AND rn.nspname='homate' ''').fetchall()
        for table, constraint in constraints:
            conn.execute(sql.SQL('ALTER TABLE rag.{} DROP CONSTRAINT {}').format(sql.Identifier(table),sql.Identifier(constraint)))
        for name in ('documents','document_devices','chunks'):
            conn.execute(sql.SQL('ALTER TABLE rag.{} OWNER TO {}').format(sql.Identifier(name),sql.Identifier(role)))
        conn.execute(sql.SQL('ALTER SCHEMA rag OWNER TO {}').format(sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier(conn.info.dbname),sql.Identifier(role)))
        conn.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))


if __name__ == '__main__':
    migrate(os.environ['DATABASE_URL'], os.environ['RAG_DB_PASSWORD'])
    print('RAG schema ready; legacy documents preserved.')
