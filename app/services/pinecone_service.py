from datetime import datetime, timezone
from typing import Any

from pinecone import Pinecone, ServerlessSpec

from app.config import Settings
from app.services.pdf_service import TextChunk
from app.utils.logging import get_logger

logger = get_logger(__name__)

_UPSERT_BATCH_SIZE = 100


class PineconeService:
    def __init__(self, settings: Settings) -> None:
        self._pc = Pinecone(api_key=settings.pinecone_api_key)
        self._index_name = settings.pinecone_index
        self._namespace = settings.pinecone_namespace
        self._dimensions = settings.gemini_embedding_dimensions
        self._index = self._get_or_create_index()

    def _get_or_create_index(self) -> Any:
        existing = [idx.name for idx in self._pc.list_indexes()]
        if self._index_name not in existing:
            logger.info("creating_pinecone_index", index=self._index_name)
            self._pc.create_index(
                name=self._index_name,
                dimension=self._dimensions,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        return self._pc.Index(self._index_name)

    async def upsert_chunks(
        self,
        chunks: list[TextChunk],
        embeddings: list[list[float]],
        uploaded_at: datetime | None = None,
    ) -> int:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")

        ts = (uploaded_at or datetime.now(timezone.utc)).isoformat()
        vectors = [
            {
                "id": chunk.chunk_id,
                "values": embedding,
                "metadata": {
                    "document_name": chunk.document_name,
                    "page_number": chunk.page_number,
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "uploaded_at": ts,
                },
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]

        total_upserted = 0
        for i in range(0, len(vectors), _UPSERT_BATCH_SIZE):
            batch = vectors[i : i + _UPSERT_BATCH_SIZE]
            self._index.upsert(vectors=batch, namespace=self._namespace)
            total_upserted += len(batch)

        logger.info("vectors_upserted", count=total_upserted)
        return total_upserted

    def query(
        self,
        embedding: list[float],
        top_k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        result = self._index.query(
            vector=embedding,
            top_k=top_k,
            include_metadata=True,
            namespace=self._namespace,
            filter=filter_dict,
        )
        return result.get("matches", [])

    def list_documents(self) -> list[dict[str, Any]]:
        stats = self._index.describe_index_stats()
        namespace_stats = stats.get("namespaces", {}).get(self._namespace, {})
        total_vectors = namespace_stats.get("vector_count", 0)

        # Fetch all vector IDs via pagination and aggregate by document_name
        documents: dict[str, dict[str, Any]] = {}

        try:
            for ids_page in self._index.list(namespace=self._namespace):
                if not ids_page:
                    continue
                fetch_result = self._index.fetch(ids=ids_page, namespace=self._namespace)
                for _id, vector_data in fetch_result.get("vectors", {}).items():
                    meta = vector_data.get("metadata", {})
                    doc_name = meta.get("document_name", "unknown")
                    page_num = meta.get("page_number", 0)

                    if doc_name not in documents:
                        documents[doc_name] = {
                            "document_name": doc_name,
                            "chunk_count": 0,
                            "pages": set(),
                            "uploaded_at": meta.get("uploaded_at"),
                        }
                    documents[doc_name]["chunk_count"] += 1
                    documents[doc_name]["pages"].add(page_num)
        except Exception:
            logger.warning("list_documents_fallback", total_vectors=total_vectors)

        result_list = []
        for doc in documents.values():
            doc["pages"] = sorted(doc["pages"])
            result_list.append(doc)

        return result_list

    def delete_document(self, document_name: str) -> int:
        # Fetch IDs matching document_name via metadata filter
        dummy_query = self._index.query(
            vector=[0.0] * self._dimensions,
            top_k=10000,
            include_metadata=False,
            namespace=self._namespace,
            filter={"document_name": {"$eq": document_name}},
        )
        ids_to_delete = [match["id"] for match in dummy_query.get("matches", [])]

        if ids_to_delete:
            self._index.delete(ids=ids_to_delete, namespace=self._namespace)

        logger.info("document_deleted", document_name=document_name, chunks_deleted=len(ids_to_delete))
        return len(ids_to_delete)
