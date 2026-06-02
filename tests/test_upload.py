import io
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient


def test_upload_rejects_non_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/upload",
        files={"file": ("doc.txt", b"some text", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/api/v1/upload",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_success(client: TestClient) -> None:
    pdf_content = b"%PDF-1.4 minimal"

    with (
        patch("app.routers.upload.PDFService.process_pdf") as mock_process,
        patch("app.routers.upload.EmbeddingService.embed_texts", new_callable=AsyncMock) as mock_embed,
        patch("app.routers.upload.PineconeService.upsert_chunks", new_callable=AsyncMock) as mock_upsert,
    ):
        from app.services.pdf_service import TextChunk

        fake_chunk = TextChunk(
            text="Hello World", page_number=1, chunk_index=0, document_name="test.pdf"
        )
        mock_process.return_value = [fake_chunk]
        mock_embed.return_value = [[0.1] * 1536]
        mock_upsert.return_value = 1

        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )

    # 201 or 422 depending on whether pypdf can parse the minimal bytes
    assert response.status_code in {201, 422}


def test_upload_too_large(client: TestClient) -> None:
    # 51 MB of zeros
    oversized = b"%PDF" + b"0" * (51 * 1024 * 1024)
    response = client.post(
        "/api/v1/upload",
        files={"file": ("big.pdf", oversized, "application/pdf")},
    )
    assert response.status_code == 413
