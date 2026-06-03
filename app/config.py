from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Google Gemini
    gemini_api_key: str
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_chat_model: str = "gemini-3.1-flash-lite"
    gemini_embedding_dimensions: int = 768  # output_dimensionality (128–3072)

    # Pinecone
    pinecone_api_key: str
    pinecone_index: str
    pinecone_namespace: str = "documents"
    pinecone_top_k: int = 5

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Upload limits
    max_file_size_mb: int = 50
    allowed_content_types: list[str] = ["application/pdf"]

    # App
    app_env: Literal["development", "production", "testing"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
