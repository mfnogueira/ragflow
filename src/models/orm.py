"""SQLAlchemy ORM models for database tables."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Enum, Boolean
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
        String(50),
        nullable=False,
        default=ProcessingStatus.PENDING.value,
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
    user_id = Column(String(255), nullable=True)
    collection_name = Column(String(100), nullable=False, index=True)
    language_code = Column(String(10), nullable=False, default='pt-BR')
    status = Column(
        String(50),
        nullable=False,
        default=QueryProcessingStatus.PENDING.value,
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
    model_name = Column("llm_model_used", String(100), nullable=False)
    prompt_tokens = Column("token_count_input", Integer, nullable=False, default=0)
    completion_tokens = Column("token_count_output", Integer, nullable=False, default=0)
    generated_at = Column("generation_timestamp", DateTime, nullable=False, default=datetime.utcnow)

    # Performance metrics columns (from migration 004)
    retrieval_latency_ms = Column(Float, nullable=False, default=0.0)
    generation_latency_ms = Column(Float, nullable=False, default=0.0)
    total_latency_ms = Column(Float, nullable=False, default=0.0)

    # Status columns (from migration 004)
    cache_hit = Column(Boolean, nullable=False, default=False)
    validation_status = Column(String(20), nullable=False, default='passed')
    escalation_flag = Column(Boolean, nullable=False, default=False)
    redaction_flag = Column(Boolean, nullable=False, default=False)

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
    relevance_score = Column(Float, nullable=False)  # Same as similarity_score (required by DB)
    reranking_score = Column(Float, nullable=True)  # Optional reranking score
    rank = Column("rank_position", Integer, nullable=False)  # Maps to rank_position column
    retrieved_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    metadata_match_flags = Column(JSON, nullable=False, default=dict)  # Metadata matching flags

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
