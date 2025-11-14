"""Test semantic search with Qdrant and OpenAI embeddings."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from qdrant_client import QdrantClient

from src.lib.config import settings
from src.lib.logger import get_logger

logger = get_logger(__name__)


def test_semantic_search(query: str, top_k: int = 5):
    """
    Test semantic search with a query.

    Args:
        query: Natural language query
        top_k: Number of results to return
    """
    print("="*60)
    print("SEMANTIC SEARCH TEST")
    print("="*60)
    print()
    print(f"Query: {query}")
    print(f"Top K: {top_k}")
    print()

    # Initialize clients
    print("Initializing clients...")
    openai_client = OpenAI(api_key=settings.openai_api_key)
    qdrant_client = QdrantClient(
        url=settings.qdrant_url.replace(":6333", ""),
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout,
    )
    print("  [OK] Clients initialized")
    print()

    # Generate query embedding
    print("Generating query embedding...")
    try:
        response = openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=query,
        )
        query_vector = response.data[0].embedding
        print(f"  [OK] Generated embedding (dimension: {len(query_vector)})")
    except Exception as e:
        logger.error(f"Failed to generate query embedding: {e}")
        print(f"  [ERROR] {e}")
        return

    print()

    # Search Qdrant
    print(f"Searching Qdrant for top {top_k} results...")
    try:
        search_results = qdrant_client.search(
            collection_name="olist_reviews",
            query_vector=query_vector,
            limit=top_k,
        )
        print(f"  [OK] Found {len(search_results)} results")
    except Exception as e:
        logger.error(f"Failed to search Qdrant: {e}")
        print(f"  [ERROR] {e}")
        return

    print()

    # Display results
    print("Search Results:")
    print("-" * 60)

    for idx, result in enumerate(search_results, 1):
        print(f"\nResult #{idx}")
        print(f"  Score: {result.score:.4f}")
        print(f"  Chunk ID: {result.id}")

        # Display metadata
        if result.payload:
            print(f"  Metadata:")
            for key, value in result.payload.items():
                # Skip very long fields
                if key == "collection":
                    continue
                if isinstance(value, str) and len(value) > 100:
                    print(f"    {key}: {value[:100]}...")
                else:
                    print(f"    {key}: {value}")

    print()
    print("="*60)
    print("SEMANTIC SEARCH TEST COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    # Test queries in Portuguese (Olist reviews are in Brazilian Portuguese)
    test_queries = [
        "Qual a avaliação sobre entrega?",
        "Produtos com problemas de qualidade",
        "Clientes satisfeitos com a compra",
    ]

    print("\n" * 2)
    print("*" * 60)
    print("RUNNING MULTIPLE SEMANTIC SEARCH TESTS")
    print("*" * 60)
    print()

    for query in test_queries:
        test_semantic_search(query, top_k=3)
        print("\n" * 2)
