"""Repository for vector database operations with Qdrant."""

from typing import Any
from uuid import UUID

from qdrant_client.http import models

from src.lib.exceptions import RetrievalError
from src.lib.logger import get_logger
from src.lib.vector_db import VectorDBClient

logger = get_logger(__name__)


class VectorRepository:
    """Repository for Qdrant vector operations."""

    def __init__(self, vector_client: VectorDBClient) -> None:
        """
        Initialize repository with vector database client.

        Args:
            vector_client: Qdrant client instance
        """
        self.client = vector_client

    def upsert_vector(
        self,
        collection_name: str,
        point_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """
        Insert or update a single vector.

        Args:
            collection_name: Collection name
            point_id: Unique point identifier (typically chunk UUID)
            vector: Vector embedding
            payload: Metadata payload

        Raises:
            RetrievalError: If operation fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            self.client.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                ],
            )

            logger.debug(f"Upserted vector {point_id} to collection {collection_name}")

        except Exception as e:
            logger.error(f"Failed to upsert vector {point_id}: {e}")
            raise RetrievalError(f"Vector upsert failed: {e}")

    def upsert_vectors_bulk(
        self,
        collection_name: str,
        points: list[dict[str, Any]],
    ) -> None:
        """
        Insert or update multiple vectors in bulk.

        Args:
            collection_name: Collection name
            points: List of point dictionaries with 'id', 'vector', 'payload'

        Raises:
            RetrievalError: If operation fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            point_structs = [
                models.PointStruct(
                    id=point["id"],
                    vector=point["vector"],
                    payload=point["payload"],
                )
                for point in points
            ]

            self.client.client.upsert(
                collection_name=collection_name,
                points=point_structs,
            )

            logger.info(
                f"Upserted {len(points)} vectors to collection {collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to upsert vectors in bulk: {e}")
            raise RetrievalError(f"Bulk vector upsert failed: {e}")

    def search_vectors(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            collection_name: Collection name
            query_vector: Query embedding vector
            limit: Maximum results
            score_threshold: Minimum similarity score (0-1)
            metadata_filter: Optional metadata filters

        Returns:
            List of search results with 'id', 'score', 'payload'

        Raises:
            RetrievalError: If search fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            # Build filter if provided
            query_filter = None
            if metadata_filter:
                query_filter = self._build_filter(metadata_filter)

            # Perform search
            results = self.client.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=query_filter,
            )

            # Format results
            formatted_results = [
                {
                    "id": str(hit.id),
                    "score": hit.score,
                    "payload": hit.payload or {},
                }
                for hit in results
            ]

            logger.info(
                f"Found {len(formatted_results)} vectors in collection {collection_name}"
            )

            return formatted_results

        except Exception as e:
            logger.error(f"Failed to search vectors: {e}")
            raise RetrievalError(f"Vector search failed: {e}")

    def get_vector(
        self,
        collection_name: str,
        point_id: str,
    ) -> dict[str, Any] | None:
        """
        Get a vector by ID.

        Args:
            collection_name: Collection name
            point_id: Point identifier

        Returns:
            Vector data with 'id', 'vector', 'payload' or None if not found

        Raises:
            RetrievalError: If operation fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            result = self.client.client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
            )

            if not result:
                return None

            point = result[0]
            return {
                "id": str(point.id),
                "vector": point.vector,
                "payload": point.payload or {},
            }

        except Exception as e:
            logger.error(f"Failed to get vector {point_id}: {e}")
            raise RetrievalError(f"Vector retrieval failed: {e}")

    def delete_vector(
        self,
        collection_name: str,
        point_id: str,
    ) -> None:
        """
        Delete a vector by ID.

        Args:
            collection_name: Collection name
            point_id: Point identifier

        Raises:
            RetrievalError: If deletion fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            self.client.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(
                    points=[point_id],
                ),
            )

            logger.debug(f"Deleted vector {point_id} from collection {collection_name}")

        except Exception as e:
            logger.error(f"Failed to delete vector {point_id}: {e}")
            raise RetrievalError(f"Vector deletion failed: {e}")

    def delete_vectors_by_filter(
        self,
        collection_name: str,
        metadata_filter: dict[str, Any],
    ) -> None:
        """
        Delete vectors matching a filter.

        Args:
            collection_name: Collection name
            metadata_filter: Metadata filter criteria

        Raises:
            RetrievalError: If deletion fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            query_filter = self._build_filter(metadata_filter)

            self.client.client.delete(
                collection_name=collection_name,
                points_selector=models.FilterSelector(
                    filter=query_filter,
                ),
            )

            logger.info(
                f"Deleted vectors matching filter from collection {collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to delete vectors by filter: {e}")
            raise RetrievalError(f"Vector deletion failed: {e}")

    def delete_vectors_by_document(
        self,
        collection_name: str,
        document_id: UUID,
    ) -> None:
        """
        Delete all vectors for a document.

        Args:
            collection_name: Collection name
            document_id: Document UUID

        Raises:
            RetrievalError: If deletion fails
        """
        try:
            metadata_filter = {"document_id": str(document_id)}
            self.delete_vectors_by_filter(collection_name, metadata_filter)

            logger.info(
                f"Deleted vectors for document {document_id} from collection {collection_name}"
            )

        except Exception as e:
            logger.error(f"Failed to delete vectors for document {document_id}: {e}")
            raise RetrievalError(f"Vector deletion failed: {e}")

    def count_vectors(self, collection_name: str) -> int:
        """
        Count total vectors in a collection.

        Args:
            collection_name: Collection name

        Returns:
            Vector count

        Raises:
            RetrievalError: If operation fails
        """
        try:
            info = self.client.get_collection_info(collection_name)
            return info.get("vectors_count", 0)

        except Exception as e:
            logger.error(f"Failed to count vectors in collection {collection_name}: {e}")
            raise RetrievalError(f"Vector count failed: {e}")

    def scroll_vectors(
        self,
        collection_name: str,
        limit: int = 100,
        offset: str | None = None,
        metadata_filter: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, Any]], str | None]:
        """
        Scroll through vectors in a collection.

        Args:
            collection_name: Collection name
            limit: Maximum results per page
            offset: Pagination offset (point ID)
            metadata_filter: Optional metadata filters

        Returns:
            Tuple of (results, next_offset)

        Raises:
            RetrievalError: If operation fails
        """
        try:
            if not self.client.client:
                raise RetrievalError("Vector client not initialized")

            # Build filter if provided
            query_filter = None
            if metadata_filter:
                query_filter = self._build_filter(metadata_filter)

            # Perform scroll
            results, next_offset = self.client.client.scroll(
                collection_name=collection_name,
                limit=limit,
                offset=offset,
                scroll_filter=query_filter,
            )

            # Format results
            formatted_results = [
                {
                    "id": str(point.id),
                    "vector": point.vector,
                    "payload": point.payload or {},
                }
                for point in results
            ]

            return formatted_results, next_offset

        except Exception as e:
            logger.error(f"Failed to scroll vectors: {e}")
            raise RetrievalError(f"Vector scroll failed: {e}")

    def _build_filter(self, metadata_filter: dict[str, Any]) -> models.Filter:
        """
        Build Qdrant filter from metadata dictionary.

        Args:
            metadata_filter: Dictionary of field: value pairs

        Returns:
            Qdrant Filter object
        """
        must_conditions = []

        for field, value in metadata_filter.items():
            if isinstance(value, (str, int, float, bool)):
                must_conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchValue(value=value),
                    )
                )
            elif isinstance(value, list):
                must_conditions.append(
                    models.FieldCondition(
                        key=field,
                        match=models.MatchAny(any=value),
                    )
                )

        return models.Filter(must=must_conditions)
