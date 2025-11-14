"""Pydantic models for human escalation requests."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EscalationReason(str, Enum):
    """Reason for escalating to human support."""

    LOW_CONFIDENCE = "low_confidence"
    VALIDATION_FAILURE = "validation_failure"
    USER_REQUEST = "user_request"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    PII_DETECTED = "pii_detected"
    HARMFUL_CONTENT = "harmful_content"
    OUT_OF_SCOPE = "out_of_scope"


class AssignmentStatus(str, Enum):
    """Status of escalation assignment."""

    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class EscalationRequest(BaseModel):
    """
    Represents a query escalated to human support.

    Attributes:
        id: Unique escalation identifier
        query_id: Reference to original query
        answer_id: Reference to attempted answer (nullable if no answer generated)
        reason: Escalation reason
        confidence_score: Confidence score at escalation (if applicable)
        escalated_at: Escalation timestamp
        priority_score: Calculated priority (0-100, higher = more urgent)
        assignment_status: Current assignment status
        assigned_agent_id: Assigned agent identifier (nullable)
        assigned_at: Assignment timestamp (nullable)
        resolved_at: Resolution timestamp (nullable)
        resolution_time_seconds: Time to resolution (nullable)
        agent_feedback: Feedback from agent (nullable)
        metadata: Additional escalation context
    """

    id: UUID = Field(default_factory=uuid4)
    query_id: UUID
    answer_id: UUID | None = None
    reason: EscalationReason
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    escalated_at: datetime = Field(default_factory=datetime.utcnow)
    priority_score: float = Field(default=50.0, ge=0.0, le=100.0)
    assignment_status: AssignmentStatus = AssignmentStatus.QUEUED
    assigned_agent_id: str | None = None
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None
    resolution_time_seconds: float | None = None
    agent_feedback: str | None = Field(None, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("priority_score")
    @classmethod
    def validate_priority_score(cls, v: float) -> float:
        """Ensure priority score is within valid range."""
        if not 0.0 <= v <= 100.0:
            raise ValueError("Priority score must be between 0 and 100")
        return v

    @field_validator("agent_feedback")
    @classmethod
    def validate_feedback(cls, v: str | None) -> str | None:
        """Trim whitespace from feedback."""
        if v is not None:
            return v.strip() if v.strip() else None
        return None

    def calculate_priority(
        self,
        wait_time_minutes: float,
        user_tier: str = "standard",
    ) -> float:
        """
        Calculate escalation priority score based on multiple factors.

        Priority factors:
        - Reason severity (0-40 points)
        - Wait time (0-30 points, increases over time)
        - User tier (0-20 points)
        - Confidence gap (0-10 points)

        Args:
            wait_time_minutes: Minutes since escalation
            user_tier: User tier (standard, premium, enterprise)

        Returns:
            Priority score (0-100)
        """
        priority = 0.0

        # Reason severity (40 points max)
        reason_weights = {
            EscalationReason.HARMFUL_CONTENT: 40.0,
            EscalationReason.PII_DETECTED: 35.0,
            EscalationReason.PROMPT_INJECTION_DETECTED: 30.0,
            EscalationReason.VALIDATION_FAILURE: 25.0,
            EscalationReason.USER_REQUEST: 20.0,
            EscalationReason.LOW_CONFIDENCE: 15.0,
            EscalationReason.OUT_OF_SCOPE: 10.0,
        }
        priority += reason_weights.get(self.reason, 15.0)

        # Wait time (30 points max, increases linearly)
        # Max priority reached at 60 minutes
        wait_time_score = min(30.0, (wait_time_minutes / 60.0) * 30.0)
        priority += wait_time_score

        # User tier (20 points max)
        tier_weights = {
            "enterprise": 20.0,
            "premium": 15.0,
            "standard": 10.0,
            "free": 5.0,
        }
        priority += tier_weights.get(user_tier.lower(), 10.0)

        # Confidence gap (10 points max)
        if self.confidence_score is not None:
            # Lower confidence = higher priority
            confidence_gap = 1.0 - self.confidence_score
            priority += confidence_gap * 10.0

        # Ensure within bounds
        return min(100.0, max(0.0, priority))

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440005",
                "query_id": "770e8400-e29b-41d4-a716-446655440002",
                "answer_id": "880e8400-e29b-41d4-a716-446655440003",
                "reason": "low_confidence",
                "confidence_score": 0.62,
                "escalated_at": "2025-11-13T14:30:05Z",
                "priority_score": 42.5,
                "assignment_status": "queued",
                "assigned_agent_id": None,
                "assigned_at": None,
                "resolved_at": None,
                "resolution_time_seconds": None,
                "agent_feedback": None,
                "metadata": {
                    "validation_warnings": ["low_retrieval_score"],
                    "retrieved_chunks_count": 3,
                },
            }
        }
    }


class EscalationCreate(BaseModel):
    """Schema for creating an escalation request."""

    query_id: UUID
    answer_id: UUID | None = None
    reason: EscalationReason
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EscalationUpdate(BaseModel):
    """Schema for updating an escalation request."""

    assignment_status: AssignmentStatus | None = None
    assigned_agent_id: str | None = None
    agent_feedback: str | None = Field(None, max_length=2000)


class EscalationResponse(BaseModel):
    """Schema for escalation API responses."""

    id: UUID
    query_id: UUID
    reason: EscalationReason
    confidence_score: float | None
    escalated_at: datetime
    priority_score: float
    assignment_status: AssignmentStatus
    assigned_agent_id: str | None
    wait_time_minutes: float | None


class EscalationDetail(EscalationResponse):
    """Detailed escalation response with full context."""

    answer_id: UUID | None
    assigned_at: datetime | None
    resolved_at: datetime | None
    resolution_time_seconds: float | None
    agent_feedback: str | None
    metadata: dict[str, Any]
    query_text: str | None  # Included for agent context
    answer_text: str | None  # Included for agent context


class EscalationQueueItem(BaseModel):
    """Simplified escalation item for queue display."""

    id: UUID
    query_id: UUID
    query_text: str
    reason: EscalationReason
    priority_score: float
    wait_time_minutes: float
    escalated_at: datetime
