from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict, Field
from homate_ai.domain.conversation import AgentUnavailable, BackendError

router = APIRouter(prefix='/api/ai', tags=['text-agent'])
bearer = HTTPBearer(auto_error=False)


class Message(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['user','assistant']
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    text: str = Field(min_length=1, max_length=4000)
    history: list[Message] = Field(default_factory=list, max_length=12)


@router.get('/status')
def status(request: Request):
    return {'text_agent':True, 'configured':bool(request.app.state.settings.api_key), 'voice':False, 'rag':False}


@router.post('/chat')
async def chat(body: ChatRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Vui lòng đăng nhập')
    try:
        return await request.app.state.agent.chat(credentials.credentials, str(body.request_id), body.text, [m.model_dump() for m in body.history])
    except BackendError as error: raise HTTPException(error.status, str(error)) from None
    except AgentUnavailable as error: raise HTTPException(503, str(error)) from None
