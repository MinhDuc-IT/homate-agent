"""Local Vietnamese speech engines. Only ai-service exposes these to users."""
import asyncio
import base64
import io
import wave
import threading
from functools import lru_cache
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from recognizer import transcribe, AudioDecodeError

app = FastAPI(title='HomeMate Local Speech')
MODEL = Path(__file__).parent / 'models' / 'vi_VN-vais1000-medium.onnx'
lock = threading.Lock()


@lru_cache(maxsize=1)
def voice():
    from piper import PiperVoice
    return PiperVoice.load(str(MODEL))


def synthesize(text: str) -> bytes:
    output = io.BytesIO()
    with lock, wave.open(output, 'wb') as wav:
        voice().synthesize_wav(text, wav)
    return output.getvalue()


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    voice: str = 'vi_VN-default'


@app.get('/health')
def health():
    return {'status': 'ok', 'stt': 'sherpa-onnx', 'tts': 'piper'}


@app.post('/transcribe')
async def recognize(audio: UploadFile = File(...)):
    try:
        raw = await audio.read(6_000_001)
        if len(raw) > 6_000_000: raise HTTPException(413, 'Audio quá lớn')
        return await transcribe(raw)
    except AudioDecodeError as error:
        raise HTTPException(400, str(error)) from None
    except (FileNotFoundError, RuntimeError):
        raise HTTPException(503, 'STT model chưa sẵn sàng') from None
    finally:
        await audio.close()


@app.post('/speak')
async def speak(body: SpeakRequest):
    if not body.text.strip(): raise HTTPException(422, 'Thiếu nội dung')
    try:
        audio = await asyncio.to_thread(synthesize, body.text.strip())
        return {'audio_format': 'wav', 'audio_base64': base64.b64encode(audio).decode('ascii')}
    except (OSError, RuntimeError):
        raise HTTPException(503, 'TTS model chưa sẵn sàng') from None
