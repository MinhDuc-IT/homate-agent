from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from types import SimpleNamespace
from homate_rag.ingestion.pipeline import IngestionPipeline
from homate_rag.ingestion.documents import DocumentCollection
from homate_rag.retrieval.pipeline import RetrievalPipeline

bearer = HTTPBearer(auto_error=False)


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Vui lòng đăng nhập')
    user = request.app.state.backend.identity(credentials.credentials)
    request.state.rag_token = credentials.credentials
    return user


def require_admin(user=Depends(get_current_user)):
    if user['role'] != 'admin': raise HTTPException(403, 'Chỉ admin được quản lý tài liệu')
    return user


def get_pipelines(request, user):
    index, embeddings, storage = request.app.state.index, request.app.state.embeddings, request.app.state.storage
    devices = request.app.state.backend.directory(request.state.rag_token)
    return SimpleNamespace(
        ingestion=IngestionPipeline(index, embeddings, storage, devices),
        retrieval=RetrievalPipeline(index, embeddings, devices),
        documents=DocumentCollection(index, storage, devices),
    )
