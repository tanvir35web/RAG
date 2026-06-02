import asyncio

from google import genai
from google.genai import types

from app.config import Settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_CONCURRENT_BATCH = 20  # max parallel embed calls

# Task prefixes for gemini-embedding-2 (replaces task_type enum)
_DOC_PREFIX = "task: retrieval document | "
_QUERY_PREFIX = "task: retrieval query | "


class EmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model
        self._dimensions = settings.gemini_embedding_dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        semaphore = asyncio.Semaphore(_CONCURRENT_BATCH)

        async def _embed_one(text: str) -> list[float]:
            async with semaphore:
                result = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=f"{_DOC_PREFIX}{text}",
                    config=types.EmbedContentConfig(
                        output_dimensionality=self._dimensions,
                    ),
                )
                return result.embeddings[0].values

        embeddings = await asyncio.gather(*[_embed_one(t) for t in texts])
        logger.info("embeddings_generated", count=len(texts))
        return list(embeddings)

    async def embed_query(self, text: str) -> list[float]:
        result = await self._client.aio.models.embed_content(
            model=self._model,
            contents=f"{_QUERY_PREFIX}{text}",
            config=types.EmbedContentConfig(
                output_dimensionality=self._dimensions,
            ),
        )
        return result.embeddings[0].values
