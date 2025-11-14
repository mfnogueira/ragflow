"""Pydantic models for documents and chunks."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class FileFormat(str, Enum):
    """Supported document file formats."""

    CSV = "csv"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


class ProcessingStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIALLY_INDEXED = "partially_indexed"


class Document(BaseModel):
    """
    Represents a source document in the knowledge base.

    Attributes:
        id: Unique document identifier
        file_name: Original file name
        file_format: Document format (CSV, PDF, etc.)
        file_size_bytes: File size in bytes
        collection_name: Vector collection assignment
        language_code: Detected language (pt-BR, en-US, etc.)
        status: Processing status
        chunk_count: Number of chunks created from this document
        uploaded_at: Upload timestamp
        processed_at: Processing completion timestamp (nullable)
        metadata: Additional document metadata
    """

    id: UUID = Field(default_factory=uuid4)
    file_name: str = Field(..., min_length=1, max_length=255)
    file_format: FileFormat
    file_size_bytes: int = Field(..., ge=0)
    collection_name: str = Field(..., min_length=1, max_length=100)
    language_code: str = Field(default="pt-BR", max_length=10)
    status: ProcessingStatus = ProcessingStatus.PENDING
    chunk_count: int = Field(default=0, ge=0)
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Ensure file name is not empty."""
        if not v.strip():
            raise ValueError("File name cannot be empty")
        return v.strip()

    @field_validator("collection_name")
    @classmethod
    def validate_collection_name(cls, v: str) -> str:
        """Ensure collection name is valid."""
        if not v.strip():
            raise ValueError("Collection name cannot be empty")
        # Collection names should be lowercase alphanumeric with underscores
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Collection name must be alphanumeric (with _ or - allowed)")
        return v.strip().lower()

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "olist_reviews_sample.csv",
                "file_format": "csv",
                "file_size_bytes": 52428800,
                "collection_name": "olist_reviews",
                "language_code": "pt-BR",
                "status": "completed",
                "chunk_count": 1250,
                "uploaded_at": "2025-11-13T10:00:00Z",
                "processed_at": "2025-11-13T10:08:45Z",
                "metadata": {
                    "source": "kaggle",
                    "uploader": "admin",
                },
            }
        }
    }


class Chunk(BaseModel):
    """
    Represents a processed text segment from a document.

    Attributes:
        id: Unique chunk identifier
        document_id: Reference to source document
        text_content: Text content (after redaction)
        vector_embedding: Vector representation (list of floats)
        sequence_position: Position in source document
        token_count: Number of tokens in chunk
        char_start_offset: Character start position in original document
        char_end_offset: Character end position in original document
        language_code: Language of the chunk
        created_at: Creation timestamp
        metadata: Extracted metadata (entities, keywords, etc.)
    """

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    text_content: str = Field(..., min_length=1, max_length=10000)
    vector_embedding: list[float] | None = None
    sequence_position: int = Field(..., ge=0)
    token_count: int = Field(..., ge=1)
    char_start_offset: int = Field(..., ge=0)
    char_end_offset: int = Field(..., ge=0)
    language_code: str = Field(default="pt-BR", max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("char_end_offset")
    @classmethod
    def validate_offsets(cls, v: int, info: Any) -> int:
        """Ensure end offset is greater than start offset."""
        if "char_start_offset" in info.data:
            if v <= info.data["char_start_offset"]:
                raise ValueError("End offset must be greater than start offset")
        return v

    @field_validator("vector_embedding")
    @classmethod
    def validate_embedding(cls, v: list[float] | None) -> list[float] | None:
        """Validate embedding dimensionality if present."""
        if v is not None:
            # Common embedding dimensions: 384, 768, 1536
            valid_dimensions = [384, 768, 1024, 1536, 3072]
            if len(v) not in valid_dimensions:
                raise ValueError(
                    f"Embedding dimension {len(v)} is not in valid dimensions: {valid_dimensions}"
                )
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "text_content": "O produto chegou em perfeito estado e antes do prazo. Muito satisfeito!",
                "vector_embedding": None,  # Omitted in example for brevity
                "sequence_position": 42,
                "token_count": 18,
                "char_start_offset": 5120,
                "char_end_offset": 5192,
                "language_code": "pt-BR",
                "created_at": "2025-11-13T10:05:30Z",
                "metadata": {
                    "sentiment": "positive",
                    "has_pii": False,
                },
            }
        }
    }


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""

    file_name: str = Field(..., min_length=1, max_length=255)
    file_format: FileFormat
    file_size_bytes: int = Field(..., ge=0)
    collection_name: str = Field(..., min_length=1, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentResponse(BaseModel):
    """Schema for document API responses."""

    id: UUID
    file_name: str
    file_format: FileFormat
    file_size_bytes: int
    collection_name: str
    language_code: str
    status: ProcessingStatus
    chunk_count: int
    uploaded_at: datetime
    processed_at: datetime | None
    metadata: dict[str, Any]


class ChunkCreate(BaseModel):
    """Schema for creating a new chunk."""

    document_id: UUID
    text_content: str = Field(..., min_length=1, max_length=10000)
    sequence_position: int = Field(..., ge=0)
    token_count: int = Field(..., ge=1)
    char_start_offset: int = Field(..., ge=0)
    char_end_offset: int = Field(..., ge=0)
    language_code: str = Field(default="pt-BR", max_length=10)
    metadata: dict[str, Any] = Field(default_factory=dict)
