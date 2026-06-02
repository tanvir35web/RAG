from google import genai
from google.genai import types

from app.config import Settings
from app.models.responses import ChatResponse, Citation
from app.services.embedding_service import EmbeddingService
from app.services.pinecone_service import PineconeService
from app.utils.logging import get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """You are a precise document assistant. Answer questions based ONLY on the provided context.
If the context does not contain enough information to answer the question, say so clearly.
Do not fabricate information. Be concise and factual."""


class ChatService:
    def __init__(self, settings: Settings) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_chat_model
        self._embedding_service = EmbeddingService(settings)
        self._pinecone_service = PineconeService(settings)

    async def answer(
        self,
        question: str,
        top_k: int = 5,
        temperature: float = 0.2,
    ) -> ChatResponse:
        query_embedding = await self._embedding_service.embed_query(question)
        matches = self._pinecone_service.query(query_embedding, top_k=top_k)

        if not matches:
            return ChatResponse(
                answer="No relevant documents found to answer this question.",
                citations=[],
                model=self._model,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )

        context_parts: list[str] = []
        citations: list[Citation] = []

        for i, match in enumerate(matches):
            meta = match.get("metadata", {})
            text = meta.get("text", "")
            doc_name = meta.get("document_name", "unknown")
            page_num = int(meta.get("page_number", 0))
            chunk_id = meta.get("chunk_id", match["id"])
            score = float(match.get("score", 0.0))

            context_parts.append(f"[Source {i+1}: {doc_name}, page {page_num}]\n{text}")
            citations.append(
                Citation(
                    document_name=doc_name,
                    page_number=page_num,
                    chunk_id=chunk_id,
                    text_excerpt=text[:200],
                    relevance_score=round(score, 4),
                )
            )

        context = "\n\n---\n\n".join(context_parts)
        user_message = f"Context:\n{context}\n\nQuestion: {question}"

        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=user_message,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=temperature,
            ),
        )

        answer_text = response.text or ""
        usage = response.usage_metadata

        logger.info(
            "chat_response_generated",
            question_len=len(question),
            citations=len(citations),
            tokens=usage.total_token_count if usage else 0,
        )

        return ChatResponse(
            answer=answer_text,
            citations=citations,
            model=self._model,
            usage={
                "prompt_tokens": usage.prompt_token_count if usage else 0,
                "completion_tokens": usage.candidates_token_count if usage else 0,
                "total_tokens": usage.total_token_count if usage else 0,
            },
        )
