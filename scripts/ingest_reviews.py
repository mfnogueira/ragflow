"""Ingest processed reviews into the RAG system."""

import json
import sys
from pathlib import Path
from uuid import uuid4

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from src.lib.config import settings
from src.lib.database import get_db_context
from src.lib.logger import get_logger

logger = get_logger(__name__)


def ingest_documents(documents_file: Path, collection: str = "olist_reviews"):
    """
    Ingest documents into PostgreSQL database.

    Args:
        documents_file: Path to JSON file with documents
        collection: Collection name
    """
    print("="*60)
    print("DOCUMENT INGESTION")
    print("="*60)
    print()

    # Load documents
    with open(documents_file, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"Loaded {len(documents)} documents from {documents_file}")
    print()

    # Verify collection exists
    with get_db_context() as db:
        result = db.execute(
            text("SELECT COUNT(*) FROM collections WHERE name = :name"),
            {"name": collection}
        )
        if result.scalar() == 0:
            print(f"ERROR: Collection '{collection}' does not exist!")
            print(f"Please create the collection first.")
            return

    print(f"Collection '{collection}' exists")
    print()

    # Ingest documents
    ingested_count = 0
    failed_count = 0

    with get_db_context() as db:
        for idx, doc in enumerate(documents, 1):
            try:
                # Generate document ID
                doc_id = str(uuid4())

                # Insert document
                db.execute(
                    text("""
                        INSERT INTO documents (
                            id,
                            file_name,
                            file_format,
                            file_size_bytes,
                            collection_name,
                            language_code,
                            status,
                            chunk_count,
                            uploaded_at,
                            metadata
                        ) VALUES (
                            :id,
                            :file_name,
                            :file_format,
                            :file_size_bytes,
                            :collection_name,
                            :language_code,
                            :status,
                            :chunk_count,
                            NOW(),
                            :metadata
                        )
                    """),
                    {
                        "id": doc_id,
                        "file_name": doc["source"],
                        "file_format": "txt",
                        "file_size_bytes": len(doc["content"].encode('utf-8')),
                        "collection_name": collection,
                        "language_code": "pt-BR",
                        "status": "pending",
                        "chunk_count": 0,
                        "metadata": json.dumps(doc["metadata"]),
                    }
                )

                # Create a single chunk for the review (reviews are small)
                chunk_id = str(uuid4())
                content = doc["content"]

                db.execute(
                    text("""
                        INSERT INTO chunks (
                            id,
                            document_id,
                            text_content,
                            sequence_position,
                            token_count,
                            char_start_offset,
                            char_end_offset,
                            language_code,
                            created_at,
                            metadata
                        ) VALUES (
                            :id,
                            :document_id,
                            :text_content,
                            :sequence_position,
                            :token_count,
                            :char_start_offset,
                            :char_end_offset,
                            :language_code,
                            NOW(),
                            :metadata
                        )
                    """),
                    {
                        "id": chunk_id,
                        "document_id": doc_id,
                        "text_content": content,
                        "sequence_position": 0,
                        "token_count": len(content.split()),
                        "char_start_offset": 0,
                        "char_end_offset": len(content),
                        "language_code": "pt-BR",
                        "metadata": json.dumps(doc["metadata"]),
                    }
                )

                # Update document chunk count and status
                db.execute(
                    text("""
                        UPDATE documents
                        SET chunk_count = 1,
                            status = 'completed',
                            processed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": doc_id}
                )

                ingested_count += 1

                if ingested_count % 10 == 0:
                    print(f"Ingested {ingested_count}/{len(documents)} documents...")

            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to ingest document {idx}: {e}")
                print(f"  [ERROR] Document {idx}: {e}")

        # Commit all changes
        db.commit()

    print()
    print("Ingestion Summary:")
    print(f"  Total documents: {len(documents)}")
    print(f"  Successfully ingested: {ingested_count}")
    print(f"  Failed: {failed_count}")
    print()

    # Update collection statistics
    with get_db_context() as db:
        db.execute(
            text("""
                UPDATE collections
                SET document_count = (
                    SELECT COUNT(*)
                    FROM documents
                    WHERE collection_name = :collection
                ),
                total_vector_count = (
                    SELECT COUNT(*)
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.collection_name = :collection
                ),
                last_updated_at = NOW()
                WHERE name = :collection
            """),
            {"collection": collection}
        )
        db.commit()

    print(f"Updated collection statistics")
    print()

    print("="*60)
    print("INGESTION COMPLETE!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Generate embeddings for chunks (requires OpenAI API)")
    print("  2. Store vectors in Qdrant")
    print("  3. Test queries via API")
    print()


if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    documents_file = project_root / "sample_data" / "documents_for_ingestion.json"

    if not documents_file.exists():
        print(f"ERROR: Documents file not found: {documents_file}")
        print("Please run process_reviews.py first")
        sys.exit(1)

    ingest_documents(documents_file)
