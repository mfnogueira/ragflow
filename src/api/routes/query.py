"""Query endpoints for RAG Q&A system."""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.lib.config import settings
from src.lib.database import get_db
from src.lib.logger import get_logger
from src.lib.queue import get_rabbitmq_channel
from src.models.query import Query as QueryModel, ProcessingStatus
from src.models.messages import ProcessQueryMessage
from src.repositories.query_repo import QueryRepository

logger = get_logger(__name__)
router = APIRouter()


# Request/Response models
class QueryRequest(BaseModel):
    """Query request model."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=settings.max_query_length,
        description="User question about Olist order reviews",
    )
    collection: Optional[str] = Field(
        default=settings.default_collection,
        description="Collection to query (default: olist_reviews)",
    )
    max_chunks: Optional[int] = Field(
        default=settings.max_chunks_per_query,
        ge=1,
        le=50,
        description="Maximum number of chunks to retrieve",
    )
    confidence_threshold: Optional[float] = Field(
        default=settings.confidence_threshold,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for answers",
    )


class QueryResponse(BaseModel):
    """Query response model."""

    query_id: str
    question: str
    status: ProcessingStatus
    answer: Optional[str] = None
    confidence_score: Optional[float] = None
    sources: Optional[list] = None
    created_at: str
    completed_at: Optional[str] = None

    class Config:
        from_attributes = True


class AsyncQueryResponse(BaseModel):
    """Async query response model."""

    query_id: str
    status: str
    message: str


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def create_query_sync(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Synchronous query endpoint.

    Creates a query and waits for the answer (blocking).
    Use for real-time interactions where immediate response is needed.

    **Note**: This endpoint is a placeholder for MVP.
    In production, implement proper async handling with WebSocket or polling.
    """
    logger.info(f"Received synchronous query: {request.question[:50]}...")

    # Create query in database
    query_repo = QueryRepository(db)

    query_id = str(uuid4())
    query = query_repo.create(
        query_id=query_id,
        question=request.question,
        collection=request.collection,
        max_chunks=request.max_chunks,
    )

    # For MVP: Return pending status
    # In production: Implement proper synchronous flow with timeout
    return QueryResponse(
        query_id=query.id,
        question=query.question,
        status=query.status,
        created_at=query.created_at.isoformat(),
    )


@router.post(
    "/query/async",
    response_model=AsyncQueryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_query_async(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> AsyncQueryResponse:
    """
    Asynchronous query endpoint.

    Creates a query and publishes to RabbitMQ for processing.
    Returns immediately with query_id for status polling.

    Use for batch processing or when immediate response is not required.
    """
    logger.info(f"Received asynchronous query: {request.question[:50]}...")

    # Create query in database
    query_repo = QueryRepository(db)

    query_id = str(uuid4())
    query = query_repo.create(
        query_id=query_id,
        question=request.question,
        collection=request.collection,
        max_chunks=request.max_chunks,
    )

    # Publish to RabbitMQ
    try:
        channel = get_rabbitmq_channel()

        # Declare queries queue
        channel.queue_declare(queue="queries", durable=True)

        # Create message
        message = ProcessQueryMessage(
            message_id=query.id,
            query_id=query.id,
            question=query.question,
            collection=request.collection or settings.default_collection,
            max_chunks=request.max_chunks or settings.max_chunks_per_query,
            confidence_threshold=request.confidence_threshold or settings.confidence_threshold,
        )

        # Publish message
        channel.basic_publish(
            exchange="",
            routing_key="queries",
            body=message.model_dump_json(),
            properties={
                "delivery_mode": 2,  # Persistent
                "content_type": "application/json",
            },
        )

        channel.close()

        logger.info(f"Query {query_id} published to queue")

    except Exception as e:
        logger.error(f"Failed to publish query to RabbitMQ: {e}")
        query_repo.update_status(query_id, ProcessingStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to queue query for processing",
        )

    return AsyncQueryResponse(
        query_id=query.id,
        status="accepted",
        message=f"Query accepted for processing. Use GET /api/v1/query/{query.id} to check status.",
    )


@router.get("/query/{query_id}", response_model=QueryResponse)
async def get_query_status(
    query_id: str,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Get query status and results.

    Returns the current status of a query and its answer if available.
    """
    query_repo = QueryRepository(db)

    query = query_repo.get_by_id(query_id)
    if not query:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found",
        )

    # Get answer if completed
    answer_text = None
    confidence_score = None
    sources = None

    if query.status == ProcessingStatus.COMPLETED and query.answers:
        # Get the latest answer
        latest_answer = query.answers[0]
        answer_text = latest_answer.answer_text
        confidence_score = latest_answer.confidence_score

        # Get sources from query_results
        if query.query_results:
            sources = [
                {
                    "chunk_id": qr.chunk_id,
                    "similarity_score": float(qr.similarity_score),
                    "rank": qr.rank,
                }
                for qr in query.query_results
            ]

    return QueryResponse(
        query_id=query.id,
        question=query.question,
        status=query.status,
        answer=answer_text,
        confidence_score=confidence_score,
        sources=sources,
        created_at=query.created_at.isoformat(),
        completed_at=query.completed_at.isoformat() if query.completed_at else None,
    )


@router.get("/queries", response_model=list[QueryResponse])
async def list_queries(
    limit: int = 10,
    offset: int = 0,
    status_filter: Optional[ProcessingStatus] = None,
    db: Session = Depends(get_db),
) -> list[QueryResponse]:
    """
    List recent queries.

    Returns paginated list of queries, optionally filtered by status.
    """
    query_repo = QueryRepository(db)

    # Build filter
    filters = {}
    if status_filter:
        filters["status"] = status_filter

    queries = query_repo.list_queries(limit=limit, offset=offset, filters=filters)

    return [
        QueryResponse(
            query_id=q.id,
            question=q.question,
            status=q.status,
            created_at=q.created_at.isoformat(),
            completed_at=q.completed_at.isoformat() if q.completed_at else None,
        )
        for q in queries
    ]
