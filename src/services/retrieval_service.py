"""Retrieval Service for semantic search using Qdrant and PostgreSQL."""

from typing import List, Dict, Any
from uuid import UUID

from qdrant_client import QdrantClient
from qdrant_client.models import ScoredPoint
from sqlalchemy.orm import Session

from src.lib.config import settings
from src.lib.database import get_db_context
from src.lib.exceptions import RetrievalError
from src.lib.logger import get_logger
from src.repositories.document_repo import DocumentRepository

logger = get_logger(__name__)


class RetrievalResult:
    """Container for a single retrieval result."""

    def __init__(
        self,
        chunk_id: str,
        text_content: str,
        similarity_score: float,
        metadata: Dict[str, Any],
        rank: int,
    ):
        """
        Initialize a retrieval result.

        Args:
            chunk_id: Chunk UUID
            text_content: The chunk text
            similarity_score: Cosine similarity score (0-1)
            metadata: Chunk metadata (sentiment, category, etc.)
            rank: Result rank (1-based)
        """
        self.chunk_id = chunk_id
        self.text_content = text_content
        self.similarity_score = similarity_score
        self.metadata = metadata
        self.rank = rank

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "chunk_id": self.chunk_id,
            "text_content": self.text_content,
            "similarity_score": self.similarity_score,
            "metadata": self.metadata,
            "rank": self.rank,
        }


class RetrievalService:
    """Service for retrieving relevant chunks using semantic search."""

    def __init__(self, db: Session | None = None):
        """
        Initialize the retrieval service.

        Args:
            db: Optional database session (for testing)
        """
        self.qdrant_client = QdrantClient(
            url=settings.qdrant_url.replace(":6333", ""),
            api_key=settings.qdrant_api_key,
            timeout=settings.qdrant_timeout,
        )
        self.db = db
        logger.info("RetrievalService initialized")

    def retrieve(
        self,
        query_vector: List[float],
        collection: str = "olist_reviews",
        top_k: int = 5,
        min_score: float = 0.0,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks using semantic search.

        Args:
            query_vector: Query embedding vector
            collection: Collection name (default: olist_reviews)
            top_k: Maximum number of results to return
            min_score: Minimum similarity score threshold (0-1)

        Returns:
            List of RetrievalResult objects, sorted by similarity score (descending)

        Raises:
            RetrievalError: If retrieval fails
        """
        try:
            logger.info(
                f"Retrieving top {top_k} chunks from '{collection}' (min_score={min_score})"
            )

            # Search Qdrant
            search_results = self._search_qdrant(
                query_vector=query_vector,
                collection=collection,
                top_k=top_k,
            )

            if not search_results:
                logger.warning("No results found in Qdrant")
                return []

            # Filter by minimum score
            filtered_results = [
                r for r in search_results if r.score >= min_score
            ]

            if len(filtered_results) < len(search_results):
                logger.info(
                    f"Filtered {len(search_results) - len(filtered_results)} results below min_score={min_score}"
                )

            if not filtered_results:
                logger.warning("No results passed score threshold")
                return []

            # Fetch chunk details from PostgreSQL
            retrieval_results = self._enrich_with_chunk_data(
                filtered_results, collection
            )

            logger.info(f"Successfully retrieved {len(retrieval_results)} chunks")
            return retrieval_results

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise RetrievalError(f"Failed to retrieve chunks: {e}")

    def _search_qdrant(
        self,
        query_vector: List[float],
        collection: str,
        top_k: int,
    ) -> List[ScoredPoint]:
        """
        Search Qdrant for similar vectors.

        Args:
            query_vector: Query embedding
            collection: Collection name
            top_k: Number of results

        Returns:
            List of ScoredPoint results from Qdrant
        """
        try:
            results = self.qdrant_client.query_points(
                collection_name=collection,
                query=query_vector,
                limit=top_k,
            )

            logger.debug(f"Qdrant returned {len(results.points)} results")
            return results.points

        except Exception as e:
            logger.error(f"Qdrant search failed: {e}")
            raise RetrievalError(f"Qdrant search error: {e}")

    def _enrich_with_chunk_data(
        self,
        scored_points: List[ScoredPoint],
        collection: str,
    ) -> List[RetrievalResult]:
        """
        Enrich Qdrant results with chunk data from PostgreSQL.

        Args:
            scored_points: Results from Qdrant
            collection: Collection name

        Returns:
            List of RetrievalResult objects with full chunk data
        """
        results = []

        # Get database session
        if self.db:
            # Use provided session
            return self._fetch_chunks_from_db(self.db, scored_points)
        else:
            # Create new session with context manager
            with get_db_context() as db:
                return self._fetch_chunks_from_db(db, scored_points)

    def _fetch_chunks_from_db(
        self,
        db: Session,
        scored_points: List[ScoredPoint],
    ) -> List[RetrievalResult]:
        """
        Fetch chunks from database for scored points.

        Args:
            db: Database session
            scored_points: Results from Qdrant

        Returns:
            List of RetrievalResult objects
        """
        results = []
        doc_repo = DocumentRepository(db)

        for rank, point in enumerate(scored_points, start=1):
            chunk_id = str(point.id)

            # Fetch chunk from database
            try:
                chunk = doc_repo.get_chunk(UUID(chunk_id))

                if chunk is None:
                    logger.warning(f"Chunk {chunk_id} not found in database")
                    continue

                # Create retrieval result
                result = RetrievalResult(
                    chunk_id=chunk_id,
                    text_content=chunk.text_content,
                    similarity_score=float(point.score),
                    metadata=chunk.extra_metadata or {},
                    rank=rank,
                )

                results.append(result)

            except Exception as e:
                logger.error(f"Failed to fetch chunk {chunk_id}: {e}")
                continue

        return results

    def health_check(self) -> Dict[str, Any]:
        """
        Check if Qdrant is accessible.

        Returns:
            Health check status
        """
        try:
            collections = self.qdrant_client.get_collections()
            return {
                "status": "healthy",
                "collections": [c.name for c in collections.collections],
            }
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Singleton instance for dependency injection
_retrieval_service: RetrievalService | None = None


def get_retrieval_service(db: Session | None = None) -> RetrievalService:
    """
    Get or create the singleton RetrievalService instance.

    Args:
        db: Optional database session

    Returns:
        RetrievalService instance
    """
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService(db=db)
    return _retrieval_service
