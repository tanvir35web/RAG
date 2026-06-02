from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.pdf_service import PDFService
from app.services.pinecone_service import PineconeService

SettingsDep = Annotated[Settings, Depends(get_settings)]

# Module-level singletons — initialized once on first request
_pdf_service: PDFService | None = None
_embedding_service: EmbeddingService | None = None
_pinecone_service: PineconeService | None = None
_chat_service: ChatService | None = None


def get_pdf_service(settings: SettingsDep) -> PDFService:
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService(settings)
    return _pdf_service


def get_embedding_service(settings: SettingsDep) -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(settings)
    return _embedding_service


def get_pinecone_service(settings: SettingsDep) -> PineconeService:
    global _pinecone_service
    if _pinecone_service is None:
        _pinecone_service = PineconeService(settings)
    return _pinecone_service


def get_chat_service(settings: SettingsDep) -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService(settings)
    return _chat_service


PDFServiceDep = Annotated[PDFService, Depends(get_pdf_service)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
PineconeServiceDep = Annotated[PineconeService, Depends(get_pinecone_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
