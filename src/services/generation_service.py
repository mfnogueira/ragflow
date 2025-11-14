"""Generation Service for creating answers using OpenAI LLM."""

from typing import List, Dict, Any

from openai import OpenAI, OpenAIError
from tenacity import retry, stop_after_attempt, wait_exponential

from src.lib.config import settings
from src.lib.exceptions import GenerationError
from src.lib.logger import get_logger
from src.services.retrieval_service import RetrievalResult

logger = get_logger(__name__)


class GenerationResult:
    """Container for generation result."""

    def __init__(
        self,
        answer: str,
        confidence_score: float,
        sources_used: int,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ):
        """
        Initialize generation result.

        Args:
            answer: Generated answer text
            confidence_score: Confidence score (0-1)
            sources_used: Number of source chunks used
            model: Model name used for generation
            prompt_tokens: Number of tokens in prompt
            completion_tokens: Number of tokens in completion
        """
        self.answer = answer
        self.confidence_score = confidence_score
        self.sources_used = sources_used
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "answer": self.answer,
            "confidence_score": self.confidence_score,
            "sources_used": self.sources_used,
            "model": self.model,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


class GenerationService:
    """Service for generating answers using OpenAI LLM."""

    def __init__(self):
        """Initialize the generation service."""
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.temperature = settings.llm_temperature
        self.max_tokens = settings.max_answer_length
        logger.info(
            f"GenerationService initialized (model={self.model}, temp={self.temperature})"
        )

    def _build_system_prompt(self) -> str:
        """
        Build the system prompt for the LLM.

        Returns:
            System prompt string
        """
        return """Você é um assistente especializado em análise de avaliações de clientes da Olist, um marketplace brasileiro.

Sua função é responder perguntas sobre as avaliações de produtos com base no contexto fornecido.

Diretrizes:
1. Responda APENAS com base no contexto fornecido
2. Se o contexto não contiver informações suficientes, diga "Não tenho informações suficientes para responder essa pergunta"
3. Seja conciso e objetivo
4. Use português brasileiro
5. Cite informações específicas das avaliações quando relevante
6. Se houver sentimentos mistos, apresente diferentes perspectivas
7. Nunca invente informações que não estejam no contexto"""

    def _build_user_prompt(
        self,
        question: str,
        retrieval_results: List[RetrievalResult],
    ) -> str:
        """
        Build the user prompt with question and context.

        Args:
            question: User's question
            retrieval_results: Retrieved chunks for context

        Returns:
            User prompt string
        """
        # Build context from retrieval results
        context_parts = []

        for idx, result in enumerate(retrieval_results, start=1):
            metadata = result.metadata
            context_parts.append(f"""[Avaliação {idx}]
Categoria: {metadata.get('category', 'N/A')}
Nota: {metadata.get('score', 'N/A')} estrelas
Sentimento: {metadata.get('sentiment', 'N/A')}
Título: {metadata.get('title', 'N/A')}
Conteúdo: {result.text_content}
---""")

        context = "\n\n".join(context_parts)

        return f"""Contexto (avaliações relevantes):

{context}

Pergunta: {question}

Resposta:"""

    def _calculate_confidence(
        self,
        retrieval_results: List[RetrievalResult],
        answer: str,
    ) -> float:
        """
        Calculate confidence score for the generated answer.

        Args:
            retrieval_results: Retrieved chunks used for generation
            answer: Generated answer

        Returns:
            Confidence score (0-1)
        """
        # Simple heuristic-based confidence calculation
        # Could be improved with more sophisticated methods

        if not retrieval_results:
            return 0.0

        # Factor 1: Average similarity score of sources
        avg_similarity = sum(r.similarity_score for r in retrieval_results) / len(
            retrieval_results
        )

        # Factor 2: Number of sources (more sources = higher confidence, up to a point)
        source_factor = min(len(retrieval_results) / 5.0, 1.0)

        # Factor 3: Check if answer indicates uncertainty
        uncertainty_phrases = [
            "não tenho informações",
            "não há informações",
            "contexto não contém",
            "não posso responder",
        ]
        has_uncertainty = any(phrase in answer.lower() for phrase in uncertainty_phrases)

        if has_uncertainty:
            # Low confidence if answer expresses uncertainty
            confidence = avg_similarity * 0.3
        else:
            # Combine factors
            confidence = (avg_similarity * 0.7) + (source_factor * 0.3)

        return round(confidence, 3)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def generate_answer(
        self,
        question: str,
        retrieval_results: List[RetrievalResult],
        temperature: float | None = None,
    ) -> GenerationResult:
        """
        Generate an answer to the question using retrieved context.

        Args:
            question: User's question
            retrieval_results: Retrieved chunks for context
            temperature: Optional temperature override (0-1)

        Returns:
            GenerationResult with answer and metadata

        Raises:
            GenerationError: If generation fails
        """
        if not question or not question.strip():
            raise GenerationError("Question cannot be empty")

        if not retrieval_results:
            raise GenerationError("No retrieval results provided")

        try:
            logger.info(
                f"Generating answer for question (length={len(question)}, sources={len(retrieval_results)})"
            )

            # Build prompts
            system_prompt = self._build_system_prompt()
            user_prompt = self._build_user_prompt(question, retrieval_results)

            # Generate answer
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature or self.temperature,
                max_tokens=self.max_tokens,
            )

            answer = response.choices[0].message.content.strip()

            # Calculate confidence
            confidence = self._calculate_confidence(retrieval_results, answer)

            # Extract token usage
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else 0
            completion_tokens = usage.completion_tokens if usage else 0

            logger.info(
                f"Answer generated (length={len(answer)}, confidence={confidence}, "
                f"tokens={prompt_tokens + completion_tokens})"
            )

            return GenerationResult(
                answer=answer,
                confidence_score=confidence,
                sources_used=len(retrieval_results),
                model=self.model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )

        except OpenAIError as e:
            logger.error(f"OpenAI API error during generation: {e}")
            raise GenerationError(f"Failed to generate answer: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during generation: {e}")
            raise GenerationError(f"Unexpected error: {e}")


# Singleton instance for dependency injection
_generation_service: GenerationService | None = None


def get_generation_service() -> GenerationService:
    """
    Get or create the singleton GenerationService instance.

    Returns:
        GenerationService instance
    """
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
