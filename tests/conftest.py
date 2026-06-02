from typing import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture(scope="session")
def mock_settings() -> Settings:
    return Settings(
        gemini_api_key="AIza-test-key",
        pinecone_api_key="pc-test-key",
        pinecone_index="test-index",
        app_env="testing",
        log_level="WARNING",
    )


@pytest.fixture(scope="session")
def client(mock_settings: Settings) -> Generator[TestClient, None, None]:
    with (
        patch("app.services.pinecone_service.Pinecone") as mock_pc,
        patch("app.config.get_settings", return_value=mock_settings),
        patch("app.dependencies.get_settings", return_value=mock_settings),
    ):
        mock_index = MagicMock()
        mock_index.describe_index_stats.return_value = {"namespaces": {}}
        mock_index.query.return_value = {"matches": []}
        mock_index.upsert.return_value = None
        mock_index.delete.return_value = None
        mock_index.list.return_value = iter([])
        mock_index.fetch.return_value = {"vectors": {}}

        mock_pc_instance = MagicMock()
        mock_pc_instance.list_indexes.return_value = []
        mock_pc_instance.Index.return_value = mock_index
        mock_pc.return_value = mock_pc_instance

        from app.main import create_app

        test_app = create_app()
        with TestClient(test_app, raise_server_exceptions=False) as c:
            yield c


@pytest.fixture
def minimal_pdf_bytes() -> bytes:
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]\n"
        b"   /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 12 Tf 72 720 Td (Hello World) Tj ET\nendstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n0000000274 00000 n \n"
        b"0000000370 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n450\n%%EOF"
    )
