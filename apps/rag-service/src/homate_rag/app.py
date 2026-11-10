from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from homate_rag.config import Settings
from homate_rag.clients.backend import BackendAccess, BackendAccessError
from homate_rag.embedding.encoder import LocalEmbeddings
from homate_rag.indexing.pgvector import PgVectorIndex
from homate_rag.storage.files import LocalDocumentStorage
from homate_rag.api.routes import router


def create_app(settings=None, *, backend=None, embeddings=None, index=None, storage=None):
    settings = settings or Settings()
    @asynccontextmanager
    async def lifespan(app):
        with httpx.Client(base_url=settings.backend_url, timeout=20) as client:
            app.state.backend = backend or BackendAccess(client)
            app.state.embeddings = embeddings or LocalEmbeddings(settings.model_cache)
            app.state.index = index or PgVectorIndex(settings.rag_database_url.get_secret_value())
            app.state.storage = storage or LocalDocumentStorage(settings.knowledge_directory)
            yield
    app = FastAPI(title='HomeMate RAG', lifespan=lifespan)
    app.include_router(router)

    @app.exception_handler(BackendAccessError)
    def backend_error(request: Request, error):
        return JSONResponse(status_code=error.status, content={'detail':error.message})

    @app.exception_handler(ValueError)
    def invalid(request: Request, error):
        return JSONResponse(status_code=400, content={'detail':str(error)})

    @app.get('/health')
    def health(): return {'status':'ok', 'service':'rag', 'embedding':'local'}
    return app
