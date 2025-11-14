"""Generate embeddings for chunks and store in Qdrant."""

import sys
import time
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sqlalchemy import text

from src.lib.config import settings
from src.lib.database import get_db_context
from src.lib.logger import get_logger

logger = get_logger(__name__)


def create_qdrant_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = 1536,
):
    """Create Qdrant collection if it doesn't exist."""
    print(f"Checking collection '{collection_name}'...")

    try:
        # Check if collection exists
        collections = client.get_collections()
        existing_names = [c.name for c in collections.collections]

        if collection_name in existing_names:
            print(f"  Collection '{collection_name}' already exists")
            # Get collection info
            info = client.get_collection(collection_name)
            print(f"  Vectors: {info.points_count}")
            print(f"  Vector size: {info.config.params.vectors.size}")
            return

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE,
            ),
        )
        print(f"  Created collection '{collection_name}'")
        print(f"  Vector size: {vector_size}")
        print(f"  Distance metric: COSINE")

    except Exception as e:
        logger.error(f"Failed to create collection: {e}")
        raise


def generate_embeddings(
    collection_name: str = "olist_reviews",
    batch_size: int = 10,
):
    """
    Generate embeddings for all chunks and store in Qdrant.

    Args:
        collection_name: PostgreSQL collection name
        batch_size: Number of chunks to process at once
    """
    print("="*60)
    print("EMBEDDING GENERATION")
    print("="*60)
    print()

    # Initialize clients
    print("Initializing clients...")
    openai_client = OpenAI(api_key=settings.openai_api_key)
    qdrant_client = QdrantClient(
        url=settings.qdrant_url.replace(":6333", ""),  # Remove port from URL
        api_key=settings.qdrant_api_key,
        timeout=settings.qdrant_timeout,
    )
    print("  [OK] OpenAI client initialized")
    print("  [OK] Qdrant client initialized")
    print()

    # Create Qdrant collection
    create_qdrant_collection(
        qdrant_client,
        collection_name,
        settings.vector_dimension,
    )
    print()

    # Get chunks from database
    with get_db_context() as db:
        result = db.execute(
            text("""
                SELECT c.id, c.text_content, c.metadata, d.collection_name
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.collection_name = :collection
                ORDER BY c.created_at
            """),
            {"collection": collection_name}
        )
        chunks = result.fetchall()

    if not chunks:
        print(f"No chunks found for collection '{collection_name}'")
        return

    print(f"Found {len(chunks)} chunks to process")
    print()

    # Process chunks in batches
    total_chunks = len(chunks)
    processed = 0
    failed = 0
    points = []

    print("Generating embeddings...")
    for i in range(0, total_chunks, batch_size):
        batch = chunks[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (total_chunks + batch_size - 1) // batch_size

        print(f"Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        try:
            # Extract texts for embedding
            texts = [chunk[1] for chunk in batch]

            # Generate embeddings
            response = openai_client.embeddings.create(
                model=settings.openai_embedding_model,
                input=texts,
            )

            # Create Qdrant points
            for idx, chunk in enumerate(batch):
                chunk_id = str(chunk[0])
                embedding = response.data[idx].embedding
                metadata = chunk[2]  # Already a dict from JSONB

                # Add collection to metadata
                metadata["collection"] = collection_name

                point = PointStruct(
                    id=chunk_id,
                    vector=embedding,
                    payload=metadata,
                )
                points.append(point)

            processed += len(batch)
            print(f"  Generated {len(batch)} embeddings")

            # Rate limiting - be nice to OpenAI
            if i + batch_size < total_chunks:
                time.sleep(0.5)

        except Exception as e:
            failed += len(batch)
            logger.error(f"Failed to process batch {batch_num}: {e}")
            print(f"  [ERROR] Failed: {e}")

    print()
    print(f"Embedding generation complete:")
    print(f"  Processed: {processed}/{total_chunks}")
    print(f"  Failed: {failed}")
    print()

    # Upload to Qdrant
    if points:
        print(f"Uploading {len(points)} vectors to Qdrant...")
        try:
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points,
            )
            print(f"  [OK] Uploaded {len(points)} vectors")
        except Exception as e:
            logger.error(f"Failed to upload to Qdrant: {e}")
            print(f"  [ERROR] Upload failed: {e}")
            return

    print()

    # Verify in Qdrant
    try:
        info = qdrant_client.get_collection(collection_name)
        print(f"Qdrant collection '{collection_name}':")
        print(f"  Total vectors: {info.points_count}")
        print(f"  Vector size: {info.config.params.vectors.size}")
        print(f"  Distance: {info.config.params.vectors.distance}")
    except Exception as e:
        logger.error(f"Failed to verify collection: {e}")

    print()
    print("="*60)
    print("EMBEDDING GENERATION COMPLETE!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Test semantic search queries")
    print("  2. Implement retrieval service")
    print("  3. Build complete RAG pipeline")
    print()


if __name__ == "__main__":
    generate_embeddings()
