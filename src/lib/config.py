"""Application configuration using Pydantic Settings."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    debug: bool = False

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = "dev-api-key-12345"

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/ragflow"
    )
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # RabbitMQ
    rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"
    rabbitmq_api_key: str = ""  # CloudAMQP management API key
    rabbitmq_prefetch_count: int = 5
    rabbitmq_connection_attempts: int = 3
    rabbitmq_retry_delay: int = 5

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_timeout: int = 30

    # Redis (Optional - not required for MVP)
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_max_connections: int = 50
    enable_redis_cache: bool = False  # Set to True to enable Redis caching

    # OpenAI API
    openai_api_key: str = Field(default="")
    openai_model: str = "gpt-4o-mini"  # LLM model for answer generation
    openai_llm_model: str = "gpt-4o-mini"  # Alias for backward compatibility
    openai_embedding_model: str = "text-embedding-3-small"
    openai_max_retries: int = 3
    openai_timeout: int = 60
    llm_temperature: float = 0.7  # Temperature for answer generation (0-1)
    max_answer_length: int = 500  # Maximum tokens for generated answers

    # RAG Configuration
    chunk_size: int = 512
    chunk_overlap: float = 0.2
    max_chunks_per_query: int = 10
    confidence_threshold: float = 0.7
    enable_reranking: bool = False

    # Guardrails
    max_query_length: int = 1000
    enable_pii_detection: bool = True
    enable_prompt_injection_detection: bool = True

    # Caching (Optional - Redis not required for MVP)
    cache_ttl_seconds: int = 3600
    enable_semantic_cache: bool = False  # Requires Redis

    # Monitoring
    prometheus_port: int = 9090
    jaeger_agent_host: str = "localhost"
    jaeger_agent_port: int = 6831
    enable_tracing: bool = True

    # Collections
    default_collection: str = "olist_reviews"
    vector_dimension: int = 1536

    # Worker Configuration
    embedding_batch_size: int = 100
    embedding_concurrency: int = 5
    query_concurrency: int = 10
    ingest_concurrency: int = 3

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


# Global settings instance
settings = Settings()
