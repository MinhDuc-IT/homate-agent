import os
import json
from uuid import uuid4
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
import pytest
from fastapi.testclient import TestClient
from homate_rag.app import create_app
from homate_rag.config import Settings
from homate_rag.indexing.migrate import migrate
from homate_rag.clients.backend import BackendAccessError
from homate_rag.embedding.encoder import EmbeddingUnavailable
from homate_rag.indexing.pgvector import PgVectorIndex
from homate_rag.storage.files import LocalDocumentStorage


@pytest.fixture
def database():
    url = os.environ.get('RAG_TEST_DATABASE_URL')
    if not url: pytest.skip('Set RAG_TEST_DATABASE_URL to a disposable-capable PostgreSQL with pgvector')
    url = url.replace('postgresql+psycopg://','postgresql://',1)
    name, role = 'rag_test_'+uuid4().hex, 'rag_role_'+uuid4().hex
    scoped = make_conninfo(url, dbname=name)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try: yield scoped, make_conninfo(scoped,user=role,password='rag-test-password'), role
    finally:
        with psycopg.connect(url,autocommit=True) as conn:
            conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
            conn.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))


class Directory:
    def __init__(self, token): self.token = token
    def validate(self, devices):
        if set(devices) - ({'light'} if self.token != 'other' else set()): raise ValueError('Invalid device')


class Backend:
    def identity(self, token):
        if token not in {'admin','member','other'}: raise BackendAccessError(401,'Invalid token')
        return {'id':token, 'home_id':'other-home' if token=='other' else 'home', 'role':'member' if token=='member' else 'admin'}
    def directory(self, token): return Directory(token)


class Embeddings:
    def embed(self,texts): return [[1.0]+[0.0]*383 for _ in texts]


def test_rag_service_permissions_isolation_lifecycle_and_database_role(database,tmp_path):
    admin_url, runtime_url, role = database
    migrate(admin_url,'rag-test-password',role)
    migrate(admin_url,'rag-test-password',role)  # Idempotent setup.
    with psycopg.connect(admin_url) as conn:
        conn.execute('CREATE SCHEMA homate; CREATE TABLE homate.private_data(secret TEXT)')
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(runtime_url) as conn: conn.execute('SELECT * FROM homate.private_data')
    with psycopg.connect(runtime_url) as conn:
        assert conn.execute('SELECT rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').fetchone() == (False,False,False)
    app = create_app(Settings(rag_database_url=runtime_url),backend=Backend(),embeddings=Embeddings(),storage=LocalDocumentStorage(tmp_path))
    data = {'title':'Guide','filename':'guide.md','content':'Confirm a proposed action with the confirm button.','device_ids':['light']}
    with TestClient(app) as client:
        headers={'Authorization':'Bearer admin'}
        member={'Authorization':'Bearer member'}
        other={'Authorization':'Bearer other'}
        base='/api/rag'
        assert client.get(base+'/documents').status_code==401
        assert client.get(base+'/documents',headers={'Authorization':'Bearer invalid'}).status_code==401
        assert client.post(base+'/documents',headers=member,json=data).status_code==403
        assert client.post(base+'/documents',headers=headers,json={**data,'device_ids':['unknown']}).status_code==400
        response=client.post(base+'/documents',headers=headers,json=data)
        assert response.status_code==201,response.text
        identifier=response.json()['id']
        path=base+f'/documents/{identifier}'
        assert client.get(path+'/source',headers=member).text==data['content']
        assert client.get(base+'/search',headers=member,params={'query':'Confirm','device_id':'light'}).json()['chunks'][0]['document_id']==identifier
        assert client.get(base+'/documents',headers=other).json()['documents']==[]
        assert client.get(base+'/search',headers=other,params={'query':'Confirm'}).json()['chunks']==[]
        assert client.get(path+'/source',headers=other).status_code==404
        assert client.delete(path,headers=other).status_code==404
        assert client.put(path+'/devices',headers=headers,json={'device_ids':[]}).status_code==200
        assert client.get(base+'/search',headers=member,params={'query':'Confirm','device_id':'light'}).json()['chunks']==[]
        assert client.delete(path,headers=member).status_code==403
        assert client.delete(path,headers=headers).status_code==200
        assert not list(tmp_path.iterdir())
        assert client.get(base+'/search',headers=member,params={'query':'Confirm'}).json()['chunks']==[]
        class Offline:
            def embed(self,texts): raise EmbeddingUnavailable('Offline')
        app.state.embeddings=Offline()
        assert client.post(base+'/documents',headers=headers,json=data).status_code==503
        assert not list(tmp_path.iterdir())


def test_legacy_tables_are_moved_without_losing_document_ids_or_vectors(database):
    admin_url,runtime_url,role=database
    identifier=str(uuid4())
    with psycopg.connect(admin_url) as conn:
        conn.execute('''CREATE EXTENSION vector; CREATE SCHEMA homate;
            CREATE TABLE homate.knowledge_documents(id UUID PRIMARY KEY,home_id TEXT,title TEXT,filename TEXT,storage_key TEXT,model TEXT,created_by TEXT,created_at TIMESTAMPTZ DEFAULT now());
            CREATE TABLE homate.device_documents(device_id TEXT,document_id UUID REFERENCES homate.knowledge_documents(id),PRIMARY KEY(device_id,document_id));
            CREATE TABLE homate.knowledge_chunks(id UUID PRIMARY KEY,document_id UUID REFERENCES homate.knowledge_documents(id),ordinal INTEGER,content TEXT,metadata JSONB,embedding vector(384));''')
        from homate_rag.embedding.model import MODEL
        conn.execute('INSERT INTO homate.knowledge_documents(id,home_id,title,filename,storage_key,model,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s)',(identifier,'home','Legacy','guide.md',identifier+'.txt',MODEL,'admin'))
        conn.execute('INSERT INTO homate.knowledge_chunks VALUES(%s,%s,0,%s,%s::jsonb,%s::vector)',(uuid4(),identifier,'Original content','{}',json.dumps([1.0]+[0.0]*383)))
        conn.execute('INSERT INTO homate.device_documents VALUES(%s,%s)',('light',identifier))
    migrate(admin_url,'rag-test-password',role)
    repository=PgVectorIndex(runtime_url)
    assert repository.get('home',identifier)['title']=='Legacy'
    assert repository.list('home')[0]['device_ids']==['light']
    assert repository.search('home',[1.0]+[0.0]*383,'light',5,0.35)[0]['content']=='Original content'
    with psycopg.connect(admin_url) as conn:
        assert conn.execute("SELECT to_regclass('homate.knowledge_documents')").fetchone()[0] is None
