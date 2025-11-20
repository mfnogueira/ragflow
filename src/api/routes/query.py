"""Query endpoints for RAG Q&A system."""

from typing import Optional
from uuid import uuid4
from datetime import datetime

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


@router.post("/query/sync", response_model=QueryResponse, status_code=status.HTTP_200_OK)
async def create_query_sync(
    request: QueryRequest,
    db: Session = Depends(get_db),
) -> QueryResponse:
    """
    Synchronous query endpoint - Executa pipeline RAG completo.

    Processa a query completamente e retorna a resposta final.
    Usa este endpoint quando o sistema integrado espera resposta imediata.

    **Atenção**: Esta requisição pode levar 3-10 segundos para completar,
    pois executa todo o pipeline RAG (validação, embedding, retrieval, geração).

    Args:
        request: QueryRequest com a pergunta e parâmetros
        db: Database session

    Returns:
        QueryResponse com resposta completa e fontes

    Raises:
        HTTPException 400: Query inválida (guardrails)
        HTTPException 404: Nenhum documento relevante encontrado
        HTTPException 500: Erro interno no processamento
    """
    from src.services.guardrails_service import get_guardrails_service
    from src.services.embedding_service import get_embedding_service
    from src.services.retrieval_service import get_retrieval_service
    from src.services.generation_service import get_generation_service
    from src.models.orm import AnswerORM, QueryResultORM
    from uuid import UUID

    logger.info(f"[SYNC] Received query: {request.question[:50]}...")

    # Initialize services
    guardrails = get_guardrails_service()
    embedding = get_embedding_service()
    retrieval = get_retrieval_service()
    generation = get_generation_service()

    # Create query in database
    query_repo = QueryRepository(db)
    query_id = str(uuid4())

    try:
        # Create query record
        query = query_repo.create(
            query_id=query_id,
            question=request.question,
            collection=request.collection,
            max_chunks=request.max_chunks,
        )

        # Update to processing
        query_repo.update_query_status(UUID(query_id), ProcessingStatus.PROCESSING)

        # Step 1: Validate with guardrails
        logger.info(f"[SYNC][{query_id}] Step 1: Validating query...")
        validation_result = await guardrails.validate_query(request.question)

        if not validation_result.is_valid:
            logger.warning(f"[SYNC][{query_id}] Validation failed: {validation_result.reason}")
            query_repo.update_query_status(UUID(query_id), ProcessingStatus.FAILED)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Query validation failed: {validation_result.reason}",
            )

        sanitized_question = validation_result.sanitized_input
        logger.info(f"[SYNC][{query_id}] ✓ Query validated")

        # Step 2: Generate embedding
        logger.info(f"[SYNC][{query_id}] Step 2: Generating embedding...")
        query_embedding = await embedding.generate_embedding(sanitized_question)
        logger.info(f"[SYNC][{query_id}] ✓ Embedding generated (dim={len(query_embedding)})")

        # Step 3: Retrieve relevant chunks
        logger.info(f"[SYNC][{query_id}] Step 3: Retrieving chunks...")
        retrieval_results = await retrieval.retrieve(
            query_vector=query_embedding,
            collection=request.collection or settings.default_collection,
            top_k=request.max_chunks or settings.max_chunks_per_query,
            min_score=0.0,
        )

        if not retrieval_results:
            logger.warning(f"[SYNC][{query_id}] No chunks retrieved")
            query_repo.update_query_status(UUID(query_id), ProcessingStatus.FAILED)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant documents found for this query",
            )

        logger.info(
            f"[SYNC][{query_id}] ✓ Retrieved {len(retrieval_results)} chunks "
            f"(scores: {retrieval_results[0].similarity_score:.3f} - {retrieval_results[-1].similarity_score:.3f})"
        )

        # Step 4: Generate answer
        logger.info(f"[SYNC][{query_id}] Step 4: Generating answer...")
        generation_result = await generation.generate_answer(
            question=sanitized_question,
            retrieval_results=retrieval_results,
        )

        logger.info(
            f"[SYNC][{query_id}] ✓ Answer generated "
            f"(confidence={generation_result.confidence_score:.3f}, length={len(generation_result.answer)})"
        )

        # Step 5: Save results to database
        logger.info(f"[SYNC][{query_id}] Step 5: Saving results...")

        # Save answer
        answer_id = uuid4()
        answer = AnswerORM(
            id=answer_id,
            query_id=UUID(query_id),
            answer_text=generation_result.answer,
            confidence_score=generation_result.confidence_score,
            model_name=generation_result.model,
            prompt_tokens=generation_result.prompt_tokens,
            completion_tokens=generation_result.completion_tokens,
            generated_at=datetime.utcnow(),
            retrieval_latency_ms=0.0,
            generation_latency_ms=0.0,
            total_latency_ms=0.0,
            cache_hit=False,
            validation_status='passed',
            escalation_flag=False,
            redaction_flag=False,
            extra_metadata={
                "sources_used": generation_result.sources_used,
                "temperature": settings.llm_temperature,
                "sync_mode": True,
            },
        )
        db.add(answer)

        # Save query results (retrieved chunks)
        for result in retrieval_results:
            query_result = QueryResultORM(
                id=uuid4(),
                query_id=UUID(query_id),
                chunk_id=UUID(result.chunk_id),
                similarity_score=result.similarity_score,
                relevance_score=result.similarity_score,
                reranking_score=None,
                rank=result.rank,
                retrieved_at=datetime.utcnow(),
                metadata_match_flags={},
            )
            db.add(query_result)

        # Commit all changes
        db.commit()

        # Update query status to completed
        query_repo.update_query_status(UUID(query_id), ProcessingStatus.COMPLETED)

        logger.info(f"[SYNC][{query_id}] ✓ Query completed successfully")

        # Prepare sources for response
        sources = [
            {
                "chunk_id": str(result.chunk_id),
                "similarity_score": float(result.similarity_score),
                "rank": result.rank,
            }
            for result in retrieval_results
        ]

        return QueryResponse(
            query_id=query_id,
            question=request.question,
            status=ProcessingStatus.COMPLETED,
            answer=generation_result.answer,
            confidence_score=generation_result.confidence_score,
            sources=sources,
            created_at=query.submitted_at.isoformat(),
            completed_at=datetime.utcnow().isoformat(),
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"[SYNC][{query_id}] Processing failed: {e}", exc_info=True)

        # Update status to failed
        try:
            query_repo.update_query_status(UUID(query_id), ProcessingStatus.FAILED)
        except Exception as db_error:
            logger.error(f"Failed to update query status: {db_error}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing query: {str(e)}",
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
    from src.models.orm import AnswerORM

    answer_orm = AnswerORM(
        id=uuid4(),
        query_id=query_id,
        answer_text=answer_text,
        confidence_score=confidence,
        model_name="demo-mode",
        prompt_tokens=100,
        completion_tokens=150,
        generated_at=datetime.utcnow(),
        retrieval_latency_ms=0.0,
        generation_latency_ms=0.0,
        total_latency_ms=0.0,
        cache_hit=False,
        validation_status='passed',
        escalation_flag=False,
        redaction_flag=False,
        extra_metadata={"mode": "demo", "simulated": True}
    )
    query_repo.create_answer(answer_orm)

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
