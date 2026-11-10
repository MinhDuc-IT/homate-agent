from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from homate_rag.api.auth import get_current_user, require_admin, get_pipelines
from homate_rag.embedding.encoder import EmbeddingUnavailable

router = APIRouter(prefix='/api/rag', tags=['knowledge'])


class DocumentInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=160)
    filename: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=100_000)
    device_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator('filename')
    @classmethod
    def text_files(cls, value):
        if not value.lower().endswith(('.md', '.txt')) or '/' in value or '\\' in value:
            raise ValueError('Chỉ hỗ trợ tên file Markdown/TXT')
        return value


class DeviceLinks(BaseModel):
    model_config = ConfigDict(extra='forbid')
    device_ids: list[str] = Field(max_length=100)


def pipelines(request, user): return get_pipelines(request, user)


@router.get('/documents')
def documents(request: Request, user=Depends(get_current_user)):
    return {'documents': pipelines(request, user).documents.list(user['home_id'])}


@router.post('/documents', status_code=201)
def create(body: DocumentInput, request: Request, user=Depends(require_admin)):
    try:
        result = pipelines(request, user).ingestion.run(user, **body.model_dump())
        return {'id':result['id'], 'title':result['title']}
    except EmbeddingUnavailable as error: raise HTTPException(503, str(error)) from None


@router.put('/documents/{identifier}/devices')
def link(identifier: UUID, body: DeviceLinks, request: Request, user=Depends(require_admin)):
    try: pipelines(request, user).documents.link(user['home_id'], str(identifier), body.device_ids)
    except LookupError as error: raise HTTPException(404, str(error)) from None
    return {'updated': True}


@router.delete('/documents/{identifier}')
def delete(identifier: UUID, request: Request, user=Depends(require_admin)):
    try: pipelines(request, user).documents.delete(user['home_id'], str(identifier))
    except LookupError as error: raise HTTPException(404, str(error)) from None
    return {'deleted': True}


@router.get('/documents/{identifier}/source')
def source(identifier: UUID, request: Request, user=Depends(get_current_user)):
    try:
        return Response(pipelines(request, user).documents.read(user['home_id'], str(identifier)), media_type='text/plain', headers={'Cache-Control':'no-store'})
    except (LookupError, FileNotFoundError): raise HTTPException(404, 'Không tìm thấy tài liệu') from None


@router.get('/search')
def search(request: Request, query: str, device_id: str | None = None, user=Depends(get_current_user)):
    if not query.strip() or len(query) > 2000: raise HTTPException(422, 'Câu hỏi phải có 1–2000 ký tự')
    try: return {'chunks':pipelines(request, user).retrieval.run(user['home_id'], query.strip(), device_id)}
    except EmbeddingUnavailable as error: raise HTTPException(503, str(error)) from None
