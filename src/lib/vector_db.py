"""Qdrant vector database client initialization and operations."""

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse

from .config import settings
from .exceptions import ExternalServiceError
from .logger import get_logger

logger = get_logger(__name__)


class VectorDBClient:
    """Client for Qdrant vector database operations."""

    def __init__(self) -> None:
        """Initialize Qdrant client."""
        self.client: QdrantClient | None = None
        self._setup_client()

    def _setup_client(self) -> None:
        """Establish connection to Qdrant."""
        try:
            self.client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key if settings.qdrant_api_key else None,
                timeout=settings.qdrant_timeout,
            )

            # Verify connection
            if self.health_check():
                logger.info(f"Connected to Qdrant at {settings.qdrant_url}")
            else:
                raise ExternalServiceError("Qdrant health check failed")

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise ExternalServiceError(f"Qdrant connection failed: {e}")

    def health_check(self) -> bool:
        """
        Check if Qdrant is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.client:
                return False

            # Try to get collections list as health check
            self.client.get_collections()
            return True

        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection

        Returns:
            True if collection exists, False otherwise
        """
        try:
            if not self.client:
                raise ExternalServiceError("Qdrant client not initialized")

            collections = self.client.get_collections()
            return any(
                col.name == collection_name
                for col in collections.collections
            )

        except Exception as e:
            logger.error(f"Failed to check collection existence: {e}")
            return False

    def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: models.Distance = models.Distance.COSINE,
        on_disk_payload: bool = True,
    ) -> None:
        """
        Create a new collection.

        Args:
            collection_name: Name of the collection
            vector_size: Dimensionality of vectors
            distance: Distance metric (COSINE, DOT, EUCLID)
            on_disk_payload: Store payload on disk (saves RAM)

        Raises:
            ExternalServiceError: If collection creation fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Qdrant client not initialized")

            if self.collection_exists(collection_name):
                logger.info(f"Collection {collection_name} already exists")
                return

            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=distance,
                    on_disk=False,  # Keep vectors in RAM for speed
                ),
                optimizers_config=models.OptimizersConfigDiff(
                    indexing_threshold=10000,  # Start indexing after this many vectors
                ),
                on_disk_payload=on_disk_payload,
            )

            logger.info(
                f"Created collection {collection_name} with vector size {vector_size} "
                f"and distance metric {distance}"
            )

        except UnexpectedResponse as e:
            logger.error(f"Failed to create collection {collection_name}: {e}")
            raise ExternalServiceError(f"Collection creation failed: {e}")

    def delete_collection(self, collection_name: str) -> None:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Raises:
            ExternalServiceError: If collection deletion fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Qdrant client not initialized")

            if not self.collection_exists(collection_name):
                logger.warning(f"Collection {collection_name} does not exist")
                return

            self.client.delete_collection(collection_name=collection_name)
            logger.info(f"Deleted collection {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete collection {collection_name}: {e}")
            raise ExternalServiceError(f"Collection deletion failed: {e}")

    def get_collection_info(self, collection_name: str) -> dict[str, Any]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information

        Raises:
            ExternalServiceError: If operation fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Qdrant client not initialized")

            info = self.client.get_collection(collection_name=collection_name)

            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance,
            }

        except Exception as e:
            logger.error(f"Failed to get collection info for {collection_name}: {e}")
            raise ExternalServiceError(f"Failed to get collection info: {e}")

    def close(self) -> None:
        """Close Qdrant client connection."""
        if self.client:
            self.client.close()
            logger.info("Closed Qdrant connection")

    def __enter__(self) -> "VectorDBClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


# Global vector database client instance
_vector_db_client: VectorDBClient | None = None


def get_vector_db_client() -> VectorDBClient:
    """Get global vector database client instance."""
    global _vector_db_client
    if _vector_db_client is None:
        _vector_db_client = VectorDBClient()
    return _vector_db_client
