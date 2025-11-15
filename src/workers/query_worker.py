"""Query Worker for processing RAG queries asynchronously."""

from datetime import datetime
from typing import Any, Dict
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.lib.config import settings
from src.lib.database import get_db_context
from src.lib.logger import get_logger
from src.models.orm import AnswerORM, QueryResultORM
from src.models.query import ProcessingStatus
from src.repositories.query_repo import QueryRepository
from src.services.embedding_service import get_embedding_service
from src.services.generation_service import get_generation_service
from src.services.guardrails_service import get_guardrails_service
from src.services.retrieval_service import get_retrieval_service
from src.workers.base_worker import BaseWorker

logger = get_logger(__name__)


class QueryWorker(BaseWorker):
    """
    Worker for processing RAG queries.

    Orchestrates the complete RAG pipeline:
    1. Validate query with guardrails
    2. Generate query embedding
    3. Retrieve relevant chunks
    4. Generate answer with LLM
    5. Store results in database
    """

    def __init__(self, queue_name: str = "queries"):
        """
        Initialize Query Worker.

        Args:
            queue_name: Name of the queue to consume from (default: "queries")
        """
        super().__init__(
            queue_name=queue_name,
            prefetch_count=settings.query_concurrency,
            auto_ack=False,
        )

        # Initialize services
        self.guardrails_service = get_guardrails_service()
        self.embedding_service = get_embedding_service()
        self.retrieval_service = get_retrieval_service()
        self.generation_service = get_generation_service()

        logger.info("Query Worker initialized with all services")

    def process_message(self, message: Dict[str, Any]) -> Any:
        """
        Process a query message through the RAG pipeline.

        Args:
            message: Message containing query data
                - message_id: Unique message ID
                - query_id: Query UUID
                - question: User's question
                - collection: Collection name
                - max_chunks: Max chunks to retrieve
                - confidence_threshold: Min confidence threshold

        Returns:
            Processing result

        Raises:
            Exception: If processing fails
        """
        query_id = message.get("query_id")
        question = message.get("query_text")  # Note: field name is query_text in message
        collection = message.get("collection_name", settings.default_collection)
        max_chunks = message.get("max_chunks", settings.max_chunks_per_query)
        confidence_threshold = message.get(
            "confidence_threshold", settings.confidence_threshold
        )

        logger.info(f"Processing query {query_id}: {question[:50]}...")

        with get_db_context() as db:
            query_repo = QueryRepository(db)

            try:
                # Update status to processing
                query_repo.update_query_status(
                    UUID(query_id), ProcessingStatus.PROCESSING
                )
                logger.info(f"Query {query_id} status → PROCESSING")

                # Step 1: Validate with guardrails
                logger.info(f"[{query_id}] Step 1: Validating query...")
                validation_result = self.guardrails_service.validate_query(question)

                if not validation_result.is_valid:
                    logger.warning(
                        f"Query {query_id} failed validation: {validation_result.reason}"
                    )
                    query_repo.update_query_status(
                        UUID(query_id), ProcessingStatus.FAILED
                    )
                    return {
                        "status": "failed",
                        "reason": validation_result.reason,
                    }

                # Use sanitized input
                sanitized_question = validation_result.sanitized_input
                logger.info(f"[{query_id}] ✓ Query validated")

                # Step 2: Generate query embedding
                logger.info(f"[{query_id}] Step 2: Generating embedding...")
                query_embedding = self.embedding_service.generate_embedding(
                    sanitized_question
                )
                logger.info(f"[{query_id}] ✓ Embedding generated (dim={len(query_embedding)})")

                # Step 3: Retrieve relevant chunks
                logger.info(f"[{query_id}] Step 3: Retrieving chunks (top_k={max_chunks})...")
                retrieval_results = self.retrieval_service.retrieve(
                    query_vector=query_embedding,
                    collection=collection,
                    top_k=max_chunks,
                    min_score=0.0,  # Will filter by confidence later
                )

                if not retrieval_results:
                    logger.warning(f"Query {query_id}: No chunks retrieved")
                    query_repo.update_query_status(
                        UUID(query_id), ProcessingStatus.FAILED
                    )
                    return {
                        "status": "failed",
                        "reason": "No relevant documents found",
                    }

                logger.info(
                    f"[{query_id}] ✓ Retrieved {len(retrieval_results)} chunks "
                    f"(scores: {retrieval_results[0].similarity_score:.3f} - {retrieval_results[-1].similarity_score:.3f})"
                )

                # Step 4: Generate answer with LLM
                logger.info(f"[{query_id}] Step 4: Generating answer...")
                generation_result = self.generation_service.generate_answer(
                    question=sanitized_question,
                    retrieval_results=retrieval_results,
                )

                logger.info(
                    f"[{query_id}] ✓ Answer generated "
                    f"(confidence={generation_result.confidence_score:.3f}, "
                    f"length={len(generation_result.answer)})"
                )

                # Step 5: Check confidence threshold
                if generation_result.confidence_score < confidence_threshold:
                    logger.warning(
                        f"Query {query_id}: Low confidence "
                        f"({generation_result.confidence_score:.3f} < {confidence_threshold})"
                    )
                    # TODO: Create escalation request
                    # For now, we still save the answer but mark it

                # Step 6: Save results to database
                logger.info(f"[{query_id}] Step 5: Saving results...")

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
                    extra_metadata={
                        "sources_used": generation_result.sources_used,
                        "temperature": settings.llm_temperature,
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
                        rank=result.rank,
                        retrieved_at=datetime.utcnow(),
                    )
                    db.add(query_result)

                # Commit all changes
                db.commit()

                # Update query status to completed
                query_repo.update_query_status(
                    UUID(query_id), ProcessingStatus.COMPLETED
                )

                logger.info(
                    f"[{query_id}] ✓ Query processing completed successfully "
                    f"(answer_id={answer_id})"
                )

                return {
                    "status": "completed",
                    "query_id": query_id,
                    "answer_id": str(answer_id),
                    "confidence_score": generation_result.confidence_score,
                    "chunks_retrieved": len(retrieval_results),
                }

            except Exception as e:
                logger.error(f"Query {query_id} processing failed: {e}", exc_info=True)

                # Update status to failed
                try:
                    query_repo.update_query_status(
                        UUID(query_id), ProcessingStatus.FAILED
                    )
                except Exception as db_error:
                    logger.error(f"Failed to update query status: {db_error}")

                raise


def main():
    """Run the Query Worker."""
    logger.info("="*60)
    logger.info("QUERY WORKER")
    logger.info("="*60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Collection: {settings.default_collection}")
    logger.info(f"Concurrency: {settings.query_concurrency}")
    logger.info("="*60)
    logger.info("")

    worker = QueryWorker()

    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        worker.stop()
    except Exception as e:
        logger.error(f"Worker crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
