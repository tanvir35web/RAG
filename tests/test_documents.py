from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient


def _mock_doc_list() -> list[dict]:
    return [
        {
            "document_name": "report.pdf",
            "chunk_count": 12,
            "pages": [1, 2, 3],
            "uploaded_at": "2026-01-01T00:00:00+00:00",
        }
    ]


def test_list_documents(client: TestClient) -> None:
    with patch(
        "app.services.pinecone_service.PineconeService.list_documents",
        return_value=_mock_doc_list(),
    ):
        response = client.get("/api/v1/documents")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["documents"][0]["document_name"] == "report.pdf"
    assert body["documents"][0]["chunk_count"] == 12


def test_delete_document(client: TestClient) -> None:
    with patch(
        "app.services.pinecone_service.PineconeService.delete_document",
        return_value=12,
    ):
        response = client.delete("/api/v1/documents/report.pdf")

    assert response.status_code == 200
    body = response.json()
    assert body["chunks_deleted"] == 12


def test_delete_nonexistent_document(client: TestClient) -> None:
    with patch(
        "app.services.pinecone_service.PineconeService.delete_document",
        return_value=0,
    ):
        response = client.delete("/api/v1/documents/ghost.pdf")

    assert response.status_code == 404
