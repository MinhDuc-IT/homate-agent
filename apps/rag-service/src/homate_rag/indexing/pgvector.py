import json
from uuid import uuid4
from psycopg.types.json import Jsonb
from homate_rag.indexing.connection import connect
from homate_rag.embedding.model import MODEL


class PgVectorIndex:
    def __init__(self, url): self.url = url

    def list(self, home_id):
        with connect(self.url) as conn:
            return conn.execute('''SELECT d.id::text, d.title, d.filename, d.model, d.created_at,
                ARRAY(SELECT device_id FROM document_devices WHERE document_id=d.id ORDER BY device_id) AS device_ids,
                (SELECT count(*) FROM chunks WHERE document_id=d.id) AS chunk_count
                FROM documents d WHERE d.home_id=%s ORDER BY d.created_at DESC''', (home_id,)).fetchall()

    def get(self, home_id, identifier):
        with connect(self.url) as conn:
            row = conn.execute('SELECT *, id::text AS id FROM documents WHERE home_id=%s AND id=%s', (home_id, identifier)).fetchone()
            if not row: raise LookupError('Không tìm thấy tài liệu')
            return row

    def create(self, document, chunks, vectors):
        with connect(self.url) as conn:
            conn.execute('''INSERT INTO documents(id, home_id, title, filename, storage_key, model, created_by)
                VALUES(%s,%s,%s,%s,%s,%s,%s)''', tuple(document[k] for k in ('id','home_id','title','filename','storage_key','model','created_by')))
            conn.executemany('INSERT INTO document_devices(device_id,document_id) VALUES(%s,%s)', [(d, document['id']) for d in document['device_ids']])
            conn.executemany('''INSERT INTO chunks(id,document_id,ordinal,content,metadata,embedding)
                VALUES(%s,%s,%s,%s,%s,%s::public.vector)''', [(uuid4(),document['id'],i,c['content'],Jsonb(c['metadata']),json.dumps(v)) for i,(c,v) in enumerate(zip(chunks,vectors))])

    def delete(self, home_id, identifier):
        with connect(self.url) as conn:
            conn.execute('DELETE FROM documents WHERE home_id=%s AND id=%s', (home_id, identifier))

    def link(self, home_id, identifier, devices):
        with connect(self.url) as conn:
            if not conn.execute('SELECT id FROM documents WHERE home_id=%s AND id=%s FOR UPDATE', (home_id, identifier)).fetchone():
                raise LookupError('Không tìm thấy tài liệu')
            conn.execute('DELETE FROM document_devices WHERE document_id=%s', (identifier,))
            conn.executemany('INSERT INTO document_devices(device_id,document_id) VALUES(%s,%s)', [(d, identifier) for d in set(devices)])

    def search(self, home_id, vector, device_id, limit, threshold):
        with connect(self.url) as conn:
            rows = conn.execute('''SELECT c.id::text AS chunk_id, d.id::text AS document_id, d.title,
                d.filename, c.ordinal, c.content, c.metadata, 1-(c.embedding <=> %s::public.vector) AS score
                FROM chunks c JOIN documents d ON d.id=c.document_id
                WHERE d.home_id=%s AND d.model=%s
                AND (%s::text IS NULL OR EXISTS(SELECT 1 FROM document_devices dd WHERE dd.document_id=d.id AND dd.device_id=%s))
                AND 1-(c.embedding <=> %s::public.vector) >= %s
                ORDER BY c.embedding <=> %s::public.vector LIMIT %s''',
                (json.dumps(vector),home_id,MODEL,device_id,device_id,json.dumps(vector),threshold,json.dumps(vector),limit)).fetchall()
            return rows
