from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI
from homate_ai.config import Settings
from homate_ai.infrastructure.rag import HttpKnowledgeRetriever
from homate_ai.application.speech import SpeechService
from homate_ai.infrastructure.speech import HttpSpeechRecognizer, HttpSpeechSynthesizer
from homate_ai.application.orchestrator import Agent
from homate_ai.infrastructure.backend_client import BackendClient
from homate_ai.infrastructure.llm import CompatibleChatModel
from homate_ai.presentation.http import router


def create_app(settings=None, model=None, backend=None, recognizer=None, synthesizer=None, retriever=None):
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        base = 'https://api.openai.com/v1/' if settings.llm_provider == 'openai' else 'https://openrouter.ai/api/v1/'
        async with httpx.AsyncClient(base_url=settings.backend_url, timeout=20) as software, httpx.AsyncClient(base_url=base, timeout=40) as provider, httpx.AsyncClient(base_url=settings.rag_url, timeout=120) as rag_client:
            app.state.settings = settings
            backend_tools = backend or BackendClient(software)
            app.state.agent = Agent(model or CompatibleChatModel(provider, settings.model, settings.api_key), backend_tools, retriever=retriever or HttpKnowledgeRetriever(rag_client))
            speech_client = httpx.AsyncClient(timeout=120)
            app.state.speech = SpeechService(backend_tools, recognizer or HttpSpeechRecognizer(speech_client, settings.stt_url), synthesizer or HttpSpeechSynthesizer(speech_client, settings.tts_url))
            try:
                yield
            finally:
                await speech_client.aclose()

    app = FastAPI(title='HomeMate AI', lifespan=lifespan)
    app.include_router(router)
    @app.get('/health')
    def health(): return {'status':'ok','llm_configured':bool(settings.api_key)}
    return app
