from homate_ai.application.ports import BackendTools, SpeechRecognizer, SpeechSynthesizer


class SpeechService:
    def __init__(self, backend: BackendTools, recognizer: SpeechRecognizer, synthesizer: SpeechSynthesizer):
        self.backend, self.recognizer, self.synthesizer = backend, recognizer, synthesizer

    async def transcribe(self, token: str, audio: bytes, content_type: str) -> str:
        await self.backend.identity(token)
        return await self.recognizer.transcribe(audio, content_type)

    async def synthesize(self, token: str, text: str) -> bytes:
        await self.backend.identity(token)
        return await self.synthesizer.synthesize(text)
