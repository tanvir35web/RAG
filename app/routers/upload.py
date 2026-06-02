from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.config import Settings
from app.dependencies import EmbeddingServiceDep, PDFServiceDep, PineconeServiceDep, SettingsDep
from app.models.responses import UploadResponse
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])


def _validate_upload(file: UploadFile, settings: Settings) -> None:
    if file.content_type not in settings.allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Only PDF files are accepted. Got: {file.content_type}",
        )
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must have a .pdf extension.",
        )


@router.post(
    "",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest a PDF",
    description="Upload a PDF file. Text is extracted, chunked, embedded, and stored in Pinecone.",
)
async def upload_pdf(
    file: UploadFile,
    settings: SettingsDep,
    pdf_service: PDFServiceDep,
    embedding_service: EmbeddingServiceDep,
    pinecone_service: PineconeServiceDep,
) -> UploadResponse:
    _validate_upload(file, settings)

    pdf_bytes = await file.read()
    if len(pdf_bytes) > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.max_file_size_mb} MB limit.",
        )
    if len(pdf_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    document_name = file.filename  # already validated non-None above

    logger.info("upload_started", document_name=document_name, size_bytes=len(pdf_bytes))

    try:
        chunks = pdf_service.process_pdf(pdf_bytes, document_name)
    except Exception as exc:
        logger.error("pdf_processing_failed", document_name=document_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process PDF: {exc}",
        ) from exc

    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No text could be extracted from the PDF.",
        )

    try:
        embeddings = await embedding_service.embed_texts([c.text for c in chunks])
    except Exception as exc:
        logger.error("embedding_failed", document_name=document_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate embeddings.",
        ) from exc

    try:
        uploaded_at = datetime.now(timezone.utc)
        await pinecone_service.upsert_chunks(chunks, embeddings, uploaded_at)
    except Exception as exc:
        logger.error("pinecone_upsert_failed", document_name=document_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to store vectors in Pinecone.",
        ) from exc

    pages = sorted({c.page_number for c in chunks})
    logger.info(
        "upload_complete",
        document_name=document_name,
        chunks=len(chunks),
        pages=len(pages),
    )

    return UploadResponse(
        document_name=document_name,
        chunks_created=len(chunks),
        pages_processed=len(pages),
        message=f"Successfully ingested '{document_name}' ({len(chunks)} chunks across {len(pages)} pages).",
    )
