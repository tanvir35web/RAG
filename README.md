# PDF RAG API

Production-ready Retrieval-Augmented Generation API built with FastAPI, Google Gemini, and Pinecone. Upload PDFs and query them in natural language with source citations.

## System Architecture

![System Architecture](https://i.ibb.co.com/Kzr8TQvf/Chat-GPT-Image-Jun-2-2026-10-52-12-PM.png)

## Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Embeddings | Gemini `gemini-embedding-2` (768-dim) |
| Generation | Gemini `gemini-2.5-flash` |
| Vector Store | Pinecone Serverless |
| PDF Parsing | pypdf |
| Logging | structlog (JSON) |
| Deployment | Render |

## Architecture

```
app/
├── main.py                   # FastAPI factory, CORS, global error handler, lifespan
├── config.py                 # Pydantic-settings v2 (env-based)
├── dependencies.py           # Singleton service wiring via module-level globals
├── models/
│   ├── requests.py           # ChatRequest
│   └── responses.py          # ChatResponse, Citation, DocumentInfo, UploadResponse, …
├── routers/
│   ├── upload.py             # POST /api/v1/upload
│   ├── chat.py               # POST /api/v1/chat
│   ├── documents.py          # GET/DELETE /api/v1/documents
│   └── health.py             # GET /health
├── services/
│   ├── pdf_service.py        # PDF extraction + word-boundary-aware chunking
│   ├── embedding_service.py  # Gemini gemini-embedding-2 (batched, async)
│   ├── pinecone_service.py   # Upsert / query / list / delete with metadata
│   └── chat_service.py       # RAG pipeline: embed → retrieve → prompt → generate
└── utils/
    └── logging.py            # Structured JSON logging
```

## Quick Start

### 1. Clone and install

```bash
git clone <repo>
cd rag-api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — fill in your API keys
```

**Required keys:**

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/app/apikey |
| `PINECONE_API_KEY` | https://app.pinecone.io |
| `PINECONE_INDEX` | Any name, e.g. `rag-documents` (auto-created on first run) |

### 3. Run locally

```bash
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

> On first startup the Pinecone index is created automatically (~10–30 seconds). Subsequent starts are instant.

---

## API Reference

### `GET /health`

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2026-06-02T15:00:00Z",
  "services": {"api": "ok"}
}
```

---

### `POST /api/v1/upload`

Upload and ingest a PDF. Text is extracted, chunked, embedded, and stored in Pinecone.

```bash
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@report.pdf"
```

```json
{
  "document_name": "report.pdf",
  "chunks_created": 42,
  "pages_processed": 8,
  "message": "Successfully ingested 'report.pdf' (42 chunks across 8 pages)."
}
```

**Limits:**
- PDF only (`.pdf`, `application/pdf`)
- Max 50 MB (configurable via `MAX_FILE_SIZE_MB`)

---

### `POST /api/v1/chat`

Ask a question against all ingested documents.

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the main findings?", "top_k": 5}'
```

```json
{
  "answer": "The main findings indicate...",
  "citations": [
    {
      "document_name": "report.pdf",
      "page_number": 3,
      "chunk_id": "report.pdf_p3_c0",
      "text_excerpt": "Key findings indicate...",
      "relevance_score": 0.9124
    }
  ],
  "model": "gemini-2.5-flash",
  "usage": {
    "prompt_tokens": 512,
    "completion_tokens": 128,
    "total_tokens": 640
  }
}
```

**Request body:**

| Field | Type | Default | Description |
|---|---|---|---|
| `question` | string | required | Natural language question (max 2000 chars) |
| `top_k` | int | 5 | Number of chunks to retrieve (1–20) |
| `temperature` | float | 0.2 | Generation temperature (0.0–2.0) |

---

### `GET /api/v1/documents`

List all ingested documents with chunk counts and page numbers.

```bash
curl http://localhost:8000/api/v1/documents
```

```json
{
  "documents": [
    {
      "document_name": "report.pdf",
      "chunk_count": 42,
      "pages": [1, 2, 3, 4, 5],
      "uploaded_at": "2026-06-02T15:00:00Z"
    }
  ],
  "total": 1
}
```

---

### `DELETE /api/v1/documents/{document_name}`

Remove all Pinecone vectors for a specific document.

```bash
curl -X DELETE "http://localhost:8000/api/v1/documents/report.pdf"
```

```json
{
  "document_name": "report.pdf",
  "chunks_deleted": 42,
  "message": "Deleted 42 chunk(s) for 'report.pdf'."
}
```

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `GEMINI_API_KEY` | **required** | Google AI Studio API key |
| `PINECONE_API_KEY` | **required** | Pinecone API key |
| `PINECONE_INDEX` | **required** | Pinecone index name |
| `GEMINI_EMBEDDING_MODEL` | `gemini-embedding-2` | Embedding model |
| `GEMINI_CHAT_MODEL` | `gemini-2.5-flash` | Chat completion model |
| `GEMINI_EMBEDDING_DIMENSIONS` | `768` | Output vector size (128–3072) |
| `PINECONE_NAMESPACE` | `documents` | Pinecone namespace |
| `PINECONE_TOP_K` | `5` | Default retrieval count |
| `CHUNK_SIZE` | `1000` | Characters per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `MAX_FILE_SIZE_MB` | `50` | Max upload size in MB |
| `APP_ENV` | `development` | `development` / `production` / `testing` |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Running Tests

```bash
pytest -v
```

Tests use mocked Pinecone and Gemini clients — no real API calls are made.

---

## Deploy to Render

1. Push this repo to GitHub.
2. In the Render dashboard, create a **Web Service** and connect your repo.
3. Render auto-detects `render.yaml`. Add your secret environment variables via the dashboard:
   - `GEMINI_API_KEY`
   - `PINECONE_API_KEY`
   - `PINECONE_INDEX`
4. Deploy — `render.yaml` handles the build and start commands.

The `render.yaml` is pre-configured with:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `GET /health`
