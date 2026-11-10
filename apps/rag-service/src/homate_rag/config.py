from pathlib import Path
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parents[4] / '.env', extra='ignore')
    rag_database_url: SecretStr = SecretStr('postgresql://homate_rag:homate_rag_local@127.0.0.1:55433/homate')
    backend_url: str = 'http://127.0.0.1:8000'
    knowledge_directory: str = '.work/knowledge'
    model_cache: str = '.work/rag-models'
