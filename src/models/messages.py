"""Pydantic schemas for RabbitMQ message payloads."""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class BaseMessage(BaseModel):
    """Base class for all message types."""

    message_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str | None = None
    retry_count: int = Field(default=0, ge=0)


class IngestDocumentMessage(BaseMessage):
    """
    Message to trigger document ingestion.

    Sent to: ingest_queue
    Consumed by: ingest_worker

    Attributes:
        document_id: UUID of document to ingest
        file_path: Path to document file (local or object storage)
        file_name: Original file name
        file_format: Document format (csv, pdf, etc.)
        collection_name: Target vector collection
        metadata: Additional document metadata
    """

    document_id: UUID
    file_path: str = Field(..., min_length=1, max_length=1000)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_format: str = Field(..., max_length=10)
    collection_name: str = Field(..., max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-11-13T10:00:00Z",
                "correlation_id": "corr_abc123",
                "retry_count": 0,
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_path": "/data/uploads/olist_reviews.csv",
                "file_name": "olist_reviews.csv",
                "file_format": "csv",
                "collection_name": "olist_reviews",
                "metadata": {"uploader": "admin"},
            }
        }
    }


class EmbedChunksMessage(BaseMessage):
    """
    Message to trigger embedding generation for chunks.

    Sent to: embed_queue
    Consumed by: embed_worker

    Attributes:
        document_id: UUID of source document
        chunk_ids: List of chunk UUIDs to embed
        collection_name: Target vector collection
        embedding_model: Model to use for embeddings
        batch_size: Number of chunks per API call
    """

    document_id: UUID
    chunk_ids: list[UUID] = Field(..., min_items=1)
    collection_name: str = Field(..., max_length=100)
    embedding_model: str = Field(default="text-embedding-3-small", max_length=100)
    batch_size: int = Field(default=100, ge=1, le=1000)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_660e8400-e29b-41d4-a716-446655440001",
                "timestamp": "2025-11-13T10:05:00Z",
                "correlation_id": "corr_abc123",
                "retry_count": 0,
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_ids": [
                    "660e8400-e29b-41d4-a716-446655440001",
                    "660e8400-e29b-41d4-a716-446655440002",
                ],
                "collection_name": "olist_reviews",
                "embedding_model": "text-embedding-3-small",
                "batch_size": 100,
            }
        }
    }


class ProcessQueryMessage(BaseMessage):
    """
    Message to trigger query processing.

    Sent to: query_queue
    Consumed by: query_worker

    Attributes:
        query_id: UUID of query to process
        query_text: User's question
        collection_name: Collection to search
        user_id: User identifier (nullable)
        max_chunks: Maximum chunks to retrieve
        enable_reranking: Whether to apply reranking
        llm_model: LLM model to use for generation
        metadata_filters: Optional metadata filters for retrieval
    """

    query_id: UUID
    query_text: str = Field(..., min_length=1, max_length=1000)
    collection_name: str = Field(..., max_length=100)
    user_id: str | None = None
    max_chunks: int = Field(default=10, ge=1, le=50)
    enable_reranking: bool = False
    llm_model: str = Field(default="gpt-4o-mini", max_length=100)
    metadata_filters: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_770e8400-e29b-41d4-a716-446655440002",
                "timestamp": "2025-11-13T14:30:00Z",
                "correlation_id": "sess_xyz789",
                "retry_count": 0,
                "query_id": "770e8400-e29b-41d4-a716-446655440002",
                "query_text": "Quais são as reclamações mais comuns?",
                "collection_name": "olist_reviews",
                "user_id": "user_12345",
                "max_chunks": 10,
                "enable_reranking": False,
                "llm_model": "gpt-4o-mini",
                "metadata_filters": {},
            }
        }
    }


class AuditEventMessage(BaseMessage):
    """
    Message to log audit event.

    Sent to: audit_queue
    Consumed by: audit_worker (or direct to database)

    Attributes:
        event_type: Type of event
        actor: User or system component
        affected_entity_type: Type of affected entity
        affected_entity_id: ID of affected entity
        severity: Event severity
        success: Whether operation succeeded
        error_message: Error message if failed
        metadata: Event-specific data
        trace_id: Distributed trace ID
        span_id: Span ID
        duration_ms: Operation duration
    """

    event_type: str = Field(..., max_length=100)
    actor: str = Field(..., max_length=255)
    affected_entity_type: str | None = Field(None, max_length=100)
    affected_entity_id: str | None = Field(None, max_length=100)
    severity: str = Field(default="info", max_length=20)
    success: bool = True
    error_message: str | None = Field(None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = Field(None, max_length=100)
    span_id: str | None = Field(None, max_length=100)
    duration_ms: float | None = Field(None, ge=0.0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_bb0e8400-e29b-41d4-a716-446655440006",
                "timestamp": "2025-11-13T14:30:03Z",
                "correlation_id": "sess_xyz789",
                "retry_count": 0,
                "event_type": "query_processed",
                "actor": "query_worker_01",
                "affected_entity_type": "query",
                "affected_entity_id": "770e8400-e29b-41d4-a716-446655440002",
                "severity": "info",
                "success": True,
                "error_message": None,
                "metadata": {"confidence_score": 0.87},
                "trace_id": "trace_abc123",
                "span_id": "span_def456",
                "duration_ms": 1650.8,
            }
        }
    }


class EscalationMessage(BaseMessage):
    """
    Message to trigger escalation creation.

    Sent to: escalation_queue (if using dedicated queue)
    Or directly created via API

    Attributes:
        query_id: UUID of query to escalate
        answer_id: UUID of answer (if generated)
        reason: Escalation reason
        confidence_score: Confidence score at escalation
        priority_score: Calculated priority
        metadata: Additional escalation context
    """

    query_id: UUID
    answer_id: UUID | None = None
    reason: str = Field(..., max_length=100)
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    priority_score: float = Field(default=50.0, ge=0.0, le=100.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_aa0e8400-e29b-41d4-a716-446655440005",
                "timestamp": "2025-11-13T14:30:05Z",
                "correlation_id": "sess_xyz789",
                "retry_count": 0,
                "query_id": "770e8400-e29b-41d4-a716-446655440002",
                "answer_id": "880e8400-e29b-41d4-a716-446655440003",
                "reason": "low_confidence",
                "confidence_score": 0.62,
                "priority_score": 42.5,
                "metadata": {"validation_warnings": ["low_retrieval_score"]},
            }
        }
    }


class WorkerHeartbeatMessage(BaseMessage):
    """
    Message for worker health reporting.

    Sent to: heartbeat_exchange (if using)
    Consumed by: monitoring system

    Attributes:
        worker_id: Worker identifier
        worker_type: Type of worker (query, ingest, embed)
        status: Worker status (healthy, degraded, unhealthy)
        queue_name: Queue being consumed
        messages_processed: Total messages processed
        messages_failed: Total messages failed
        current_load: Current processing load (0-1)
        uptime_seconds: Worker uptime
    """

    worker_id: str = Field(..., max_length=100)
    worker_type: str = Field(..., max_length=50)
    status: str = Field(default="healthy", max_length=20)
    queue_name: str = Field(..., max_length=100)
    messages_processed: int = Field(default=0, ge=0)
    messages_failed: int = Field(default=0, ge=0)
    current_load: float = Field(default=0.0, ge=0.0, le=1.0)
    uptime_seconds: float = Field(..., ge=0.0)

    model_config = {
        "json_schema_extra": {
            "example": {
                "message_id": "msg_heartbeat_001",
                "timestamp": "2025-11-13T14:30:00Z",
                "correlation_id": None,
                "retry_count": 0,
                "worker_id": "query_worker_01",
                "worker_type": "query",
                "status": "healthy",
                "queue_name": "query_queue",
                "messages_processed": 1523,
                "messages_failed": 12,
                "current_load": 0.65,
                "uptime_seconds": 86400.0,
            }
        }
    }
