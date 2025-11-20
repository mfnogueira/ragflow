"""Guardrails Service for input validation and safety checks."""

import re
from typing import Dict, Any, List

from src.lib.config import settings
from src.lib.exceptions import ValidationError
from src.lib.logger import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """Container for validation result."""

    def __init__(
        self,
        is_valid: bool,
        reason: str | None = None,
        sanitized_input: str | None = None,
    ):
        """
        Initialize validation result.

        Args:
            is_valid: Whether input passed validation
            reason: Reason for validation failure (if applicable)
            sanitized_input: Sanitized version of input (if applicable)
        """
        self.is_valid = is_valid
        self.reason = reason
        self.sanitized_input = sanitized_input

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "is_valid": self.is_valid,
            "reason": self.reason,
            "sanitized_input": self.sanitized_input,
        }


class GuardrailsService:
    """Service for validating and sanitizing user inputs."""

    def __init__(self):
        """Initialize the guardrails service."""
        self.max_query_length = settings.max_query_length
        self.min_query_length = 3  # Minimum characters for a valid query

        # Patterns for potentially harmful inputs
        self.sql_injection_patterns = [
            r"(\bUNION\b.*\bSELECT\b)",
            r"(\bDROP\b.*\bTABLE\b)",
            r"(\bINSERT\b.*\bINTO\b)",
            r"(\bDELETE\b.*\bFROM\b)",
            r"(--|\#|\/\*|\*\/)",
        ]

        # Patterns for prompt injection attempts
        self.prompt_injection_patterns = [
            r"(ignore.*previous.*instructions?)",
            r"(forget.*previous.*instructions?)",
            r"(you are now)",
            r"(system:)",
            r"(assistant:)",
            r"(disregard.*above)",
        ]

        logger.info("GuardrailsService initialized")

    async def validate_query(self, query: str) -> ValidationResult:
        """
        Validate a user query for safety and correctness.

        Args:
            query: User's question

        Returns:
            ValidationResult indicating if query is valid

        Raises:
            ValidationError: If validation fails critically
        """
        try:
            # Check if query is empty or only whitespace
            if not query or not query.strip():
                return ValidationResult(
                    is_valid=False,
                    reason="Query cannot be empty",
                )

            # Sanitize (remove extra whitespace)
            sanitized = " ".join(query.split())

            # Check length constraints
            if len(sanitized) < self.min_query_length:
                return ValidationResult(
                    is_valid=False,
                    reason=f"Query too short (minimum {self.min_query_length} characters)",
                )

            if len(sanitized) > self.max_query_length:
                return ValidationResult(
                    is_valid=False,
                    reason=f"Query too long (maximum {self.max_query_length} characters)",
                )

            # Check for SQL injection patterns
            sql_check = self._check_sql_injection(sanitized)
            if not sql_check.is_valid:
                logger.warning(f"SQL injection attempt detected: {query[:50]}...")
                return sql_check

            # Check for prompt injection patterns
            prompt_check = self._check_prompt_injection(sanitized)
            if not prompt_check.is_valid:
                logger.warning(f"Prompt injection attempt detected: {query[:50]}...")
                return prompt_check

            # Query is valid
            logger.debug(f"Query validated successfully (length={len(sanitized)})")
            return ValidationResult(
                is_valid=True,
                sanitized_input=sanitized,
            )

        except Exception as e:
            logger.error(f"Error during query validation: {e}")
            raise ValidationError(f"Validation error: {e}")

    def _check_sql_injection(self, text: str) -> ValidationResult:
        """
        Check for SQL injection patterns.

        Args:
            text: Text to check

        Returns:
            ValidationResult
        """
        text_upper = text.upper()

        for pattern in self.sql_injection_patterns:
            if re.search(pattern, text_upper, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    reason="Potential SQL injection detected",
                )

        return ValidationResult(is_valid=True)

    def _check_prompt_injection(self, text: str) -> ValidationResult:
        """
        Check for prompt injection patterns.

        Args:
            text: Text to check

        Returns:
            ValidationResult
        """
        text_lower = text.lower()

        for pattern in self.prompt_injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return ValidationResult(
                    is_valid=False,
                    reason="Potential prompt injection detected",
                )

        return ValidationResult(is_valid=True)

    def validate_collection_name(self, collection: str) -> ValidationResult:
        """
        Validate a collection name.

        Args:
            collection: Collection name to validate

        Returns:
            ValidationResult
        """
        if not collection or not collection.strip():
            return ValidationResult(
                is_valid=False,
                reason="Collection name cannot be empty",
            )

        # Only allow alphanumeric, underscores, and hyphens
        if not re.match(r"^[a-zA-Z0-9_-]+$", collection):
            return ValidationResult(
                is_valid=False,
                reason="Collection name can only contain alphanumeric characters, underscores, and hyphens",
            )

        if len(collection) > 100:
            return ValidationResult(
                is_valid=False,
                reason="Collection name too long (maximum 100 characters)",
            )

        return ValidationResult(
            is_valid=True,
            sanitized_input=collection.strip(),
        )

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text by removing extra whitespace and normalizing.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove extra whitespace
        sanitized = " ".join(text.split())

        # Remove null bytes
        sanitized = sanitized.replace("\x00", "")

        return sanitized.strip()

    def validate_parameters(
        self,
        max_chunks: int | None = None,
        confidence_threshold: float | None = None,
    ) -> ValidationResult:
        """
        Validate query parameters.

        Args:
            max_chunks: Maximum chunks to retrieve
            confidence_threshold: Confidence threshold

        Returns:
            ValidationResult
        """
        if max_chunks is not None:
            if max_chunks < 1:
                return ValidationResult(
                    is_valid=False,
                    reason="max_chunks must be at least 1",
                )
            if max_chunks > 50:
                return ValidationResult(
                    is_valid=False,
                    reason="max_chunks cannot exceed 50",
                )

        if confidence_threshold is not None:
            if confidence_threshold < 0.0 or confidence_threshold > 1.0:
                return ValidationResult(
                    is_valid=False,
                    reason="confidence_threshold must be between 0.0 and 1.0",
                )

        return ValidationResult(is_valid=True)


# Singleton instance for dependency injection
_guardrails_service: GuardrailsService | None = None


def get_guardrails_service() -> GuardrailsService:
    """
    Get or create the singleton GuardrailsService instance.

    Returns:
        GuardrailsService instance
    """
    global _guardrails_service
    if _guardrails_service is None:
        _guardrails_service = GuardrailsService()
    return _guardrails_service
