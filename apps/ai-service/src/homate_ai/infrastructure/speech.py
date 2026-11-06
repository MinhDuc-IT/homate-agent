"""HTTP adapters for independent STT and TTS services."""
import base64
import binascii
import httpx
from homate_ai.domain.conversation import AgentUnavailable


class HttpSpeechRecognizer:
    def __init__(self, client: httpx.AsyncClient, url: str):
        self.client, self.url = client, url

    async def transcribe(self, audio: bytes, content_type: str) -> str:
        if not self.url:
            raise AgentUnavailable('Chưa cấu hình STT_URL.')
        try:
            response = await self.client.post(self.url.rstrip('/') + '/transcribe',
                files={'audio': ('recording.wav', audio, content_type)})
            response.raise_for_status()
            text = response.json()['text']
            if not isinstance(text, str) or len(text) > 4000:
                raise ValueError('Invalid transcript')
            return text.strip()
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise AgentUnavailable('Không nhận dạng được giọng nói. Kiểm tra STT service.') from None


class HttpSpeechSynthesizer:
    def __init__(self, client: httpx.AsyncClient, url: str):
        self.client, self.url = client, url

    async def synthesize(self, text: str) -> bytes:
        if not self.url:
            raise AgentUnavailable('Chưa cấu hình TTS_URL.')
        try:
            response = await self.client.post(self.url.rstrip('/') + '/speak',
                json={'text': text, 'voice': 'vi_VN-default'})
            response.raise_for_status()
            audio = base64.b64decode(response.json()['audio_base64'], validate=True)
            if len(audio) < 44 or audio[:4] != b'RIFF' or audio[8:12] != b'WAVE':
                raise ValueError('Invalid WAV')
            return audio
        except (httpx.HTTPError, ValueError, KeyError, TypeError, binascii.Error):
            raise AgentUnavailable('Không tạo được giọng đọc. Kiểm tra TTS service.') from None
