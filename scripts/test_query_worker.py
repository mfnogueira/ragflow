"""Test script for Query Worker - publishes test queries to RabbitMQ."""

import json
import sys
import time
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pika

from src.lib.config import settings
from src.lib.database import get_db_context
from src.lib.logger import get_logger
from src.models.messages import ProcessQueryMessage
from src.models.query import ProcessingStatus
from src.repositories.query_repo import QueryRepository

logger = get_logger(__name__)


def publish_test_query(
    question: str,
    collection: str = "olist_reviews",
    max_chunks: int = 5,
) -> str:
    """
    Publish a test query to RabbitMQ.

    Args:
        question: User's question
        collection: Collection name
        max_chunks: Max chunks to retrieve

    Returns:
        Query ID
    """
    print("="*60)
    print("PUBLISHING TEST QUERY TO RABBITMQ")
    print("="*60)
    print()

    # Create query in database
    with get_db_context() as db:
        query_repo = QueryRepository(db)
        query_id = str(uuid4())

        print(f"Creating query in database...")
        print(f"  Query ID: {query_id}")
        print(f"  Question: {question}")
        print(f"  Collection: {collection}")
        print()

        query = query_repo.create(
            query_id=query_id,
            question=question,
            collection=collection,
            max_chunks=max_chunks,
        )

    # Publish to RabbitMQ
    print(f"Publishing to RabbitMQ queue 'queries'...")

    try:
        parameters = pika.URLParameters(settings.rabbitmq_url)
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # Declare queue
        channel.queue_declare(queue="queries", durable=True)

        # Create message
        message = ProcessQueryMessage(
            message_id=query_id,
            query_id=query_id,
            query_text=question,
            collection_name=collection,
            max_chunks=max_chunks,
            confidence_threshold=settings.confidence_threshold,
        )

        # Publish
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
        connection.close()

        print(f"  [OK] Message published")
        print()

    except Exception as e:
        logger.error(f"Failed to publish to RabbitMQ: {e}")
        print(f"  [ERROR] {e}")
        return query_id

    print("="*60)
    print(f"TEST QUERY PUBLISHED: {query_id}")
    print("="*60)
    print()
    print("Next steps:")
    print(f"  1. Start the Query Worker: python src/workers/query_worker.py")
    print(f"  2. Monitor logs to see processing")
    print(f"  3. Check query status: python scripts/check_query_status.py {query_id}")
    print()

    return query_id


def check_query_status(query_id: str) -> None:
    """
    Check the status of a query.

    Args:
        query_id: Query UUID
    """
    print("="*60)
    print("CHECKING QUERY STATUS")
    print("="*60)
    print()

    with get_db_context() as db:
        query_repo = QueryRepository(db)

        try:
            from uuid import UUID
            query = query_repo.get_by_id(query_id)

            if not query:
                print(f"Query {query_id} not found")
                return

            print(f"Query ID: {query.id}")
            print(f"Question: {query.question}")
            print(f"Status: {query.status.value}")
            print(f"Submitted: {query.submitted_at}")
            print(f"Completed: {query.completed_at or 'N/A'}")
            print()

            if query.status == ProcessingStatus.COMPLETED:
                print("Answer:")
                if query.answers:
                    answer = query.answers[0]
                    print(f"  {answer.answer_text}")
                    print()
                    print(f"  Confidence: {answer.confidence_score:.3f}")
                    print(f"  Model: {answer.model_name}")
                    print(f"  Tokens: {answer.prompt_tokens + answer.completion_tokens}")
                    print()

                if query.query_results:
                    print(f"Sources ({len(query.query_results)} chunks):")
                    for qr in query.query_results[:3]:
                        print(f"  - Chunk {qr.chunk_id} (score: {qr.similarity_score:.3f}, rank: {qr.rank})")
                    print()

            elif query.status == ProcessingStatus.FAILED:
                print("Query processing failed")
                print()

            elif query.status == ProcessingStatus.PENDING:
                print("Query is pending (waiting for worker)")
                print()

            elif query.status == ProcessingStatus.PROCESSING:
                print("Query is being processed...")
                print()

        except Exception as e:
            logger.error(f"Failed to check query status: {e}")
            print(f"[ERROR] {e}")

    print("="*60)


def main():
    """Run test queries."""
    print("\n" * 2)
    print("*" * 60)
    print("QUERY WORKER TEST SUITE")
    print("*" * 60)
    print()

    # Test queries in Portuguese
    test_queries = [
        "Quais produtos têm mais reclamações dos clientes?",
        "O que os clientes dizem sobre a qualidade dos produtos?",
        "Como é a experiência de entrega segundo as avaliações?",
    ]

    query_ids = []

    for idx, question in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"TEST QUERY {idx}/{len(test_queries)}")
        print(f"{'='*60}\n")

        query_id = publish_test_query(question)
        query_ids.append(query_id)

        # Wait a bit between queries
        if idx < len(test_queries):
            time.sleep(2)

    print("\n" * 2)
    print("*" * 60)
    print(f"PUBLISHED {len(query_ids)} TEST QUERIES")
    print("*" * 60)
    print()
    print("Query IDs:")
    for qid in query_ids:
        print(f"  - {qid}")
    print()
    print("To start the worker:")
    print("  python src/workers/query_worker.py")
    print()
    print("To check status:")
    for qid in query_ids:
        print(f"  python scripts/check_query_status.py {qid}")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Check specific query status
        query_id = sys.argv[1]
        check_query_status(query_id)
    else:
        # Publish test queries
        main()
