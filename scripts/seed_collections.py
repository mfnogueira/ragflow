"""
Script to seed default Qdrant collections for the RAG system.

Creates the following collections:
- olist_reviews: Olist order reviews from Kaggle dataset
- product_docs: Product documentation
- support_articles: Support knowledge base articles
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client.http import models

from src.lib.config import settings
from src.lib.logger import get_logger, setup_logging
from src.lib.vector_db import get_vector_db_client

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Default collections configuration
DEFAULT_COLLECTIONS = [
    {
        "name": "olist_reviews",
        "description": "Olist order reviews from Kaggle dataset",
        "vector_size": 1536,  # OpenAI text-embedding-3-small
        "distance": models.Distance.COSINE,
    },
    {
        "name": "product_docs",
        "description": "Product documentation and technical specs",
        "vector_size": 1536,
        "distance": models.Distance.COSINE,
    },
    {
        "name": "support_articles",
        "description": "Support knowledge base articles and FAQs",
        "vector_size": 1536,
        "distance": models.Distance.COSINE,
    },
]


def seed_collections(force: bool = False) -> None:
    """
    Create default collections in Qdrant.

    Args:
        force: If True, delete existing collections before creating
    """
    try:
        logger.info("Starting collection seeding...")
        client = get_vector_db_client()

        created_count = 0
        skipped_count = 0
        error_count = 0

        for collection_config in DEFAULT_COLLECTIONS:
            collection_name = collection_config["name"]
            logger.info(f"Processing collection: {collection_name}")

            try:
                # Check if collection already exists
                exists = client.collection_exists(collection_name)

                if exists:
                    if force:
                        logger.info(f"Deleting existing collection: {collection_name}")
                        client.delete_collection(collection_name)
                        print(f"  Deleted existing: {collection_name}")
                    else:
                        logger.info(f"Skipping existing collection: {collection_name}")
                        print(f"  Skipped (already exists): {collection_name}")
                        skipped_count += 1
                        continue

                # Create collection
                client.create_collection(
                    collection_name=collection_name,
                    vector_size=collection_config["vector_size"],
                    distance=collection_config["distance"],
                    on_disk_payload=True,
                )

                logger.info(f"Created collection: {collection_name}")
                print(f"  Created: {collection_name}")
                print(f"    Description: {collection_config['description']}")
                print(f"    Vector size: {collection_config['vector_size']}")
                print(f"    Distance: {collection_config['distance'].value}")

                created_count += 1

            except Exception as e:
                logger.error(f"Failed to create collection {collection_name}: {e}")
                print(f"  ERROR: Failed to create {collection_name}: {e}")
                error_count += 1

        # Summary
        print(f"\nSummary:")
        print(f"  Created: {created_count}")
        print(f"  Skipped: {skipped_count}")
        print(f"  Errors: {error_count}")

        if error_count > 0:
            sys.exit(1)
        else:
            logger.info("Collection seeding completed successfully")
            print("\nSUCCESS: All collections seeded successfully!")

    except Exception as e:
        logger.error(f"Collection seeding failed: {e}")
        print(f"\nERROR: Collection seeding failed: {e}")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Seed default Qdrant collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This script creates the following collections:
  - olist_reviews: Olist order reviews from Kaggle dataset
  - product_docs: Product documentation
  - support_articles: Support knowledge base articles

Examples:
  # Create collections (skip existing)
  python scripts/seed_collections.py

  # Force recreate all collections
  python scripts/seed_collections.py --force
        """,
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing collections before creating",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("Qdrant Collections Seeding")
    print("=" * 60)
    print()

    if args.force:
        print("WARNING: Force mode enabled - existing collections will be deleted!")
        print()

    seed_collections(force=args.force)


if __name__ == "__main__":
    main()
