"""SQLAlchemy ORM models for database tables."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.lib.database import Base
from src.models.document import ProcessingStatus
from src.models.query import ProcessingStatus as QueryProcessingStatus


class DocumentORM(Base):
    """Document ORM model (database table)."""

    __tablename__ = "documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    file_name = Column(String(500), nullable=False)
    file_format = Column(String(50), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    collection_name = Column(String(100), nullable=False, index=True)
    language_code = Column(String(10), nullable=False, default="pt-BR")
    status = Column(
        Enum(ProcessingStatus, name="processing_status"),
        nullable=False,
        default=ProcessingStatus.PENDING,
        index=True,
    )
    chunk_count = Column(Integer, nullable=False, default=0)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    chunks = relationship("ChunkORM", back_populates="document", cascade="all, delete-orphan")


class ChunkORM(Base):
    """Chunk ORM model (database table)."""

    __tablename__ = "chunks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PG_UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False, index=True)
    text_content = Column(Text, nullable=False)
    sequence_position = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=False)
    char_start_offset = Column(Integer, nullable=False)
    char_end_offset = Column(Integer, nullable=False)
    language_code = Column(String(10), nullable=False, default="pt-BR")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    document = relationship("DocumentORM", back_populates="chunks")


class QueryORM(Base):
    """Query ORM model (database table)."""

    __tablename__ = "queries"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_text = Column(Text, nullable=False)
    collection_name = Column(String(100), nullable=False, index=True)
    status = Column(
        Enum(QueryProcessingStatus, name="query_processing_status"),
        nullable=False,
        default=QueryProcessingStatus.PENDING,
        index=True,
    )
    submitted_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    answers = relationship("AnswerORM", back_populates="query", cascade="all, delete-orphan")
    query_results = relationship("QueryResultORM", back_populates="query", cascade="all, delete-orphan")


class AnswerORM(Base):
    """Answer ORM model (database table)."""

    __tablename__ = "answers"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id = Column(PG_UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False, index=True)
    answer_text = Column(Text, nullable=False)
    confidence_score = Column(Float, nullable=False)
    model_name = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    generated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    query = relationship("QueryORM", back_populates="answers")


class QueryResultORM(Base):
    """QueryResult ORM model (database table)."""

    __tablename__ = "query_results"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id = Column(PG_UUID(as_uuid=True), ForeignKey("queries.id"), nullable=False, index=True)
    chunk_id = Column(PG_UUID(as_uuid=True), nullable=False)  # Reference to chunk (not FK)
    similarity_score = Column(Float, nullable=False)
    rank = Column(Integer, nullable=False)
    retrieved_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    query = relationship("QueryORM", back_populates="query_results")


class CollectionORM(Base):
    """Collection ORM model (database table)."""

    __tablename__ = "collections"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    vector_dimensionality = Column(Integer, nullable=False, default=1536)
    distance_metric = Column(String(20), nullable=False, default="cosine")
    document_count = Column(Integer, nullable=False, default=0)
    total_vector_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)


class EscalationRequestORM(Base):
    """EscalationRequest ORM model (database table)."""

    __tablename__ = "escalation_requests"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    query_id = Column(PG_UUID(as_uuid=True), nullable=False)
    reason = Column(String(255), nullable=False)
    low_confidence_score = Column(Float, nullable=True)
    user_feedback = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="pending")
    escalated_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    extra_metadata = Column("metadata", JSON, nullable=False, default=dict)


class AuditEventORM(Base):
    """AuditEvent ORM model (database table)."""

    __tablename__ = "audit_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    user_id = Column(String(255), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
