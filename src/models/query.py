"""Pydantic models for queries, answers, and query results."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ProcessingStatus(str, Enum):
    """Query processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


class ValidationStatus(str, Enum):
    """Answer validation status."""

    PASSED = "passed"
    FAILED = "failed"
    WARNINGS = "warnings"


class Query(BaseModel):
    """
    Represents a user question.

    Attributes:
        id: Unique query identifier
        query_text: User's original question
        query_embedding: Vector representation of query (nullable until generated)
        user_id: User identifier (nullable if unauthenticated)
        collection_name: Target collection for search
        submitted_at: Submission timestamp
        language_code: Detected language
        status: Processing status
        worker_id: Assigned worker identifier (nullable)
        session_correlation_id: Session correlation ID for tracing
    """

    id: UUID = Field(default_factory=uuid4)
    query_text: str = Field(..., min_length=1, max_length=1000)
    query_embedding: list[float] | None = None
    user_id: str | None = None
    collection_name: str = Field(default="olist_reviews", max_length=100)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    language_code: str = Field(default="pt-BR", max_length=10)
    status: ProcessingStatus = ProcessingStatus.PENDING
    worker_id: str | None = None
    session_correlation_id: str | None = None

    @field_validator("query_text")
    @classmethod
    def validate_query_text(cls, v: str) -> str:
        """Ensure query text is not empty."""
        if not v.strip():
            raise ValueError("Query text cannot be empty")
        return v.strip()

    @field_validator("query_embedding")
    @classmethod
    def validate_embedding(cls, v: list[float] | None) -> list[float] | None:
        """Validate embedding dimensionality if present."""
        if v is not None:
            valid_dimensions = [384, 768, 1024, 1536, 3072]
            if len(v) not in valid_dimensions:
                raise ValueError(
                    f"Embedding dimension {len(v)} is not in valid dimensions: {valid_dimensions}"
                )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "query_text": "Quais são as reclamações mais comuns sobre entrega?",
                "query_embedding": None,
                "user_id": "user_12345",
                "collection_name": "olist_reviews",
                "submitted_at": "2025-11-13T14:30:00Z",
                "language_code": "pt-BR",
                "status": "pending",
                "worker_id": None,
                "session_correlation_id": "sess_abc123",
            }
        }
    }


class Answer(BaseModel):
    """
    Represents a generated response to a query.

    Attributes:
        id: Unique answer identifier
        query_id: Reference to query
        answer_text: LLM-generated response
        confidence_score: Composite confidence metric (0-1)
        generation_timestamp: Generation timestamp
        llm_model_used: LLM model identifier
        token_count_input: Input tokens consumed
        token_count_output: Output tokens generated
        retrieval_latency_ms: Retrieval operation latency
        generation_latency_ms: LLM generation latency
        total_latency_ms: Total end-to-end latency
        cache_hit: Whether answer was retrieved from cache
        validation_status: Validation outcome
        escalation_flag: Whether query was escalated
        redaction_flag: Whether PII was redacted from answer
        metadata: Additional metadata (sources, chunks used, etc.)
    """

    id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    answer_text: str = Field(..., min_length=1, max_length=5000)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    generation_timestamp: datetime = Field(default_factory=datetime.utcnow)
    llm_model_used: str = Field(..., max_length=100)
    token_count_input: int = Field(..., ge=0)
    token_count_output: int = Field(..., ge=0)
    retrieval_latency_ms: float = Field(..., ge=0.0)
    generation_latency_ms: float = Field(..., ge=0.0)
    total_latency_ms: float = Field(..., ge=0.0)
    cache_hit: bool = False
    validation_status: ValidationStatus = ValidationStatus.PASSED
    escalation_flag: bool = False
    redaction_flag: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("answer_text")
    @classmethod
    def validate_answer_text(cls, v: str) -> str:
        """Ensure answer text is not empty."""
        if not v.strip():
            raise ValueError("Answer text cannot be empty")
        return v.strip()

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "query_id": "770e8400-e29b-41d4-a716-446655440002",
                "answer_text": "As reclamações mais comuns sobre entrega incluem: atrasos na entrega (45%), produtos danificados (23%), e problemas de rastreamento (18%).",
                "confidence_score": 0.87,
                "generation_timestamp": "2025-11-13T14:30:03Z",
                "llm_model_used": "gpt-4o-mini",
                "token_count_input": 1200,
                "token_count_output": 85,
                "retrieval_latency_ms": 450.5,
                "generation_latency_ms": 1200.3,
                "total_latency_ms": 1650.8,
                "cache_hit": False,
                "validation_status": "passed",
                "escalation_flag": False,
                "redaction_flag": False,
                "metadata": {
                    "sources_count": 5,
                    "chunks_used": 10,
                },
            }
        }
    }


class QueryResult(BaseModel):
    """
    Represents a retrieved chunk relevant to a query.

    Links Query to Chunk with relevance scoring.

    Attributes:
        id: Unique result identifier
        query_id: Reference to query
        chunk_id: Reference to chunk
        relevance_score: Vector similarity score (0-1)
        reranking_score: Reranking score if applied (nullable)
        rank_position: Position in result set (1-based)
        retrieved_at: Retrieval timestamp
        metadata_match_flags: Boolean indicators for metadata filters
    """

    id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    chunk_id: UUID
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    reranking_score: float | None = Field(None, ge=0.0, le=1.0)
    rank_position: int = Field(..., ge=1)
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    metadata_match_flags: dict[str, bool] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440004",
                "query_id": "770e8400-e29b-41d4-a716-446655440002",
                "chunk_id": "660e8400-e29b-41d4-a716-446655440001",
                "relevance_score": 0.91,
                "reranking_score": 0.94,
                "rank_position": 1,
                "retrieved_at": "2025-11-13T14:30:02Z",
                "metadata_match_flags": {
                    "date_filter_match": True,
                    "category_filter_match": True,
                },
            }
        }
    }


class QueryCreate(BaseModel):
    """Schema for creating a new query."""

    query_text: str = Field(..., min_length=1, max_length=1000)
    user_id: str | None = None
    collection_name: str = Field(default="olist_reviews", max_length=100)
    session_correlation_id: str | None = None


class QueryResponse(BaseModel):
    """Schema for query API responses."""

    id: UUID
    query_text: str
    collection_name: str
    submitted_at: datetime
    status: ProcessingStatus
    answer: "AnswerResponse | None" = None


class AnswerResponse(BaseModel):
    """Schema for answer API responses."""

    id: UUID
    answer_text: str
    confidence_score: float
    generation_timestamp: datetime
    total_latency_ms: float
    cache_hit: bool
    escalation_flag: bool
    sources: list[dict[str, Any]] = Field(default_factory=list)


class QueryWithAnswer(BaseModel):
    """Combined query and answer for full response."""

    query: QueryResponse
    answer: AnswerResponse | None


# Required for forward reference resolution
QueryResponse.model_rebuild()
