import io
from dataclasses import dataclass

from pypdf import PdfReader

from app.config import Settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TextChunk:
    text: str
    page_number: int
    chunk_index: int
    document_name: str

    @property
    def chunk_id(self) -> str:
        return f"{self.document_name}_p{self.page_number}_c{self.chunk_index}"


class PDFService:
    def __init__(self, settings: Settings) -> None:
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap

    def extract_text_by_page(self, pdf_bytes: bytes) -> dict[int, str]:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages: dict[int, str] = {}

        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                pages[page_num] = text

        logger.info("pdf_text_extracted", pages_with_text=len(pages), total_pages=len(reader.pages))
        return pages

    def chunk_text(self, text: str, page_number: int, document_name: str) -> list[TextChunk]:
        chunks: list[TextChunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Avoid cutting mid-word: walk back to last space
            if end < len(text) and not text[end].isspace():
                last_space = chunk_text.rfind(" ")
                if last_space > self.chunk_size // 2:
                    chunk_text = chunk_text[:last_space]
                    end = start + last_space

            chunk_text = chunk_text.strip()
            if chunk_text:
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        document_name=document_name,
                    )
                )
                chunk_index += 1

            start = end - self.chunk_overlap if end < len(text) else len(text)

        return chunks

    def process_pdf(self, pdf_bytes: bytes, document_name: str) -> list[TextChunk]:
        pages = self.extract_text_by_page(pdf_bytes)
        all_chunks: list[TextChunk] = []

        for page_number, text in pages.items():
            page_chunks = self.chunk_text(text, page_number, document_name)
            all_chunks.extend(page_chunks)

        logger.info(
            "pdf_processed",
            document_name=document_name,
            total_chunks=len(all_chunks),
            pages=len(pages),
        )
        return all_chunks
