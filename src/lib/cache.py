"""Redis caching operations with connection pooling."""

import hashlib
import json
from typing import Any

import redis
from redis.connection import ConnectionPool

from .config import settings
from .exceptions import ExternalServiceError
from .logger import get_logger

logger = get_logger(__name__)


class CacheClient:
    """Client for Redis caching operations."""

    def __init__(self) -> None:
        """Initialize Redis client with connection pooling."""
        self.pool: ConnectionPool | None = None
        self.client: redis.Redis | None = None
        self._setup_client()

    def _setup_client(self) -> None:
        """Establish connection to Redis with pooling."""
        try:
            # Create connection pool
            self.pool = ConnectionPool.from_url(
                settings.redis_url,
                db=settings.redis_db,
                max_connections=settings.redis_max_connections,
                decode_responses=True,  # Auto-decode bytes to strings
            )

            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)

            # Verify connection
            if self.health_check():
                logger.info(f"Connected to Redis at {settings.redis_url}")
            else:
                raise ExternalServiceError("Redis health check failed")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise ExternalServiceError(f"Redis connection failed: {e}")

    def health_check(self) -> bool:
        """
        Check if Redis is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self.client:
                return False

            # Try to ping Redis
            return self.client.ping()

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (uses default if None)

        Raises:
            ExternalServiceError: If cache operation fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Redis client not initialized")

            # Serialize value to JSON
            serialized_value = json.dumps(value)

            # Use configured TTL if not specified
            ttl_seconds = ttl if ttl is not None else settings.cache_ttl_seconds

            # Set with TTL
            self.client.setex(
                name=key,
                time=ttl_seconds,
                value=serialized_value,
            )

            logger.debug(f"Cached value for key: {key} (TTL: {ttl_seconds}s)")

        except Exception as e:
            logger.error(f"Failed to set cache for key {key}: {e}")
            raise ExternalServiceError(f"Cache set operation failed: {e}")

    def get(self, key: str) -> Any | None:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (deserialized from JSON) or None if not found

        Raises:
            ExternalServiceError: If cache operation fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Redis client not initialized")

            # Get value
            cached_value = self.client.get(key)

            if cached_value is None:
                logger.debug(f"Cache miss for key: {key}")
                return None

            # Deserialize from JSON
            logger.debug(f"Cache hit for key: {key}")
            return json.loads(cached_value)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize cached value for key {key}: {e}")
            # Delete corrupted cache entry
            self.delete(key)
            return None

        except Exception as e:
            logger.error(f"Failed to get cache for key {key}: {e}")
            raise ExternalServiceError(f"Cache get operation failed: {e}")

    def delete(self, key: str) -> None:
        """
        Delete a value from cache.

        Args:
            key: Cache key

        Raises:
            ExternalServiceError: If cache operation fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Redis client not initialized")

            deleted_count = self.client.delete(key)
            logger.debug(f"Deleted {deleted_count} cache entry for key: {key}")

        except Exception as e:
            logger.error(f"Failed to delete cache for key {key}: {e}")
            raise ExternalServiceError(f"Cache delete operation failed: {e}")

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        try:
            if not self.client:
                raise ExternalServiceError("Redis client not initialized")

            return bool(self.client.exists(key))

        except Exception as e:
            logger.error(f"Failed to check cache existence for key {key}: {e}")
            return False

    def generate_semantic_cache_key(
        self,
        query: str,
        collection_name: str,
    ) -> str:
        """
        Generate a cache key for semantic queries.

        Uses SHA256 hash of query text and collection name to create
        a deterministic cache key for identical queries.

        Args:
            query: User query text
            collection_name: Vector collection name

        Returns:
            Cache key string
        """
        # Create deterministic hash
        content = f"{collection_name}:{query.strip().lower()}"
        hash_digest = hashlib.sha256(content.encode()).hexdigest()

        return f"semantic_cache:{collection_name}:{hash_digest[:16]}"

    def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis key pattern (e.g., "semantic_cache:*")

        Returns:
            Number of keys deleted

        Raises:
            ExternalServiceError: If operation fails
        """
        try:
            if not self.client:
                raise ExternalServiceError("Redis client not initialized")

            # Find matching keys
            keys = list(self.client.scan_iter(match=pattern))

            if not keys:
                logger.debug(f"No keys found matching pattern: {pattern}")
                return 0

            # Delete in pipeline for efficiency
            pipeline = self.client.pipeline()
            for key in keys:
                pipeline.delete(key)
            pipeline.execute()

            logger.info(f"Deleted {len(keys)} keys matching pattern: {pattern}")
            return len(keys)

        except Exception as e:
            logger.error(f"Failed to clear keys with pattern {pattern}: {e}")
            raise ExternalServiceError(f"Cache clear operation failed: {e}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get Redis cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            if not self.client:
                raise ExternalServiceError("Redis client not initialized")

            info = self.client.info("stats")

            return {
                "total_keys": self.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0) /
                    max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0))
                ) * 100,
                "evicted_keys": info.get("evicted_keys", 0),
                "expired_keys": info.get("expired_keys", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}

    def close(self) -> None:
        """Close Redis connection."""
        if self.client:
            self.client.close()
        if self.pool:
            self.pool.disconnect()
        logger.info("Closed Redis connection")

    def __enter__(self) -> "CacheClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


# Global cache client instance
_cache_client: CacheClient | None = None


def get_cache_client() -> CacheClient:
    """Get global cache client instance."""
    global _cache_client
    if _cache_client is None:
        _cache_client = CacheClient()
    return _cache_client
