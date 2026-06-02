from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.dependencies import PineconeServiceDep
from app.models.responses import DeleteResponse, DocumentInfo, DocumentListResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all ingested documents",
)
async def list_documents(
    pinecone_service: PineconeServiceDep,
) -> DocumentListResponse:
    try:
        raw_docs = pinecone_service.list_documents()
    except Exception as exc:
        logger.error("list_documents_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve document list.",
        ) from exc

    documents = [
        DocumentInfo(
            document_name=doc["document_name"],
            chunk_count=doc["chunk_count"],
            uploaded_at=_parse_dt(doc.get("uploaded_at")),
            pages=doc.get("pages", []),
        )
        for doc in raw_docs
    ]

    return DocumentListResponse(documents=documents, total=len(documents))


@router.delete(
    "/{document_name:path}",
    response_model=DeleteResponse,
    summary="Delete all chunks for a document",
)
async def delete_document(
    document_name: str,
    pinecone_service: PineconeServiceDep,
) -> DeleteResponse:
    if not document_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="document_name must not be empty.",
        )

    logger.info("delete_document_request", document_name=document_name)

    try:
        deleted = pinecone_service.delete_document(document_name)
    except Exception as exc:
        logger.error("delete_document_failed", document_name=document_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to delete document.",
        ) from exc

    if deleted == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No document named '{document_name}' found.",
        )

    return DeleteResponse(
        document_name=document_name,
        chunks_deleted=deleted,
        message=f"Deleted {deleted} chunk(s) for '{document_name}'.",
    )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
