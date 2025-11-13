# Data Model: RAG Q&A System

**Feature**: 001-rag-qa-system
**Date**: 2025-11-13
**Source**: Extracted from [spec.md](./spec.md) Key Entities section

## Overview

This document defines the data model for the RAG-based Question Answering System. The model supports document ingestion, vector storage, query processing, answer generation, escalation workflows, and audit logging.

**Design Principles**:
- **Immutability**: Most entities are append-only (audit trail)
- **Traceability**: All entities have UUIDs and timestamps for correlation
- **Metadata-rich**: Extensive metadata for filtering, analytics, and debugging
- **Scalability**: Designed for horizontal partitioning (documents by collection, queries by date)

---

## Entity Relationship Diagram

```
┌─────────────┐
│  Document   │
└──────┬──────┘
       │ 1:N
       ▼
┌─────────────┐      ┌──────────────┐
│    Chunk    │◄────►│  Collection  │
└──────┬──────┘  N:1 └──────────────┘
       │ N:M
       │ (via QueryResult)
       │
       ▼
┌─────────────┐      ┌─────────────┐
│    Query    │─────►│   Answer    │
└──────┬──────┘  1:1 └─────────────┘
       │ 1:N           (optional)
       ▼
┌─────────────┐
│ QueryResult │
└─────────────┘
       │ N:1
       ▼
┌─────────────┐
│    Chunk    │
└─────────────┘

┌─────────────┐      ┌─────────────┐
│    Query    │─────►│ Escalation  │
└─────────────┘  1:1 │   Request   │
                     └─────────────┘
                          (optional)

┌─────────────┐
│  Embedding  │
│     Job     │
└──────┬──────┘
       │ M:N
       ▼
┌─────────────┐
│  Document   │
└─────────────┘

┌─────────────┐
│ AuditEvent  │  (references any entity)
└─────────────┘
```

---

## Core Entities

### 1. Document

Represents a source file ingested into the knowledge base.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `file_name` | String(255) | NOT NULL | Original file name (e.g., "olist_reviews.csv") |
| `file_format` | Enum | NOT NULL | File type: CSV, PDF, DOCX, TXT, MD |
| `file_size_bytes` | Integer | NOT NULL | File size in bytes |
| `upload_timestamp` | DateTime | NOT NULL, Indexed | When document was uploaded (ISO 8601 UTC) |
| `detected_language` | String(10) | NOT NULL | Language code (e.g., "pt-BR", "en-US") |
| `processing_status` | Enum | NOT NULL, Indexed | pending, processing, completed, failed |
| `chunk_count` | Integer | NULL | Number of chunks created (NULL if processing) |
| `collection_name` | String(100) | NOT NULL, FK → Collection | Which collection vectors belong to |
| `error_message` | Text | NULL | Error details if processing_status = failed |
| `metadata` | JSONB | NOT NULL | Custom metadata (uploader_id, tags, etc.) |

**Indexes**:
- Primary: `id`
- Secondary: `processing_status`, `upload_timestamp`, `collection_name`

**Relationships**:
- One Document has many Chunks (1:N)
- One Document belongs to one Collection (N:1)
- One Document referenced by many EmbeddingJobs (M:N)

**State Transitions**:
```
pending → processing → completed
pending → processing → failed

Failed documents can be retried:
failed → pending (manual re-ingestion)
```

**Validation Rules**:
- `file_size_bytes` must be > 0 and < 2GB (platform limit)
- `file_name` must not contain path separators (security)
- `detected_language` must be valid ISO 639-1 code
- If `processing_status = completed`, `chunk_count` must be > 0
- If `processing_status = failed`, `error_message` must be NOT NULL

**Example**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "olist_order_reviews_dataset.csv",
  "file_format": "CSV",
  "file_size_bytes": 52428800,
  "upload_timestamp": "2025-11-13T10:30:00Z",
  "detected_language": "pt-BR",
  "processing_status": "completed",
  "chunk_count": 12543,
  "collection_name": "olist_reviews",
  "error_message": null,
  "metadata": {
    "uploader_id": "admin",
    "source": "kaggle",
    "dataset_version": "1.0"
  }
}
```

---

### 2. Chunk

Represents a processed text segment with vector embedding.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `document_id` | UUID | FK → Document, NOT NULL, Indexed | Source document |
| `text_content` | Text | NOT NULL | Chunk text (after PII redaction) |
| `vector_embedding` | Float[] | NOT NULL, Dimension per model | Vector representation (1536 for ada-002, 768 for sentence-transformers) |
| `sequence_position` | Integer | NOT NULL | Position in source document (0-indexed) |
| `token_count` | Integer | NOT NULL | Number of tokens in chunk |
| `char_start_offset` | Integer | NOT NULL | Character offset in original document |
| `char_end_offset` | Integer | NOT NULL | Character offset in original document |
| `extracted_metadata` | JSONB | NOT NULL | Detected entities, keywords, headings |
| `creation_timestamp` | DateTime | NOT NULL, Indexed | When chunk was created (ISO 8601 UTC) |
| `language_code` | String(10) | NOT NULL | Language code (inherited from document) |

**Indexes**:
- Primary: `id`
- Secondary: `document_id`, `creation_timestamp`
- Vector index: `vector_embedding` (HNSW in Qdrant)

**Relationships**:
- One Chunk belongs to one Document (N:1)
- One Chunk appears in many QueryResults (1:N)

**Validation Rules**:
- `text_content` must not be empty
- `token_count` must be > 0 and <= 1024 (max chunk size)
- `char_end_offset` > `char_start_offset`
- `sequence_position` must be unique per `document_id`
- `vector_embedding` dimension must match collection configuration

**Example**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "text_content": "O produto chegou com defeito e o atendimento foi péssimo. Não recomendo.",
  "vector_embedding": [0.023, -0.145, 0.678, ...],
  "sequence_position": 42,
  "token_count": 18,
  "char_start_offset": 5240,
  "char_end_offset": 5320,
  "extracted_metadata": {
    "sentiment": "negative",
    "entities": ["produto", "atendimento"],
    "heading": null
  },
  "creation_timestamp": "2025-11-13T10:35:12Z",
  "language_code": "pt-BR"
}
```

---

### 3. Query

Represents a user question submitted to the system.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `query_text` | Text | NOT NULL | User's original question |
| `query_embedding` | Float[] | NOT NULL | Vector representation of query |
| `user_id` | String(100) | NULL, Indexed | User identifier (if authenticated) |
| `submission_timestamp` | DateTime | NOT NULL, Indexed | When query was submitted (ISO 8601 UTC) |
| `detected_language` | String(10) | NOT NULL | Detected query language |
| `processing_status` | Enum | NOT NULL, Indexed | pending, processing, completed, failed, escalated |
| `assigned_worker_id` | String(100) | NULL | Worker that processed query |
| `session_correlation_id` | String(100) | NULL, Indexed | Session ID for multi-turn conversations |
| `metadata` | JSONB | NOT NULL | IP address, user agent, custom fields |

**Indexes**:
- Primary: `id`
- Secondary: `user_id`, `submission_timestamp`, `processing_status`, `session_correlation_id`

**Relationships**:
- One Query has many QueryResults (1:N)
- One Query has one Answer (1:1, optional)
- One Query has one EscalationRequest (1:1, optional)

**State Transitions**:
```
pending → processing → completed
pending → processing → failed
pending → processing → escalated

Completed queries can be escalated later:
completed → escalated (user requests human help)
```

**Validation Rules**:
- `query_text` must not be empty and <= 1000 characters
- `query_embedding` dimension must match model configuration
- If `processing_status = completed`, must have associated Answer
- If `processing_status = escalated`, must have associated EscalationRequest

**Example**:
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "query_text": "Quais são os principais motivos de avaliações negativas?",
  "query_embedding": [-0.012, 0.234, -0.567, ...],
  "user_id": "user_12345",
  "submission_timestamp": "2025-11-13T14:22:30Z",
  "detected_language": "pt-BR",
  "processing_status": "completed",
  "assigned_worker_id": "query-worker-03",
  "session_correlation_id": "sess_abc123",
  "metadata": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "request_id": "req_xyz789"
  }
}
```

---

### 4. QueryResult

Represents a retrieved chunk relevant to a query (many-to-many link between Query and Chunk).

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `query_id` | UUID | FK → Query, NOT NULL, Indexed | Query reference |
| `chunk_id` | UUID | FK → Chunk, NOT NULL, Indexed | Retrieved chunk reference |
| `relevance_score` | Float | NOT NULL, Range [0, 1] | Vector similarity score |
| `reranking_score` | Float | NULL, Range [0, 1] | Cross-encoder score (if reranking used) |
| `rank_position` | Integer | NOT NULL | Position in retrieval results (1-indexed) |
| `retrieval_timestamp` | DateTime | NOT NULL | When retrieval occurred (ISO 8601 UTC) |
| `metadata_match_flags` | JSONB | NOT NULL | Boolean flags for metadata filters applied |

**Indexes**:
- Primary: `id`
- Secondary: `query_id`, `chunk_id`
- Composite: `(query_id, rank_position)` for ordered retrieval

**Relationships**:
- One QueryResult belongs to one Query (N:1)
- One QueryResult references one Chunk (N:1)

**Validation Rules**:
- `relevance_score` must be in [0, 1]
- `reranking_score` must be in [0, 1] or NULL
- `rank_position` must be > 0 and unique per `query_id`
- If `reranking_score` is NOT NULL, it should be used for ranking (not `relevance_score`)

**Example**:
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "query_id": "770e8400-e29b-41d4-a716-446655440002",
  "chunk_id": "660e8400-e29b-41d4-a716-446655440001",
  "relevance_score": 0.87,
  "reranking_score": 0.92,
  "rank_position": 1,
  "retrieval_timestamp": "2025-11-13T14:22:31Z",
  "metadata_match_flags": {
    "language_match": true,
    "date_filter_applied": false,
    "collection_filter_applied": true
  }
}
```

---

### 5. Answer

Represents a generated response to a query.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `query_id` | UUID | FK → Query, NOT NULL, Unique, Indexed | Query reference (1:1) |
| `answer_text` | Text | NOT NULL | LLM-generated response |
| `confidence_score` | Float | NOT NULL, Range [0, 1] | Composite confidence metric |
| `generation_timestamp` | DateTime | NOT NULL, Indexed | When answer was generated (ISO 8601 UTC) |
| `llm_model_used` | String(50) | NOT NULL | Model name (e.g., "gpt-4o-mini") |
| `token_count_input` | Integer | NOT NULL | Input tokens consumed |
| `token_count_output` | Integer | NOT NULL | Output tokens consumed |
| `latency_retrieval_ms` | Integer | NOT NULL | Retrieval time in milliseconds |
| `latency_generation_ms` | Integer | NOT NULL | LLM generation time in milliseconds |
| `latency_total_ms` | Integer | NOT NULL | End-to-end latency |
| `cache_hit` | Boolean | NOT NULL | True if answer was cached |
| `validation_status` | Enum | NOT NULL | passed, failed, warnings |
| `escalation_flag` | Boolean | NOT NULL | True if low confidence (suggest escalation) |
| `redaction_flag` | Boolean | NOT NULL | True if PII was redacted from answer |
| `metadata` | JSONB | NOT NULL | Confidence breakdown, validation details |

**Indexes**:
- Primary: `id`
- Secondary: `query_id`, `generation_timestamp`, `confidence_score`

**Relationships**:
- One Answer belongs to one Query (1:1)

**Validation Rules**:
- `answer_text` must not be empty
- `confidence_score` must be in [0, 1]
- `token_count_input` and `token_count_output` must be > 0
- `latency_total_ms` >= `latency_retrieval_ms` + `latency_generation_ms`
- If `cache_hit = true`, `latency_generation_ms` should be ~0
- If `escalation_flag = true`, `confidence_score` should be < 0.7 (threshold)

**Example**:
```json
{
  "id": "990e8400-e29b-41d4-a716-446655440004",
  "query_id": "770e8400-e29b-41d4-a716-446655440002",
  "answer_text": "Com base nas avaliações, os principais motivos de reclamações negativas são: 1) Atraso na entrega (45%), 2) Produto com defeito (30%), 3) Atendimento ao cliente ruim (15%), 4) Embalagem danificada (10%).",
  "confidence_score": 0.85,
  "generation_timestamp": "2025-11-13T14:22:33Z",
  "llm_model_used": "gpt-4o-mini",
  "token_count_input": 520,
  "token_count_output": 85,
  "latency_retrieval_ms": 120,
  "latency_generation_ms": 450,
  "latency_total_ms": 620,
  "cache_hit": false,
  "validation_status": "passed",
  "escalation_flag": false,
  "redaction_flag": false,
  "metadata": {
    "confidence_breakdown": {
      "retrieval_score": 0.87,
      "generation_perplexity": 0.92,
      "context_coverage": 0.80
    },
    "validation_checks": {
      "hallucination": "passed",
      "pii_leakage": "passed",
      "policy_compliance": "passed"
    }
  }
}
```

---

### 6. EscalationRequest

Represents a query escalated to human support.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `query_id` | UUID | FK → Query, NOT NULL, Unique, Indexed | Query reference (1:1) |
| `answer_id` | UUID | FK → Answer, NULL | Answer reference (if answer was attempted) |
| `escalation_reason` | Enum | NOT NULL | low_confidence, validation_failure, user_request |
| `confidence_score_at_escalation` | Float | NULL, Range [0, 1] | Confidence score when escalated |
| `escalation_timestamp` | DateTime | NOT NULL, Indexed | When escalation occurred (ISO 8601 UTC) |
| `priority_score` | Float | NOT NULL, Range [0, 1] | Calculated priority (0=low, 1=critical) |
| `assignment_status` | Enum | NOT NULL, Indexed | queued, assigned, resolved |
| `assigned_agent_id` | String(100) | NULL, Indexed | Support agent ID (if assigned) |
| `resolution_timestamp` | DateTime | NULL | When request was resolved |
| `agent_feedback` | Text | NULL | Agent's notes or correct answer |
| `metadata` | JSONB | NOT NULL | Validation failures, user context |

**Indexes**:
- Primary: `id`
- Secondary: `query_id`, `escalation_timestamp`, `assignment_status`, `assigned_agent_id`
- Priority queue: `(assignment_status, priority_score DESC)` for fetching next task

**Relationships**:
- One EscalationRequest belongs to one Query (1:1)
- One EscalationRequest may reference one Answer (1:1, optional)

**State Transitions**:
```
queued → assigned → resolved

Assigned requests can be re-queued:
assigned → queued (agent unavailable)
```

**Validation Rules**:
- If `escalation_reason = low_confidence`, `confidence_score_at_escalation` must be NOT NULL and < 0.7
- If `assignment_status = assigned`, `assigned_agent_id` must be NOT NULL
- If `assignment_status = resolved`, `resolution_timestamp` must be NOT NULL
- `priority_score` calculated from: wait_time, confidence_score_gap, validation_failure_severity

**Example**:
```json
{
  "id": "aa0e8400-e29b-41d4-a716-446655440005",
  "query_id": "770e8400-e29b-41d4-a716-446655440002",
  "answer_id": "990e8400-e29b-41d4-a716-446655440004",
  "escalation_reason": "low_confidence",
  "confidence_score_at_escalation": 0.62,
  "escalation_timestamp": "2025-11-13T14:22:34Z",
  "priority_score": 0.45,
  "assignment_status": "queued",
  "assigned_agent_id": null,
  "resolution_timestamp": null,
  "agent_feedback": null,
  "metadata": {
    "wait_time_minutes": 5,
    "user_tier": "standard",
    "validation_failures": []
  }
}
```

---

### 7. EmbeddingJob

Represents a batch embedding task for document processing.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `document_ids` | UUID[] | NOT NULL | Array of document references |
| `chunk_count_total` | Integer | NOT NULL | Total chunks to process |
| `chunk_count_processed` | Integer | NOT NULL, Default 0 | Chunks processed so far |
| `chunk_count_failed` | Integer | NOT NULL, Default 0 | Chunks that failed embedding |
| `processing_status` | Enum | NOT NULL, Indexed | pending, processing, completed, failed |
| `started_timestamp` | DateTime | NULL | When job started (ISO 8601 UTC) |
| `completed_timestamp` | DateTime | NULL | When job finished (ISO 8601 UTC) |
| `worker_id` | String(100) | NULL, Indexed | Worker that processed job |
| `batch_size` | Integer | NOT NULL | Chunks per API call |
| `error_messages` | Text[] | NULL | Error details for failed chunks |
| `metadata` | JSONB | NOT NULL | Job parameters, retry count |

**Indexes**:
- Primary: `id`
- Secondary: `processing_status`, `started_timestamp`, `worker_id`

**Relationships**:
- One EmbeddingJob references many Documents (M:N via `document_ids` array)

**State Transitions**:
```
pending → processing → completed
pending → processing → failed

Failed jobs can be retried:
failed → pending (with retry_count++ in metadata)
```

**Validation Rules**:
- `chunk_count_processed` + `chunk_count_failed` <= `chunk_count_total`
- If `processing_status = completed`, `chunk_count_processed` + `chunk_count_failed` = `chunk_count_total`
- If `processing_status = completed`, `completed_timestamp` must be NOT NULL
- `batch_size` must be > 0 and <= 2048 (OpenAI limit)

**Example**:
```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440006",
  "document_ids": ["550e8400-e29b-41d4-a716-446655440000"],
  "chunk_count_total": 12543,
  "chunk_count_processed": 12543,
  "chunk_count_failed": 0,
  "processing_status": "completed",
  "started_timestamp": "2025-11-13T10:30:15Z",
  "completed_timestamp": "2025-11-13T10:37:42Z",
  "worker_id": "embed-worker-02",
  "batch_size": 100,
  "error_messages": [],
  "metadata": {
    "embedding_model": "text-embedding-3-small",
    "retry_count": 0,
    "cost_usd": 0.42
  }
}
```

---

### 8. AuditEvent

Represents a logged system action for compliance and debugging.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | UUID | PK, NOT NULL | Unique identifier |
| `event_type` | Enum | NOT NULL, Indexed | ingestion, query, escalation, validation_failure, pii_detection, cache_hit, etc. |
| `timestamp` | DateTime | NOT NULL, Indexed | When event occurred (ISO 8601 UTC, millisecond precision) |
| `actor` | String(100) | NOT NULL | User ID or system component name |
| `affected_entity_type` | Enum | NOT NULL | document, query, chunk, answer, etc. |
| `affected_entity_id` | UUID | NOT NULL, Indexed | Entity reference |
| `severity_level` | Enum | NOT NULL | info, warning, error, critical |
| `event_metadata` | JSONB | NOT NULL | Event-specific data (flexible schema) |
| `trace_id` | String(100) | NULL, Indexed | Distributed tracing trace ID |
| `span_id` | String(100) | NULL | Distributed tracing span ID |

**Indexes**:
- Primary: `id`
- Secondary: `event_type`, `timestamp`, `affected_entity_id`, `trace_id`
- Time-series: Partition by `timestamp` (monthly partitions for performance)

**Relationships**:
- AuditEvent references any entity via `(affected_entity_type, affected_entity_id)`

**Validation Rules**:
- `event_metadata` schema depends on `event_type` (validated at application layer)
- `timestamp` must be recent (<= current time + 1 minute for clock skew)
- `severity_level` should match event type (e.g., validation_failure → warning/error)

**Retention Policy**:
- info: 90 days
- warning/error: 365 days
- critical: indefinite

**Example**:
```json
{
  "id": "cc0e8400-e29b-41d4-a716-446655440007",
  "event_type": "pii_detection",
  "timestamp": "2025-11-13T10:35:11.234Z",
  "actor": "ingest-worker-01",
  "affected_entity_type": "chunk",
  "affected_entity_id": "660e8400-e29b-41d4-a716-446655440001",
  "severity_level": "warning",
  "event_metadata": {
    "pii_type": "email",
    "pattern_matched": "[REDACTED_EMAIL]",
    "original_char_offset": 5280,
    "redaction_applied": true
  },
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

---

### 9. Collection

Represents a vector database collection for domain organization.

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `name` | String(100) | PK, NOT NULL | Collection name (e.g., "olist_reviews") |
| `description` | Text | NOT NULL | Human-readable description |
| `vector_dimensionality` | Integer | NOT NULL | Embedding dimension (1536, 768, etc.) |
| `distance_metric` | Enum | NOT NULL | cosine, dot_product, euclidean |
| `document_count` | Integer | NOT NULL, Default 0 | Number of documents in collection |
| `total_vector_count` | Integer | NOT NULL, Default 0 | Number of vectors (chunks) in collection |
| `creation_timestamp` | DateTime | NOT NULL | When collection was created (ISO 8601 UTC) |
| `last_update_timestamp` | DateTime | NOT NULL | Last time a document was added/removed |
| `retention_policy_days` | Integer | NULL | Days to retain vectors (NULL = indefinite) |
| `metadata_schema` | JSONB | NOT NULL | JSON Schema for expected metadata fields |

**Indexes**:
- Primary: `name`

**Relationships**:
- One Collection has many Chunks (1:N)
- One Collection has many Documents (1:N)

**Validation Rules**:
- `vector_dimensionality` must be > 0 and match embedding model
- `retention_policy_days` must be >= 30 or NULL (prevent accidental short retention)
- `metadata_schema` must be valid JSON Schema
- `document_count` and `total_vector_count` should be kept in sync (updated via triggers or background job)

**Example**:
```json
{
  "name": "olist_reviews",
  "description": "Brazilian e-commerce order reviews from Olist dataset",
  "vector_dimensionality": 1536,
  "distance_metric": "cosine",
  "document_count": 1,
  "total_vector_count": 12543,
  "creation_timestamp": "2025-11-13T10:00:00Z",
  "last_update_timestamp": "2025-11-13T10:37:42Z",
  "retention_policy_days": null,
  "metadata_schema": {
    "type": "object",
    "properties": {
      "language": {"type": "string"},
      "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
      "entities": {"type": "array", "items": {"type": "string"}}
    }
  }
}
```

---

## Storage Strategy

### Primary Storage (Transactional Data)

**PostgreSQL 14+** for structured relational data:
- Documents, Queries, Answers, EscalationRequests, EmbeddingJobs
- ACID guarantees for consistency
- JSON(B) columns for flexible metadata
- Partitioning: AuditEvents by timestamp (monthly), Queries by timestamp (weekly)

**Schema**:
```sql
-- Simplified DDL (illustrative)

CREATE TABLE documents (
  id UUID PRIMARY KEY,
  file_name VARCHAR(255) NOT NULL,
  file_format VARCHAR(10) NOT NULL CHECK (file_format IN ('CSV', 'PDF', 'DOCX', 'TXT', 'MD')),
  file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0),
  upload_timestamp TIMESTAMPTZ NOT NULL,
  detected_language VARCHAR(10) NOT NULL,
  processing_status VARCHAR(20) NOT NULL CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
  chunk_count INTEGER,
  collection_name VARCHAR(100) NOT NULL REFERENCES collections(name),
  error_message TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX idx_documents_status ON documents(processing_status);
CREATE INDEX idx_documents_upload_time ON documents(upload_timestamp);

-- Similar tables for: queries, answers, escalation_requests, embedding_jobs, audit_events, collections
```

### Vector Storage

**Qdrant 1.7+** for embeddings and similarity search:
- Chunks (text_content + vector_embedding + metadata)
- Collections (olist_reviews, product_docs, etc.)
- HNSW index for fast approximate nearest neighbor search

**Qdrant Collection Config**:
```json
{
  "collection_name": "olist_reviews",
  "vectors": {
    "size": 1536,
    "distance": "Cosine"
  },
  "hnsw_config": {
    "m": 16,
    "ef_construct": 200
  },
  "payload_schema": {
    "document_id": "keyword",
    "sequence_position": "integer",
    "token_count": "integer",
    "language_code": "keyword",
    "extracted_metadata": "json"
  }
}
```

### Caching Layer

**Redis 7+** for semantic caching:
- Key: `query_hash:{query_embedding_hash}:{top_3_chunk_ids_hash}`
- Value: Serialized Answer object
- TTL: 3600 seconds (1 hour)
- Eviction: LRU (Least Recently Used)

**Cache Entry**:
```json
{
  "key": "query_hash:abc123def456:chunk789xyz012",
  "value": {
    "answer_id": "990e8400-e29b-41d4-a716-446655440004",
    "answer_text": "...",
    "confidence_score": 0.85,
    "generation_timestamp": "2025-11-13T14:22:33Z"
  },
  "ttl": 3600
}
```

---

## Data Flow Examples

### 1. Document Ingestion Flow

```
1. User uploads CSV → Document created (status=pending)
2. Ingest worker picks up → Document.status=processing
3. Worker preprocesses: text extraction, PII redaction, chunking
4. Worker creates Chunks (without embeddings yet)
5. Worker creates EmbeddingJob (references Document)
6. Embed worker picks up EmbeddingJob → generates embeddings
7. Embed worker stores Chunks in Qdrant
8. EmbeddingJob.status=completed → Document.status=completed
```

### 2. Query Flow

```
1. User submits query → Query created (status=pending)
2. Query worker picks up → Query.status=processing
3. Worker generates query embedding
4. Worker searches Qdrant → top 10 chunks
5. Worker creates QueryResults (links Query to Chunks)
6. Worker composes prompt with retrieved chunks
7. Worker calls LLM → generates answer
8. Worker creates Answer (links to Query)
9. Worker validates answer → Answer.validation_status=passed
10. Query.status=completed → return Answer to user
```

### 3. Escalation Flow

```
1. Query completed with Answer (confidence=0.62 < 0.7 threshold)
2. System creates EscalationRequest (reason=low_confidence)
3. EscalationRequest.assignment_status=queued, priority calculated
4. Support agent fetches highest priority EscalationRequest
5. Agent assigns to self → EscalationRequest.assignment_status=assigned
6. Agent reviews Query + Answer + QueryResults (retrieved chunks)
7. Agent provides correct answer → EscalationRequest.agent_feedback
8. Agent marks resolved → EscalationRequest.assignment_status=resolved
9. (Optional) System uses feedback for fine-tuning or prompt improvement
```

---

## Data Retention & Archival

| Entity | Hot Storage (PostgreSQL/Qdrant) | Cold Storage (S3) | Deletion |
|--------|----------------------------------|-------------------|----------|
| Documents | Indefinite or per collection policy | After 365 days | Per LGPD request only |
| Chunks | Indefinite or per collection policy | After 365 days | With parent Document |
| Queries | 90 days | 90-365 days | After 365 days |
| Answers | 90 days | 90-365 days | With parent Query |
| QueryResults | 90 days | 90-365 days | With parent Query |
| EscalationRequests | 365 days | After 365 days | After 730 days |
| EmbeddingJobs | 30 days | Not archived | After 30 days |
| AuditEvents (info) | 90 days | Not archived | After 90 days |
| AuditEvents (warning/error) | 365 days | After 365 days | After 730 days |
| AuditEvents (critical) | Indefinite | After 730 days | Per compliance requirement |
| Collections | Indefinite | Not archived | Manual deletion only |

**Archival Process**:
- Daily cron job queries PostgreSQL for records older than hot storage threshold
- Exports to JSON (documents) or Parquet (queries, answers) in S3
- Deletes from PostgreSQL after successful S3 upload and verification
- Qdrant vectors deleted based on collection retention policy (via metadata timestamp filter)

---

## Migrations & Versioning

**Schema Versioning**:
- Use Alembic (Python) for PostgreSQL migrations
- Track schema version in `schema_migrations` table
- Qdrant collections versioned via naming: `olist_reviews_v1`, `olist_reviews_v2`

**Breaking Changes**:
- Add new columns as nullable, backfill later (avoid blocking deployments)
- Rename columns via 2-phase approach: add new column, dual-write, drop old column
- Qdrant schema changes: create new collection, reindex, switch pointer, delete old collection

**Backward Compatibility**:
- JSONB `metadata` fields allow adding new fields without schema changes
- API contracts versioned (v1, v2) to avoid breaking clients during migrations

---

## Summary

This data model provides:
- **Traceability**: Every query traced through QueryResults to source Chunks and Documents
- **Auditability**: Comprehensive AuditEvents for compliance (LGPD, SOC 2)
- **Scalability**: Partitioning and archival strategies for billion-scale growth
- **Flexibility**: JSONB metadata fields enable iteration without schema changes
- **Performance**: Appropriate indexes for access patterns (timestamp, status, user_id)

All entities are designed for append-mostly patterns (immutable queries/answers) with clear state transitions and validation rules. The model supports the full RAG pipeline from document ingestion to query answering to human escalation.
