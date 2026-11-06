from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request, Response
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
    return {'text_agent':True, 'configured':bool(request.app.state.settings.api_key), 'voice':bool(request.app.state.settings.stt_url and request.app.state.settings.tts_url), 'stt_configured':bool(request.app.state.settings.stt_url), 'tts_configured':bool(request.app.state.settings.tts_url), 'rag':False}


@router.post('/chat')
async def chat(body: ChatRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Vui lòng đăng nhập')
    try:
        return await request.app.state.agent.chat(credentials.credentials, str(body.request_id), body.text, [m.model_dump() for m in body.history])
    except BackendError as error: raise HTTPException(error.status, str(error)) from None
    except AgentUnavailable as error: raise HTTPException(503, str(error)) from None


class SpeakRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    text: str = Field(min_length=1, max_length=4000)


@router.post('/speech/transcribe')
async def transcribe(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Vui lòng đăng nhập')
    # WAV PCM from the browser; limit streamed bytes even without Content-Length.
    if request.headers.get('content-type', '').split(';')[0] not in {'audio/wav', 'audio/x-wav'}:
        raise HTTPException(415, 'Chỉ hỗ trợ WAV')
    audio = bytearray()
    async for chunk in request.stream():
        audio.extend(chunk)
        if len(audio) > 6_000_000: raise HTTPException(413, 'Bản ghi quá lớn; tối đa 60 giây')
    if len(audio) < 44 or audio[:4] != b'RIFF' or audio[8:12] != b'WAVE':
        raise HTTPException(400, 'Dữ liệu WAV không hợp lệ')
    try:
        text = await request.app.state.speech.transcribe(credentials.credentials, bytes(audio), 'audio/wav')
        return {'text': text}
    except BackendError as error: raise HTTPException(error.status, str(error)) from None
    except AgentUnavailable as error: raise HTTPException(503, str(error)) from None


@router.post('/speech/synthesize')
async def synthesize(body: SpeakRequest, request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Vui lòng đăng nhập')
    if not body.text.strip(): raise HTTPException(422, 'Nội dung không được để trống')
    try:
        audio = await request.app.state.speech.synthesize(credentials.credentials, body.text.strip())
        return Response(audio, media_type='audio/wav', headers={'Cache-Control':'no-store'})
    except BackendError as error: raise HTTPException(error.status, str(error)) from None
    except AgentUnavailable as error: raise HTTPException(503, str(error)) from None
