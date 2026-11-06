import asyncio
import base64
import io
import wave
import httpx
import pytest
from fastapi.testclient import TestClient
from homate_ai.bootstrap import create_app
from homate_ai.config import Settings
from homate_ai.domain.conversation import BackendError, AgentUnavailable
from homate_ai.infrastructure.speech import HttpSpeechRecognizer, HttpSpeechSynthesizer


def wav_bytes():
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(b'\0\0' * 160)
    return buffer.getvalue()


class Backend:
    async def identity(self, token):
        if token != 'valid': raise BackendError(401, 'Invalid token')
        return {'id': 'user'}


class Speech:
    def __init__(self): self.calls = []
    async def transcribe(self, audio, content_type):
        self.calls.append(audio)
        return 'Tắt đèn phòng khách'
    async def synthesize(self, text):
        self.calls.append(text)
        return wav_bytes()


def test_speech_routes_require_live_identity_and_validate_payloads():
    speech = Speech()
    with TestClient(create_app(Settings(), backend=Backend(), recognizer=speech, synthesizer=speech)) as client:
        path = '/api/ai/speech/transcribe'
        assert client.post(path, content=wav_bytes(), headers={'Content-Type':'audio/wav'}).status_code == 401
        headers = {'Authorization':'Bearer invalid', 'Content-Type':'audio/wav'}
        assert client.post(path, content=wav_bytes(), headers=headers).status_code == 401
        assert not speech.calls
        headers['Authorization'] = 'Bearer valid'
        assert client.post(path, content=b'bad', headers=headers).status_code == 400
        assert client.post(path, content=wav_bytes(), headers={**headers, 'Content-Type':'audio/webm'}).status_code == 415
        assert client.post(path, content=b'0' * 6_000_001, headers=headers).status_code == 413
        assert client.post(path, content=wav_bytes(), headers=headers).json()['text'] == 'Tắt đèn phòng khách'
        response = client.post('/api/ai/speech/synthesize', json={'text':'Xin chào'}, headers={'Authorization':'Bearer valid'})
        assert response.content == wav_bytes()
        assert response.headers['cache-control'] == 'no-store'
        assert client.post('/api/ai/speech/synthesize', json={'text':' '}, headers={'Authorization':'Bearer valid'}).status_code == 422


def test_http_speech_adapters_decode_and_reject_invalid_outputs():
    async def run():
        def handler(request):
            if request.url.path == '/transcribe':
                assert b'name="audio"' in request.content
                return httpx.Response(200, json={'text':' Xin chào '})
            return httpx.Response(200, json={'audio_base64':base64.b64encode(wav_bytes()).decode()})
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            assert await HttpSpeechRecognizer(client, 'http://speech').transcribe(wav_bytes(), 'audio/wav') == 'Xin chào'
            assert await HttpSpeechSynthesizer(client, 'http://speech').synthesize('Chào') == wav_bytes()
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={'audio_base64':'bad'}))) as client:
            with pytest.raises(AgentUnavailable):
                await HttpSpeechSynthesizer(client, 'http://speech').synthesize('Chào')
    asyncio.run(run())
