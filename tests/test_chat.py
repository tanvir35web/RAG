from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.models.responses import ChatResponse, Citation


def _make_mock_response() -> ChatResponse:
    return ChatResponse(
        answer="The document discusses testing.",
        citations=[
            Citation(
                document_name="report.pdf",
                page_number=2,
                chunk_id="report.pdf_p2_c0",
                text_excerpt="Testing is important...",
                relevance_score=0.92,
            )
        ],
        model="gpt-4o-mini",
        usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )


def test_chat_returns_answer(client: TestClient) -> None:
    with patch(
        "app.services.chat_service.ChatService.answer",
        new_callable=AsyncMock,
        return_value=_make_mock_response(),
    ):
        response = client.post(
            "/api/v1/chat",
            json={"question": "What does the document say?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert isinstance(body["citations"], list)
    assert body["citations"][0]["document_name"] == "report.pdf"


def test_chat_rejects_empty_question(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"question": ""})
    assert response.status_code == 422


def test_chat_rejects_too_long_question(client: TestClient) -> None:
    response = client.post("/api/v1/chat", json={"question": "x" * 2001})
    assert response.status_code == 422


def test_chat_invalid_top_k(client: TestClient) -> None:
    response = client.post(
        "/api/v1/chat",
        json={"question": "valid question", "top_k": 0},
    )
    assert response.status_code == 422
