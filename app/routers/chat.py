from fastapi import APIRouter, HTTPException, status

from app.dependencies import ChatServiceDep
from app.models.requests import ChatRequest
from app.models.responses import ChatResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask a question against ingested documents",
    description=(
        "Submit a natural-language question. The API retrieves the most relevant "
        "chunks from Pinecone and generates a grounded answer with citations."
    ),
)
async def chat(
    request: ChatRequest,
    chat_service: ChatServiceDep,
) -> ChatResponse:
    logger.info("chat_request", question_preview=request.question[:80])

    try:
        response = await chat_service.answer(
            question=request.question,
            top_k=request.top_k,
            temperature=request.temperature,
        )
    except Exception as exc:
        logger.error("chat_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate answer. Please try again.",
        ) from exc

    return response
