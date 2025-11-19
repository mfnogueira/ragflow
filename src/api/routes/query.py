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
        query_id=str(query.id),
        question=query.query_text,
        status=query.status,
        created_at=query.submitted_at.isoformat(),
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
            query_id=query.id,
            query_text=query.query_text,
            collection_name=request.collection or settings.default_collection,
            max_chunks=request.max_chunks or settings.max_chunks_per_query,
        )

        # Publish message
        import pika
        channel.basic_publish(
            exchange="",
            routing_key="queries",
            body=message.model_dump_json(),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Persistent
                content_type="application/json",
            ),
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
        query_id=str(query.id),
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
        query_id=str(query.id),
        question=query.query_text,
        status=query.status,
        answer=answer_text,
        confidence_score=confidence_score,
        sources=sources,
        created_at=query.submitted_at.isoformat(),
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

    # Call list_queries with named parameters
    queries = query_repo.list_queries(
        status=status_filter,
        limit=limit,
        offset=offset,
    )

    return [
        QueryResponse(
            query_id=str(q.id),
            question=q.query_text,
            status=q.status,
            created_at=q.submitted_at.isoformat(),
            completed_at=q.completed_at.isoformat() if q.completed_at else None,
        )
        for q in queries
    ]


@router.post(
    "/query/demo",
    response_model=AsyncQueryResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_query_demo(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> AsyncQueryResponse:
    """
    Demo endpoint que retorna respostas simuladas.

    Útil para testar a interface sem depender de RabbitMQ, OpenAI ou Qdrant.
    Cria a query no banco e retorna imediatamente com uma resposta simulada.
    """
    import time
    from datetime import datetime, timedelta

    logger.info(f"Received demo query: {request.question[:50]}...")

    # Create query in database
    query_repo = QueryRepository(db)

    query_id = str(uuid4())
    query = query_repo.create(
        query_id=query_id,
        question=request.question,
        collection=request.collection,
        max_chunks=request.max_chunks,
    )

    # Simular resposta baseada na pergunta
    demo_answers = {
        "negativ": "Com base nos reviews analisados, os principais motivos de avaliações negativas são: (1) Atrasos na entrega - muitos clientes reclamam de produtos que chegaram com semanas de atraso; (2) Produtos diferentes do anunciado - discrepâncias entre descrição e produto recebido; (3) Problemas com qualidade - produtos com defeitos ou danificados no transporte.",
        "elogiam": "Os clientes mais elogiam: (1) Qualidade dos produtos - muitos comentários sobre produtos que superaram expectativas; (2) Atendimento - vendedores atenciosos e prestativos; (3) Embalagem - cuidado no empacotamento e apresentação; (4) Preços competitivos - bom custo-benefício.",
        "categoria": "As categorias com melhores avaliações são: (1) Livros e mídia - score médio de 4.5/5; (2) Produtos de beleza e cuidados pessoais - 4.3/5; (3) Informática e eletrônicos - 4.2/5. As categorias com avaliações mais baixas incluem móveis (3.8/5) e produtos para casa (3.9/5).",
        "entrega": "As principais reclamações sobre entrega incluem: (1) Prazos não cumpridos - 45% das reclamações; (2) Falta de rastreamento - 25%; (3) Produtos perdidos ou extraviados - 15%; (4) Problemas com transportadora - 10%; (5) Outros - 5%.",
        "qualidade": "Sobre a qualidade dos produtos, os clientes mencionam: (1) Maioria dos produtos atende ou supera expectativas (65% positivo); (2) Alguns produtos com qualidade inferior ao esperado (20% negativo); (3) Problemas com descrições imprecisas (15%). Produtos de marcas reconhecidas têm melhor avaliação de qualidade."
    }

    # Encontrar melhor resposta
    question_lower = request.question.lower()
    answer_text = "Com base nos reviews analisados, podemos fornecer informações sobre diversos aspectos das avaliações de clientes. Os dados indicam padrões interessantes de satisfação e reclamações que podem ajudar a entender melhor a experiência dos consumidores."
    confidence = 0.75

    for keyword, text in demo_answers.items():
        if keyword in question_lower:
            answer_text = text
            confidence = 0.85
            break

    # Criar answer no banco
    from src.repositories.query_repo import QueryRepository
    from datetime import datetime

    answer_id = str(uuid4())
    answer_data = {
        "id": answer_id,
        "query_id": query_id,
        "answer_text": answer_text,
        "confidence_score": confidence,
        "model_name": "demo-mode",
        "prompt_tokens": 100,
        "completion_tokens": 150,
        "generated_at": datetime.utcnow(),
        "metadata": {"mode": "demo", "simulated": True}
    }

    query_repo.create_answer(
        query_id=query_id,
        answer_text=answer_text,
        confidence_score=confidence,
        model_name="demo-mode",
        prompt_tokens=100,
        completion_tokens=150,
    )

    # Atualizar status da query para completed
    query_repo.update_status(query_id, ProcessingStatus.COMPLETED)

    # Criar query results simulados (sources)
    from uuid import uuid4 as new_uuid

    for i in range(3):
        chunk_id = str(new_uuid())
        query_repo.create_query_result(
            query_id=query_id,
            chunk_id=chunk_id,
            similarity_score=0.85 - (i * 0.05),
            rank=i + 1,
        )

    logger.info(f"Demo query {query_id} processed successfully")

    return AsyncQueryResponse(
        query_id=query_id,
        message="Query queued for processing (DEMO MODE - usando respostas simuladas)",
    )
