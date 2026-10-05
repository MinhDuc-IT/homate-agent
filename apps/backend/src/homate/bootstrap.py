import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

from homate.modules.catalog.application import CatalogService
from homate.modules.catalog.domain import CatalogError
from homate.modules.catalog.infrastructure import PostgresCatalogRepository
from homate.modules.catalog.presentation import catalog_router


def create_catalog_app(database_url: str | None = None):
    url = database_url or os.environ.get("DATABASE_URL")
    if not url or not url.startswith("postgresql+psycopg://"):
        raise RuntimeError("Set DATABASE_URL to a postgresql+psycopg:// connection URL.")
    engine = create_engine(url, pool_pre_ping=True)

    @asynccontextmanager
    async def lifespan(app):
        yield
        engine.dispose()

    app = FastAPI(title="Homate Catalog API", version="0.1.0", lifespan=lifespan)

    def service():
        # Commit before returning a successful response; exceptions roll back.
        with engine.begin() as connection:
            yield CatalogService(PostgresCatalogRepository(connection))

    @app.exception_handler(CatalogError)
    async def catalog_error(request: Request, error: CatalogError):
        return JSONResponse(status_code=error.status, content={"detail": error.message})

    @app.get("/health")
    def health():
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(catalog_router(service))
    return app


def create_app(database_url: str | None = None, *, start_workers=True):
    from homate.software_bootstrap import create_app as create_software_app
    return create_software_app(database_url, start_workers=start_workers)
