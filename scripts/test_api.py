"""Test script for FastAPI application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from fastapi.testclient import TestClient

from src.api.app import app

# Create test client
client = TestClient(app)


def test_root():
    """Test root endpoint."""
    print("\n" + "=" * 60)
    print("Testing Root Endpoint")
    print("=" * 60)

    response = client.get("/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    assert response.json()["service"] == "ragFlow API"
    print("[OK] Root endpoint working")


def test_health():
    """Test health check endpoint."""
    print("\n" + "=" * 60)
    print("Testing Health Check Endpoint")
    print("=" * 60)

    response = client.get("/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    print("[OK] Health endpoint working")


def test_ready():
    """Test readiness probe endpoint."""
    print("\n" + "=" * 60)
    print("Testing Readiness Probe Endpoint")
    print("=" * 60)

    response = client.get("/health/ready")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    # May fail if DB/RabbitMQ not accessible
    print(f"Database: {'[OK]' if response.json()['checks']['database'] else '[FAIL]'}")
    print(f"RabbitMQ: {'[OK]' if response.json()['checks']['rabbitmq'] else '[FAIL]'}")


def test_live():
    """Test liveness probe endpoint."""
    print("\n" + "=" * 60)
    print("Testing Liveness Probe Endpoint")
    print("=" * 60)

    response = client.get("/health/live")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    assert response.status_code == 200
    assert response.json()["alive"] is True
    print("[OK] Liveness endpoint working")


def test_metrics():
    """Test metrics endpoint."""
    print("\n" + "=" * 60)
    print("Testing Metrics Endpoint")
    print("=" * 60)

    response = client.get("/health/metrics")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Service: {data['service']}")
        print(f"Database Stats: {data.get('database', {})}")
        print("[OK] Metrics endpoint working")
    else:
        print(f"[WARNING] Metrics endpoint returned {response.status_code}")


def test_query_endpoints():
    """Test query endpoints structure."""
    print("\n" + "=" * 60)
    print("Testing Query Endpoints Structure")
    print("=" * 60)

    # Test invalid query (should fail validation)
    response = client.post(
        "/api/v1/query/async",
        json={"question": "ab"}  # Too short
    )
    print(f"Invalid query status: {response.status_code}")
    print(f"Expected: 422 (validation error)")

    # Test valid query structure (may fail if DB not available)
    response = client.post(
        "/api/v1/query/async",
        json={
            "question": "Quais produtos têm mais reclamações dos clientes?",
            "collection": "olist_reviews",
            "max_chunks": 5
        }
    )
    print(f"Valid query status: {response.status_code}")

    if response.status_code == 202:
        print(f"Response: {response.json()}")
        print("[OK] Query endpoint accepting requests")
    else:
        print(f"[WARNING] Query endpoint returned {response.status_code}")
        print(f"Response: {response.text}")


def test_openapi_docs():
    """Test OpenAPI documentation."""
    print("\n" + "=" * 60)
    print("Testing OpenAPI Documentation")
    print("=" * 60)

    response = client.get("/openapi.json")
    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        openapi = response.json()
        print(f"API Title: {openapi['info']['title']}")
        print(f"API Version: {openapi['info']['version']}")
        print(f"Available paths: {len(openapi['paths'])}")
        print("\nEndpoints:")
        for path in sorted(openapi['paths'].keys()):
            methods = list(openapi['paths'][path].keys())
            print(f"  {path}: {', '.join(methods).upper()}")
        print("[OK] OpenAPI documentation available")
    else:
        print(f"[WARNING] OpenAPI docs not available (status {response.status_code})")


def main():
    """Run all tests."""
    print("\n" * 2)
    print("*" * 60)
    print("FASTAPI APPLICATION TEST SUITE")
    print("*" * 60)

    tests = [
        test_root,
        test_health,
        test_live,
        test_ready,
        test_metrics,
        test_query_endpoints,
        test_openapi_docs,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"\n[ERROR] Test {test.__name__} failed: {e}")
            failed += 1

    print("\n" * 2)
    print("*" * 60)
    print("TEST SUMMARY")
    print("*" * 60)
    print(f"Passed: {passed}/{len(tests)}")
    print(f"Failed: {failed}/{len(tests)}")
    print()

    if failed == 0:
        print("[SUCCESS] All tests passed!")
    else:
        print(f"[WARNING] {failed} test(s) failed")

    print("\nTo start the API server:")
    print("  uvicorn src.api.app:app --reload --port 8000")
    print("\nTo view API docs:")
    print("  http://localhost:8000/docs")
    print()


if __name__ == "__main__":
    main()
