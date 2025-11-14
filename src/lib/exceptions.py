"""Custom exception hierarchy for RagFlow."""

from typing import Any


class RagFlowException(Exception):
    """Base exception for all RagFlow errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize exception with message and optional details."""
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(RagFlowException):
    """Raised when input validation fails."""

    pass


class NotFoundError(RagFlowException):
    """Raised when a requested resource is not found."""

    pass


class AlreadyExistsError(RagFlowException):
    """Raised when attempting to create a resource that already exists."""

    pass


class ExternalServiceError(RagFlowException):
    """Raised when an external service (OpenAI, Qdrant, etc.) fails."""

    pass


class RateLimitError(ExternalServiceError):
    """Raised when an external service rate limit is exceeded."""

    pass


class DatabaseError(RagFlowException):
    """Raised when a database operation fails."""

    pass


class QueueError(RagFlowException):
    """Raised when a message queue operation fails."""

    pass


class EmbeddingError(RagFlowException):
    """Raised when embedding generation fails."""

    pass


class RetrievalError(RagFlowException):
    """Raised when vector search/retrieval fails."""

    pass


class GenerationError(RagFlowException):
    """Raised when LLM answer generation fails."""

    pass


class GuardrailsError(RagFlowException):
    """Raised when guardrails detect a policy violation."""

    pass


class PIIDetectedError(GuardrailsError):
    """Raised when PII is detected in input or output."""

    pass


class PromptInjectionError(GuardrailsError):
    """Raised when prompt injection attempt is detected."""

    pass


class HallucinationError(GuardrailsError):
    """Raised when LLM output appears to be hallucinated."""

    pass


class ConfigurationError(RagFlowException):
    """Raised when application is misconfigured."""

    pass
