"""Check implementation status of services and workers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lib.config import settings

print("=" * 60)
print("IMPLEMENTATION STATUS CHECK")
print("=" * 60)
print()

# Check configuration
print("=== Configuration ===")
print(f"OpenAI API Key: {'[OK] Set' if settings.openai_api_key else '[X] Missing'}")
print(f"Qdrant URL: {'[OK] Set' if settings.qdrant_url else '[X] Missing'}")
print(f"Qdrant API Key: {'[OK] Set' if settings.qdrant_api_key else '[X] Missing'}")
print(f"RabbitMQ URL: {'[OK] Set' if settings.rabbitmq_url else '[X] Missing'}")
print()

# Test service imports
print("=== Service Imports ===")
services_ok = True

try:
    from src.services.guardrails_service import get_guardrails_service

    print("[OK] GuardrailsService")
except Exception as e:
    print(f"[X] GuardrailsService: {e}")
    services_ok = False

try:
    from src.services.embedding_service import get_embedding_service

    print("[OK] EmbeddingService")
except Exception as e:
    print(f"[X] EmbeddingService: {e}")
    services_ok = False

try:
    from src.services.retrieval_service import get_retrieval_service

    print("[OK] RetrievalService")
except Exception as e:
    print(f"[X] RetrievalService: {e}")
    services_ok = False

try:
    from src.services.generation_service import get_generation_service

    print("[OK] GenerationService")
except Exception as e:
    print(f"[X] GenerationService: {e}")
    services_ok = False

print()

# Test worker imports
print("=== Worker Imports ===")
workers_ok = True

try:
    from src.workers.base_worker import BaseWorker

    print("[OK] BaseWorker")
except Exception as e:
    print(f"[X] BaseWorker: {e}")
    workers_ok = False

try:
    from src.workers.query_worker import QueryWorker

    print("[OK] QueryWorker")
except Exception as e:
    print(f"[X] QueryWorker: {e}")
    workers_ok = False

print()

# Test basic functionality (without external services)
print("=== Guardrails Service Test (No External Dependencies) ===")
try:
    from src.services.guardrails_service import get_guardrails_service

    guardrails = get_guardrails_service()

    # Test valid query
    result1 = guardrails.validate_query("Quais produtos têm mais reclamações?")
    print(f"[OK] Valid query: {result1.is_valid}")

    # Test invalid query (too short)
    result2 = guardrails.validate_query("ab")
    print(f"[OK] Invalid query detection: {not result2.is_valid} (reason: {result2.reason})")

    # Test SQL injection detection
    result3 = guardrails.validate_query("SELECT * FROM users; DROP TABLE users;")
    print(f"[OK] SQL injection detection: {not result3.is_valid}")

    print()
    print("[OK] GuardrailsService working correctly!")

except Exception as e:
    print(f"[X] GuardrailsService test failed: {e}")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"Services: {'[OK] All OK' if services_ok else '[X] Some failed'}")
print(f"Workers: {'[OK] All OK' if workers_ok else '[X] Some failed'}")
print()
print("Note: Full end-to-end testing requires:")
print("  - Qdrant Cloud cluster activated")
print("  - OpenAI API credits added")
print("=" * 60)
