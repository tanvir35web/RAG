from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_name: str
    page_number: int
    chunk_id: str
    text_excerpt: str = Field(..., description="First 200 chars of the source chunk")
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    model: str
    usage: dict[str, int]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "answer": "The document discusses...",
                    "citations": [
                        {
                            "document_name": "report.pdf",
                            "page_number": 3,
                            "chunk_id": "report.pdf_p3_c0",
                            "text_excerpt": "Key findings indicate...",
                            "relevance_score": 0.91,
                        }
                    ],
                    "model": "gpt-4o-mini",
                    "usage": {"prompt_tokens": 512, "completion_tokens": 128, "total_tokens": 640},
                }
            ]
        }
    }


class DocumentInfo(BaseModel):
    document_name: str
    chunk_count: int
    uploaded_at: datetime | None = None
    pages: list[int] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class UploadResponse(BaseModel):
    document_name: str
    chunks_created: int
    pages_processed: int
    message: str


class DeleteResponse(BaseModel):
    document_name: str
    chunks_deleted: int
    message: str


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    services: dict[str, str]
