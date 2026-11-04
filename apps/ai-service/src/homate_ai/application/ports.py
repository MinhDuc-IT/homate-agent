from typing import Protocol
from homate_ai.domain.conversation import ModelReply


class LanguageModel(Protocol):
    async def complete(self, messages: list[dict], tools: list[dict]) -> ModelReply: ...


class BackendTools(Protocol):
    async def identity(self, token: str) -> dict: ...
    async def call(self, token: str, request_id: str, name: str, arguments: dict) -> dict: ...


class SpeechRecognizer(Protocol):
    async def transcribe(self, audio: bytes, content_type: str) -> str: ...


class SpeechSynthesizer(Protocol):
    async def synthesize(self, text: str) -> bytes: ...


class KnowledgeRetriever(Protocol):
    async def retrieve(self, home_id: str, query: str) -> list[dict]: ...
