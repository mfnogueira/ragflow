"""Pydantic models for audit events and compliance logging."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of audit events."""

    # Document lifecycle
    DOCUMENT_UPLOADED = "document_uploaded"
    DOCUMENT_PROCESSED = "document_processed"
    DOCUMENT_FAILED = "document_failed"
    DOCUMENT_DELETED = "document_deleted"

    # Ingestion and indexing
    INGESTION_STARTED = "ingestion_started"
    INGESTION_COMPLETED = "ingestion_completed"
    INGESTION_FAILED = "ingestion_failed"
    EMBEDDING_GENERATED = "embedding_generated"
    EMBEDDING_FAILED = "embedding_failed"

    # Query processing
    QUERY_SUBMITTED = "query_submitted"
    QUERY_PROCESSED = "query_processed"
    QUERY_FAILED = "query_failed"
    QUERY_CACHED = "query_cached"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"

    # Validation and guardrails
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    PII_DETECTED = "pii_detected"
    PII_REDACTED = "pii_redacted"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    HARMFUL_CONTENT_DETECTED = "harmful_content_detected"

    # Escalation
    ESCALATION_CREATED = "escalation_created"
    ESCALATION_ASSIGNED = "escalation_assigned"
    ESCALATION_RESOLVED = "escalation_resolved"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    HEALTH_CHECK_FAILED = "health_check_failed"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"

    # Access control
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    API_KEY_USED = "api_key_used"


class SeverityLevel(str, Enum):
    """Severity levels for audit events."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """
    Represents a logged system action for compliance and debugging.

    Attributes:
        id: Unique event identifier
        event_type: Type of event
        timestamp: Event timestamp with millisecond precision
        actor: User ID or system component name that triggered event
        affected_entity_type: Type of affected entity (query, document, etc.)
        affected_entity_id: ID of affected entity (nullable)
        severity: Event severity level
        success: Whether the operation succeeded
        error_message: Error message if operation failed (nullable)
        metadata: Event-specific additional data
        trace_id: Distributed trace ID for correlation
        span_id: Span ID within trace
        duration_ms: Operation duration in milliseconds (nullable)
        ip_address: Client IP address (if applicable)
        user_agent: Client user agent (if applicable)
    """

    id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: str = Field(..., min_length=1, max_length=255)
    affected_entity_type: str | None = Field(None, max_length=100)
    affected_entity_id: str | None = Field(None, max_length=100)
    severity: SeverityLevel = SeverityLevel.INFO
    success: bool = True
    error_message: str | None = Field(None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = Field(None, max_length=100)
    span_id: str | None = Field(None, max_length=100)
    duration_ms: float | None = Field(None, ge=0.0)
    ip_address: str | None = Field(None, max_length=45)
    user_agent: str | None = Field(None, max_length=500)

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "bb0e8400-e29b-41d4-a716-446655440006",
                "event_type": "query_processed",
                "timestamp": "2025-11-13T14:30:03.456Z",
                "actor": "query_worker_01",
                "affected_entity_type": "query",
                "affected_entity_id": "770e8400-e29b-41d4-a716-446655440002",
                "severity": "info",
                "success": True,
                "error_message": None,
                "metadata": {
                    "query_text_length": 52,
                    "confidence_score": 0.87,
                    "chunks_retrieved": 10,
                },
                "trace_id": "trace_abc123xyz",
                "span_id": "span_def456",
                "duration_ms": 1650.8,
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0...",
            }
        }
    }


class AuditEventCreate(BaseModel):
    """Schema for creating audit events."""

    event_type: EventType
    actor: str = Field(..., min_length=1, max_length=255)
    affected_entity_type: str | None = Field(None, max_length=100)
    affected_entity_id: str | None = Field(None, max_length=100)
    severity: SeverityLevel = SeverityLevel.INFO
    success: bool = True
    error_message: str | None = Field(None, max_length=1000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = Field(None, max_length=100)
    span_id: str | None = Field(None, max_length=100)
    duration_ms: float | None = Field(None, ge=0.0)
    ip_address: str | None = Field(None, max_length=45)
    user_agent: str | None = Field(None, max_length=500)


class AuditEventResponse(BaseModel):
    """Schema for audit event API responses."""

    id: UUID
    event_type: EventType
    timestamp: datetime
    actor: str
    affected_entity_type: str | None
    affected_entity_id: str | None
    severity: SeverityLevel
    success: bool


class AuditEventDetail(AuditEventResponse):
    """Detailed audit event response."""

    error_message: str | None
    metadata: dict[str, Any]
    trace_id: str | None
    span_id: str | None
    duration_ms: float | None


class AuditQuery(BaseModel):
    """Query parameters for searching audit events."""

    event_types: list[EventType] | None = None
    severity_levels: list[SeverityLevel] | None = None
    actor: str | None = None
    affected_entity_type: str | None = None
    affected_entity_id: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    success: bool | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditSummary(BaseModel):
    """Summary statistics for audit events."""

    total_events: int
    events_by_type: dict[str, int]
    events_by_severity: dict[str, int]
    success_rate: float = Field(..., ge=0.0, le=100.0)
    period_start: datetime
    period_end: datetime
    average_duration_ms: float | None


class PIIDetectionEvent(BaseModel):
    """Specialized audit event for PII detection."""

    audit_event_id: UUID
    detected_pii_types: list[str]  # e.g., ["cpf", "email", "phone"]
    redacted_count: int
    original_text_length: int
    redacted_text_length: int
    detection_confidence: float = Field(..., ge=0.0, le=1.0)


class ValidationFailureEvent(BaseModel):
    """Specialized audit event for validation failures."""

    audit_event_id: UUID
    validation_type: str  # e.g., "prompt_injection", "hallucination"
    failure_reason: str
    input_snippet: str | None  # Truncated for privacy
    blocked: bool  # Whether the request was blocked
