from pathlib import Path
from typing import Literal
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[4] / '.env', extra='ignore')
    llm_provider: Literal['openai','openrouter'] = 'openai'
    openai_api_key: SecretStr = SecretStr('')
    openai_model_name: str = 'gpt-4o-mini'
    openrouter_api_key: SecretStr = SecretStr('')
    openrouter_model_name: str = 'openai/gpt-4o-mini'
    backend_url: str = 'http://127.0.0.1:8000'

    @property
    def api_key(self):
        return (self.openai_api_key if self.llm_provider == 'openai' else self.openrouter_api_key).get_secret_value()

    @property
    def model(self):
        return self.openai_model_name if self.llm_provider == 'openai' else self.openrouter_model_name
