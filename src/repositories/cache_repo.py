"""Repository for caching operations with semantic cache support."""

from typing import Any

from src.lib.cache import CacheClient
from src.lib.logger import get_logger
from src.models.query import Answer, AnswerResponse

logger = get_logger(__name__)


class CacheRepository:
    """Repository for cache operations with semantic cache key generation."""

    def __init__(self, cache_client: CacheClient) -> None:
        """
        Initialize repository with cache client.

        Args:
            cache_client: Redis cache client instance
        """
        self.client = cache_client

    def cache_query_answer(
        self,
        query_text: str,
        collection_name: str,
        answer: AnswerResponse,
        ttl: int | None = None,
    ) -> None:
        """
        Cache a query answer with semantic key.

        Args:
            query_text: User query text
            collection_name: Collection name
            answer: Answer to cache
            ttl: Time to live in seconds (uses default if None)
        """
        try:
            # Generate semantic cache key
            cache_key = self.client.generate_semantic_cache_key(
                query=query_text,
                collection_name=collection_name,
            )

            # Cache the answer
            self.client.set(
                key=cache_key,
                value=answer.model_dump(),
                ttl=ttl,
            )

            logger.debug(f"Cached answer for query (key: {cache_key[:16]}...)")

        except Exception as e:
            # Don't fail if caching fails, just log
            logger.warning(f"Failed to cache query answer: {e}")

    def get_cached_answer(
        self,
        query_text: str,
        collection_name: str,
    ) -> AnswerResponse | None:
        """
        Get cached answer for a query.

        Args:
            query_text: User query text
            collection_name: Collection name

        Returns:
            Cached answer or None if not found/expired
        """
        try:
            # Generate semantic cache key
            cache_key = self.client.generate_semantic_cache_key(
                query=query_text,
                collection_name=collection_name,
            )

            # Get from cache
            cached_data = self.client.get(cache_key)

            if cached_data:
                logger.debug(f"Cache hit for query (key: {cache_key[:16]}...)")
                return AnswerResponse(**cached_data)

            logger.debug(f"Cache miss for query (key: {cache_key[:16]}...)")
            return None

        except Exception as e:
            # Don't fail if cache retrieval fails, just log
            logger.warning(f"Failed to get cached answer: {e}")
            return None

    def cache_embeddings(
        self,
        text: str,
        embedding: list[float],
        model: str,
        ttl: int | None = None,
    ) -> None:
        """
        Cache embeddings for text.

        Args:
            text: Text content
            embedding: Embedding vector
            model: Embedding model name
            ttl: Time to live in seconds
        """
        try:
            import hashlib

            # Generate cache key from text hash
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            cache_key = f"embedding:{model}:{text_hash}"

            # Cache the embedding
            self.client.set(
                key=cache_key,
                value={"text": text, "embedding": embedding, "model": model},
                ttl=ttl,
            )

            logger.debug(f"Cached embedding for text (key: {cache_key})")

        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")

    def get_cached_embedding(
        self,
        text: str,
        model: str,
    ) -> list[float] | None:
        """
        Get cached embedding for text.

        Args:
            text: Text content
            model: Embedding model name

        Returns:
            Cached embedding or None if not found
        """
        try:
            import hashlib

            # Generate cache key
            text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
            cache_key = f"embedding:{model}:{text_hash}"

            # Get from cache
            cached_data = self.client.get(cache_key)

            if cached_data:
                logger.debug(f"Embedding cache hit (key: {cache_key})")
                return cached_data.get("embedding")

            return None

        except Exception as e:
            logger.warning(f"Failed to get cached embedding: {e}")
            return None

    def cache_retrieval_results(
        self,
        query_embedding: list[float],
        collection_name: str,
        chunk_ids: list[str],
        ttl: int | None = None,
    ) -> None:
        """
        Cache retrieval results (chunk IDs) for a query embedding.

        Args:
            query_embedding: Query embedding vector
            collection_name: Collection name
            chunk_ids: List of retrieved chunk IDs
            ttl: Time to live in seconds
        """
        try:
            import hashlib
            import json

            # Generate cache key from embedding hash
            embedding_str = json.dumps(query_embedding[:10])  # Use first 10 dims
            embedding_hash = hashlib.sha256(embedding_str.encode()).hexdigest()[:16]
            cache_key = f"retrieval:{collection_name}:{embedding_hash}"

            # Cache the results
            self.client.set(
                key=cache_key,
                value={"chunk_ids": chunk_ids},
                ttl=ttl,
            )

            logger.debug(f"Cached retrieval results (key: {cache_key})")

        except Exception as e:
            logger.warning(f"Failed to cache retrieval results: {e}")

    def get_cached_retrieval_results(
        self,
        query_embedding: list[float],
        collection_name: str,
    ) -> list[str] | None:
        """
        Get cached retrieval results for a query embedding.

        Args:
            query_embedding: Query embedding vector
            collection_name: Collection name

        Returns:
            List of cached chunk IDs or None if not found
        """
        try:
            import hashlib
            import json

            # Generate cache key
            embedding_str = json.dumps(query_embedding[:10])
            embedding_hash = hashlib.sha256(embedding_str.encode()).hexdigest()[:16]
            cache_key = f"retrieval:{collection_name}:{embedding_hash}"

            # Get from cache
            cached_data = self.client.get(cache_key)

            if cached_data:
                logger.debug(f"Retrieval cache hit (key: {cache_key})")
                return cached_data.get("chunk_ids")

            return None

        except Exception as e:
            logger.warning(f"Failed to get cached retrieval results: {e}")
            return None

    def invalidate_query_cache(
        self,
        collection_name: str | None = None,
    ) -> int:
        """
        Invalidate query answer cache.

        Args:
            collection_name: Optional collection name to filter

        Returns:
            Number of keys deleted
        """
        try:
            if collection_name:
                pattern = f"semantic_cache:{collection_name}:*"
            else:
                pattern = "semantic_cache:*"

            count = self.client.clear_pattern(pattern)
            logger.info(f"Invalidated {count} cached query answers")
            return count

        except Exception as e:
            logger.warning(f"Failed to invalidate query cache: {e}")
            return 0

    def invalidate_embedding_cache(self, model: str | None = None) -> int:
        """
        Invalidate embedding cache.

        Args:
            model: Optional model name to filter

        Returns:
            Number of keys deleted
        """
        try:
            if model:
                pattern = f"embedding:{model}:*"
            else:
                pattern = "embedding:*"

            count = self.client.clear_pattern(pattern)
            logger.info(f"Invalidated {count} cached embeddings")
            return count

        except Exception as e:
            logger.warning(f"Failed to invalidate embedding cache: {e}")
            return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            return self.client.get_stats()

        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {}

    def warm_cache(
        self,
        queries: list[tuple[str, str, AnswerResponse]],
    ) -> int:
        """
        Warm cache with pre-computed query answers.

        Args:
            queries: List of (query_text, collection_name, answer) tuples

        Returns:
            Number of items cached
        """
        try:
            count = 0
            for query_text, collection_name, answer in queries:
                self.cache_query_answer(query_text, collection_name, answer)
                count += 1

            logger.info(f"Warmed cache with {count} query answers")
            return count

        except Exception as e:
            logger.warning(f"Failed to warm cache: {e}")
            return 0
