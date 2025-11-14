"""Embedding Service for generating text embeddings using OpenAI."""

from typing import List

from openai import OpenAI, OpenAIError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.lib.config import settings
from src.lib.exceptions import EmbeddingError
from src.lib.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating embeddings using OpenAI API."""

    def __init__(self):
        """Initialize the embedding service."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_embedding_model
        self.dimension = settings.vector_dimension
        logger.info(f"EmbeddingService initialized (model={self.model}, dim={self.dimension})")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty text")

        try:
            logger.debug(f"Generating embedding for text (length={len(text)})")

            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            embedding = response.data[0].embedding

            # Validate embedding dimension
            if len(embedding) != self.dimension:
                raise EmbeddingError(
                    f"Unexpected embedding dimension: {len(embedding)} (expected {self.dimension})"
                )

            logger.debug(f"Successfully generated embedding (dim={len(embedding)})")
            return embedding

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise EmbeddingError(f"Failed to generate embedding: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise EmbeddingError(f"Unexpected error: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single API call.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            raise EmbeddingError("Cannot generate embeddings for empty list")

        # Filter out empty texts
        valid_texts = [t for t in texts if t and t.strip()]
        if not valid_texts:
            raise EmbeddingError("All texts are empty after filtering")

        if len(valid_texts) != len(texts):
            logger.warning(
                f"Filtered {len(texts) - len(valid_texts)} empty texts from batch"
            )

        try:
            logger.debug(f"Generating embeddings for {len(valid_texts)} texts")

            response = self.client.embeddings.create(
                model=self.model,
                input=valid_texts,
            )

            embeddings = [item.embedding for item in response.data]

            # Validate count
            if len(embeddings) != len(valid_texts):
                raise EmbeddingError(
                    f"Mismatch in embedding count: got {len(embeddings)}, expected {len(valid_texts)}"
                )

            # Validate dimensions
            for idx, embedding in enumerate(embeddings):
                if len(embedding) != self.dimension:
                    raise EmbeddingError(
                        f"Unexpected embedding dimension at index {idx}: {len(embedding)} (expected {self.dimension})"
                    )

            logger.debug(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings

        except OpenAIError as e:
            logger.error(f"OpenAI API error in batch: {e}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {e}")
        except Exception as e:
            logger.error(f"Unexpected error generating batch embeddings: {e}")
            raise EmbeddingError(f"Unexpected error: {e}")

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.

        Returns:
            Embedding dimension (e.g., 1536 for text-embedding-3-small)
        """
        return self.dimension

    def get_model_name(self) -> str:
        """
        Get the name of the embedding model.

        Returns:
            Model name (e.g., "text-embedding-3-small")
        """
        return self.model


# Singleton instance for dependency injection
_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """
    Get or create the singleton EmbeddingService instance.

    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
