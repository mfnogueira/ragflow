"""CLI tool to create a Qdrant collection with specified configuration."""

import argparse
import sys
from typing import Literal

from qdrant_client.http import models

from src.lib.config import settings
from src.lib.logger import get_logger, setup_logging
from src.lib.vector_db import get_vector_db_client

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_collection(
    name: str,
    vector_size: int,
    distance: Literal["cosine", "dot", "euclid"] = "cosine",
    on_disk_payload: bool = True,
) -> None:
    """
    Create a new Qdrant collection.

    Args:
        name: Collection name
        vector_size: Vector dimensionality
        distance: Distance metric (cosine, dot, euclid)
        on_disk_payload: Store payload on disk to save RAM

    Raises:
        SystemExit: If collection creation fails
    """
    try:
        logger.info(f"Creating collection '{name}' with vector size {vector_size}")

        # Get vector DB client
        client = get_vector_db_client()

        # Map distance string to enum
        distance_map = {
            "cosine": models.Distance.COSINE,
            "dot": models.Distance.DOT,
            "euclid": models.Distance.EUCLID,
        }
        distance_metric = distance_map[distance]

        # Create collection
        client.create_collection(
            collection_name=name,
            vector_size=vector_size,
            distance=distance_metric,
            on_disk_payload=on_disk_payload,
        )

        logger.info(f"Successfully created collection '{name}'")
        print(f"SUCCESS: Collection '{name}' created successfully!")
        print(f"  Vector size: {vector_size}")
        print(f"  Distance metric: {distance}")
        print(f"  On-disk payload: {on_disk_payload}")

    except Exception as e:
        logger.error(f"Failed to create collection '{name}': {e}")
        print(f"ERROR: Failed to create collection: {e}")
        sys.exit(1)


def list_collections() -> None:
    """List all existing collections."""
    try:
        client = get_vector_db_client()

        if not client.client:
            print("ERROR: Vector client not initialized")
            sys.exit(1)

        collections = client.client.get_collections()

        if collections.collections:
            print(f"Found {len(collections.collections)} collection(s):")
            for col in collections.collections:
                print(f"  - {col.name}")
                # Get detailed info
                info = client.get_collection_info(col.name)
                print(f"    Vectors: {info['vectors_count']}")
                print(f"    Dimension: {info['vector_size']}")
                print(f"    Distance: {info['distance']}")
        else:
            print("No collections found.")

    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        print(f"ERROR: Failed to list collections: {e}")
        sys.exit(1)


def delete_collection(name: str) -> None:
    """
    Delete a collection.

    Args:
        name: Collection name to delete
    """
    try:
        logger.info(f"Deleting collection '{name}'")

        client = get_vector_db_client()
        client.delete_collection(name)

        logger.info(f"Successfully deleted collection '{name}'")
        print(f"SUCCESS: Collection '{name}' deleted successfully!")

    except Exception as e:
        logger.error(f"Failed to delete collection '{name}': {e}")
        print(f"ERROR: Failed to delete collection: {e}")
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Manage Qdrant collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a collection
  python -m src.cli.create_collection create olist_reviews --vector-size 1536

  # List all collections
  python -m src.cli.create_collection list

  # Delete a collection
  python -m src.cli.create_collection delete olist_reviews
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new collection")
    create_parser.add_argument("name", help="Collection name")
    create_parser.add_argument(
        "--vector-size",
        type=int,
        default=settings.vector_dimension,
        help=f"Vector dimensionality (default: {settings.vector_dimension})",
    )
    create_parser.add_argument(
        "--distance",
        choices=["cosine", "dot", "euclid"],
        default="cosine",
        help="Distance metric (default: cosine)",
    )
    create_parser.add_argument(
        "--no-disk-payload",
        action="store_true",
        help="Store payload in RAM instead of disk",
    )

    # List command
    subparsers.add_parser("list", help="List all collections")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a collection")
    delete_parser.add_argument("name", help="Collection name to delete")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "create":
        create_collection(
            name=args.name,
            vector_size=args.vector_size,
            distance=args.distance,
            on_disk_payload=not args.no_disk_payload,
        )
    elif args.command == "list":
        list_collections()
    elif args.command == "delete":
        delete_collection(name=args.name)


if __name__ == "__main__":
    main()
