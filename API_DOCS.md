# PDF RAG API — Frontend Integration Guide

> **Version**: 1.0.0  
> **Base URL (production)**: `https://rag-api.onrender.com`  
> **Base URL (local dev)**: `http://localhost:8000`  
> **Interactive docs (Swagger)**: `{BASE_URL}/docs`  
> **Interactive docs (ReDoc)**: `{BASE_URL}/redoc`

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [CORS](#cors)
4. [Base URL & Versioning](#base-url--versioning)
5. [Error Handling](#error-handling)
6. [Endpoints](#endpoints)
   - [Health Check](#1-health-check)
   - [Upload PDF](#2-upload-pdf)
   - [Chat / Ask a Question](#3-chat--ask-a-question)
   - [List Documents](#4-list-documents)
   - [Delete Document](#5-delete-document)
7. [Data Models](#data-models)
8. [End-to-End Frontend Flow](#end-to-end-frontend-flow)
9. [JavaScript / TypeScript Examples](#javascript--typescript-examples)

---

## Overview

This API implements a **Retrieval-Augmented Generation (RAG)** system. The general workflow is:

1. **Upload** one or more PDF files — the API extracts text, chunks it, generates embeddings, and stores them in a vector database.
2. **Ask questions** in plain English — the API finds the most relevant chunks from uploaded PDFs and uses an LLM to generate a grounded, cited answer.
3. **Manage documents** — list all uploaded PDFs or delete them when no longer needed.

---

## Authentication

**None.** The API is fully open. No API keys, tokens, or session headers are required from the frontend.

---

## CORS

The API accepts requests from **any origin** with any headers and methods. No special CORS setup is needed on the frontend side.

---

## Base URL & Versioning

All API endpoints (except `/health`) are prefixed with `/api/v1`.

```
GET  /health                              ← no prefix
POST /api/v1/upload                       ← PDF upload
POST /api/v1/chat                         ← ask a question
GET  /api/v1/documents                    ← list documents
DEL  /api/v1/documents/{document_name}    ← delete a document
```

---

## Error Handling

All errors follow the standard FastAPI error shape:

```json
{
  "detail": "Human-readable error message."
}
```

| HTTP Status | Meaning | When it happens |
|-------------|---------|-----------------|
| `400` | Bad Request | Malformed input |
| `404` | Not Found | Document doesn't exist |
| `413` | Payload Too Large | File exceeds 50 MB |
| `415` | Unsupported Media Type | Uploaded file is not a PDF |
| `422` | Unprocessable Entity | Validation failed (wrong type, value out of range, empty question, etc.) |
| `502` | Bad Gateway | External service failure (Gemini or Pinecone is down / unreachable) |
| `500` | Internal Server Error | Unexpected server-side error |

**Frontend recommendation:** Always check for non-2xx status codes and display `response.detail` to the user.

---

## Endpoints

---

### 1. Health Check

Use this to verify the API is running before making other calls.

```
GET /health
```

**Request:** No body, no parameters.

**Response — `200 OK`**

```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2024-12-19T10:30:45.123456+00:00",
  "services": {
    "api": "ok"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"ok"` when the server is up |
| `version` | `string` | API version string |
| `timestamp` | `string` (ISO 8601) | Server time at the moment of the request |
| `services` | `object` | Map of service name → status string |

---

### 2. Upload PDF

Uploads a PDF file. The server extracts text, splits it into chunks, generates embeddings, and stores everything in the vector database. This is an async-heavy operation — expect **5–30 seconds** depending on file size.

```
POST /api/v1/upload
Content-Type: multipart/form-data
```

**Request body — `multipart/form-data`**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | `File` | Yes | A `.pdf` file. Max size: **50 MB**. |

**Constraints checked by the server:**
- File extension must be `.pdf`
- Content-Type must be `application/pdf`
- File must not be empty
- File must not exceed 50 MB
- The PDF must contain extractable text (not a scanned image-only PDF)

**Response — `201 Created`**

```json
{
  "document_name": "annual_report_2024.pdf",
  "chunks_created": 45,
  "pages_processed": 12,
  "message": "Successfully ingested 'annual_report_2024.pdf' (45 chunks across 12 pages)."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `document_name` | `string` | Original filename of the uploaded PDF |
| `chunks_created` | `integer` | Number of text chunks stored in the vector DB |
| `pages_processed` | `integer` | Number of pages extracted from the PDF |
| `message` | `string` | Human-readable success summary |

**Error responses:**

| Status | Example `detail` | Cause |
|--------|-----------------|-------|
| `415` | `"Only PDF files are accepted. Got: image/png"` | Wrong file type |
| `413` | `"File exceeds 50 MB limit."` | File too large |
| `422` | `"File must have a .pdf extension."` | Wrong extension |
| `422` | `"Uploaded file is empty."` | Zero-byte file |
| `422` | `"No text could be extracted from the PDF."` | Scanned/image PDF with no text layer |
| `422` | `"Failed to process PDF: {reason}"` | Corrupt or unreadable PDF |
| `502` | `"Failed to generate embeddings."` | Gemini API unreachable |
| `502` | `"Failed to store vectors in Pinecone."` | Pinecone unreachable |
| `500` | `"An unexpected error occurred."` | Unknown server error |

---

### 3. Chat / Ask a Question

Sends a natural-language question. The API embeds the question, retrieves the most relevant document chunks, then uses an LLM to generate a grounded answer with source citations. Expect **3–15 seconds** for a response.

```
POST /api/v1/chat
Content-Type: application/json
```

**Request body — JSON**

```json
{
  "question": "What were the key revenue drivers in Q3?",
  "top_k": 5,
  "temperature": 0.2
}
```

| Field | Type | Required | Default | Constraints | Description |
|-------|------|----------|---------|-------------|-------------|
| `question` | `string` | Yes | — | Min 1 char, max 2000 chars | The question to ask |
| `top_k` | `integer` | No | `5` | Min 1, max 20 | How many document chunks to retrieve as context |
| `temperature` | `float` | No | `0.2` | Min 0.0, max 2.0 | LLM creativity. Lower = more factual, higher = more creative |

**Response — `200 OK`**

```json
{
  "answer": "Revenue in Q3 was primarily driven by the expansion of the SaaS segment, which grew 34% year-over-year according to the financial statements.",
  "citations": [
    {
      "document_name": "annual_report_2024.pdf",
      "page_number": 7,
      "chunk_id": "annual_report_2024.pdf_p7_c2",
      "text_excerpt": "The SaaS segment achieved 34% year-over-year growth in Q3, becoming the primary revenue driver...",
      "relevance_score": 0.94
    },
    {
      "document_name": "annual_report_2024.pdf",
      "page_number": 8,
      "chunk_id": "annual_report_2024.pdf_p8_c0",
      "text_excerpt": "Total Q3 revenue reached $4.2B, with SaaS contributing 61% of the total compared to 48% in Q3 2023...",
      "relevance_score": 0.87
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

| Field | Type | Description |
|-------|------|-------------|
| `answer` | `string` | The LLM-generated answer |
| `citations` | `Citation[]` | Array of source chunks used to form the answer (see below) |
| `model` | `string` | Name of the LLM model used |
| `usage.prompt_tokens` | `integer` | Tokens in the input (context + question) |
| `usage.completion_tokens` | `integer` | Tokens in the generated answer |
| `usage.total_tokens` | `integer` | Total tokens consumed |

**Citation object:**

| Field | Type | Description |
|-------|------|-------------|
| `document_name` | `string` | Filename of the source PDF |
| `page_number` | `integer` | Page number where this chunk was found |
| `chunk_id` | `string` | Unique identifier: `{filename}_p{page}_c{index}` |
| `text_excerpt` | `string` | First 200 characters of the source chunk |
| `relevance_score` | `float` | Cosine similarity to the question (0.0–1.0). Higher = more relevant. |

**No documents found:**

When no uploaded documents match the question, the API still returns `200 OK` with:

```json
{
  "answer": "No relevant documents found to answer this question.",
  "citations": [],
  "model": "gemini-2.5-flash",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

The frontend should detect `citations.length === 0` and/or check the answer string to show an appropriate empty-state message.

**Error responses:**

| Status | Example `detail` | Cause |
|--------|-----------------|-------|
| `422` | `"String should have at most 2000 characters"` | Question too long |
| `422` | `"Input should be greater than or equal to 1"` | `top_k` below 1 |
| `502` | `"Failed to generate answer. Please try again."` | Gemini API error |
| `500` | `"An unexpected error occurred."` | Unknown server error |

---

### 4. List Documents

Returns all PDFs that have been uploaded and ingested.

```
GET /api/v1/documents
```

**Request:** No body, no parameters.

**Response — `200 OK`**

```json
{
  "documents": [
    {
      "document_name": "annual_report_2024.pdf",
      "chunk_count": 45,
      "uploaded_at": "2024-12-19T10:30:45.123456+00:00",
      "pages": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    },
    {
      "document_name": "product_whitepaper.pdf",
      "chunk_count": 28,
      "uploaded_at": "2024-12-19T11:15:30.654321+00:00",
      "pages": [1, 2, 3, 4, 5, 6, 7, 8]
    }
  ],
  "total": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `documents` | `DocumentInfo[]` | Array of document metadata objects |
| `total` | `integer` | Total number of documents stored |

**DocumentInfo object:**

| Field | Type | Description |
|-------|------|-------------|
| `document_name` | `string` | Original PDF filename |
| `chunk_count` | `integer` | Number of stored text chunks |
| `uploaded_at` | `string \| null` | ISO 8601 upload timestamp, or `null` if unavailable |
| `pages` | `integer[]` | Sorted list of page numbers that have content |

**Error responses:**

| Status | Example `detail` | Cause |
|--------|-----------------|-------|
| `502` | `"Failed to retrieve document list."` | Pinecone unreachable |
| `500` | `"An unexpected error occurred."` | Unknown server error |

---

### 5. Delete Document

Permanently removes all chunks for a given document from the vector database. The original PDF file is not stored on the server — only the embeddings are deleted.

```
DELETE /api/v1/documents/{document_name}
```

**Path parameter:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `document_name` | `string` | Exact filename of the document to delete (e.g. `annual_report_2024.pdf`) |

**URL encode the filename** if it contains spaces or special characters.

**Response — `200 OK`**

```json
{
  "document_name": "annual_report_2024.pdf",
  "chunks_deleted": 45,
  "message": "Deleted 45 chunk(s) for 'annual_report_2024.pdf'."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `document_name` | `string` | The document that was deleted |
| `chunks_deleted` | `integer` | Number of vector chunks removed |
| `message` | `string` | Human-readable confirmation |

**Error responses:**

| Status | Example `detail` | Cause |
|--------|-----------------|-------|
| `422` | `"document_name must not be empty."` | Empty path parameter |
| `404` | `"No document named 'foo.pdf' found."` | Document doesn't exist |
| `502` | `"Failed to delete document."` | Pinecone unreachable |
| `500` | `"An unexpected error occurred."` | Unknown server error |

---

## Data Models

A summary of all types used across the API.

```typescript
// POST /api/v1/chat — request
interface ChatRequest {
  question: string;       // required, 1–2000 chars
  top_k?: number;         // optional, 1–20, default 5
  temperature?: number;   // optional, 0.0–2.0, default 0.2
}

interface Citation {
  document_name: string;
  page_number: number;
  chunk_id: string;
  text_excerpt: string;
  relevance_score: number; // 0.0–1.0
}

interface ChatResponse {
  answer: string;
  citations: Citation[];
  model: string;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

interface UploadResponse {
  document_name: string;
  chunks_created: number;
  pages_processed: number;
  message: string;
}

interface DocumentInfo {
  document_name: string;
  chunk_count: number;
  uploaded_at: string | null; // ISO 8601
  pages: number[];
}

interface DocumentListResponse {
  documents: DocumentInfo[];
  total: number;
}

interface DeleteResponse {
  document_name: string;
  chunks_deleted: number;
  message: string;
}

interface HealthResponse {
  status: string;
  version: string;
  timestamp: string; // ISO 8601
  services: Record<string, string>;
}

// All error responses
interface ErrorResponse {
  detail: string;
}
```

---

## End-to-End Frontend Flow

```
┌─────────────┐                        ┌──────────────────────────┐
│   Frontend  │                        │         API              │
└──────┬──────┘                        └────────────┬─────────────┘
       │                                            │
       │  1. GET /health                            │
       │ ─────────────────────────────────────────>│
       │ <─────────────────────── 200 { status }   │
       │                                            │
       │  2. POST /api/v1/upload (FormData)         │
       │ ─────────────────────────────────────────>│ Extract → Chunk → Embed → Store
       │ <────────── 201 { document_name, chunks }  │
       │                                            │
       │  3. GET /api/v1/documents                  │
       │ ─────────────────────────────────────────>│
       │ <────────── 200 { documents[], total }     │
       │                                            │
       │  4. POST /api/v1/chat { question }         │
       │ ─────────────────────────────────────────>│ Embed → Retrieve → Generate
       │ <────────── 200 { answer, citations[] }    │
       │                                            │
       │  5. DELETE /api/v1/documents/{name}        │
       │ ─────────────────────────────────────────>│
       │ <────────── 200 { chunks_deleted }         │
       │                                            │
```

**Recommended UI states to handle:**

| State | Trigger | UI suggestion |
|-------|---------|--------------|
| Uploading | POST /upload in-flight | Progress bar or spinner, disable the upload button |
| Processing | Upload returned 201 | Show chunk/page counts; document is now queryable |
| Asking | POST /chat in-flight | Skeleton loader or typing indicator |
| No results | `citations.length === 0` | "No relevant content found" empty state |
| Service error | 502 response | "Service temporarily unavailable, please try again" toast |
| Validation error | 422 response | Inline field error using `detail` message |

---

## JavaScript / TypeScript Examples

### Check API health

```typescript
const BASE_URL = "https://rag-api.onrender.com";

async function checkHealth() {
  const res = await fetch(`${BASE_URL}/health`);
  const data = await res.json();
  console.log(data.status); // "ok"
}
```

### Upload a PDF

```typescript
async function uploadPDF(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/api/v1/upload`, {
    method: "POST",
    body: formData,
    // Do NOT set Content-Type manually — the browser sets it automatically
    // with the correct multipart boundary when using FormData.
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }

  return await res.json(); // UploadResponse
}
```

### Ask a question

```typescript
async function askQuestion(question: string, topK = 5) {
  const res = await fetch(`${BASE_URL}/api/v1/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }

  return await res.json(); // ChatResponse
}

// Usage
const result = await askQuestion("What were the key findings?");
console.log(result.answer);
result.citations.forEach((c) => {
  console.log(`Source: ${c.document_name}, page ${c.page_number} (score: ${c.relevance_score})`);
});
```

### List all documents

```typescript
async function listDocuments() {
  const res = await fetch(`${BASE_URL}/api/v1/documents`);

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }

  return await res.json(); // DocumentListResponse
}
```

### Delete a document

```typescript
async function deleteDocument(documentName: string) {
  const encoded = encodeURIComponent(documentName);

  const res = await fetch(`${BASE_URL}/api/v1/documents/${encoded}`, {
    method: "DELETE",
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail);
  }

  return await res.json(); // DeleteResponse
}
```

### Centralised API client (recommended pattern)

```typescript
const BASE_URL = "https://rag-api.onrender.com";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(body.detail ?? "Unknown error");
  }

  return res.json() as Promise<T>;
}

export const api = {
  health: () =>
    apiFetch<HealthResponse>("/health"),

  upload: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiFetch<UploadResponse>("/api/v1/upload", { method: "POST", body: fd });
  },

  chat: (question: string, top_k = 5, temperature = 0.2) =>
    apiFetch<ChatResponse>("/api/v1/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k, temperature }),
    }),

  listDocuments: () =>
    apiFetch<DocumentListResponse>("/api/v1/documents"),

  deleteDocument: (name: string) =>
    apiFetch<DeleteResponse>(`/api/v1/documents/${encodeURIComponent(name)}`, {
      method: "DELETE",
    }),
};
```

---

*For questions or issues, refer to the interactive Swagger UI at `{BASE_URL}/docs` which always reflects the live schema.*
