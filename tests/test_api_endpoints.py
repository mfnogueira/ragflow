"""Test API endpoints."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


def test_root():
    """Test root endpoint."""
    print("Testing root endpoint...")
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ragFlow API"
    print("  [OK] Root endpoint")


def test_health():
    """Test health endpoint."""
    print("\nTesting health endpoints...")

    # Basic health
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("  [OK] Health check")

    # Liveness
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True
    print("  [OK] Liveness probe")

    # Readiness
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    print(f"  [OK] Readiness probe - Ready: {data['ready']}")

    # Metrics
    response = client.get("/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "database" in data
    print("  [OK] Metrics endpoint")


def test_collections():
    """Test collections endpoints."""
    print("\nTesting collection endpoints...")

    # List collections
    response = client.get("/api/v1/collections")
    assert response.status_code == 200
    collections = response.json()
    print(f"  [OK] List collections - Found {len(collections)} collection(s)")

    if collections:
        collection_name = collections[0]["name"]

        # Get collection details
        response = client.get(f"/api/v1/collections/{collection_name}")
        assert response.status_code == 200
        data = response.json()
        print(f"  [OK] Get collection - {collection_name}")

        # Get collection stats
        response = client.get(f"/api/v1/collections/{collection_name}/stats")
        assert response.status_code == 200
        data = response.json()
        print(f"  [OK] Get collection stats - {data['document_count']} documents")


def test_documents():
    """Test document endpoints."""
    print("\nTesting document endpoints...")

    # List documents
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    documents = response.json()
    print(f"  [OK] List documents - Found {len(documents)} document(s)")

    # Create document
    response = client.post(
        "/api/v1/documents",
        json={
            "content": "This is a test document for API testing.",
            "source": "api_test",
            "collection": "olist_reviews",
            "metadata": {"test": True},
        },
    )
    assert response.status_code == 201
    doc_data = response.json()
    doc_id = doc_data["document_id"]
    print(f"  [OK] Create document - ID: {doc_id[:8]}...")

    # Get document details
    response = client.get(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    print(f"  [OK] Get document - {data['chunk_count']} chunks")

    # Get document chunks
    response = client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert response.status_code == 200
    chunks = response.json()
    print(f"  [OK] Get document chunks - {len(chunks)} chunk(s)")

    # Get embedding status
    response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert response.status_code == 200
    data = response.json()
    print(f"  [OK] Get embedding status - {data['progress_percentage']:.1f}% complete")

    # Delete document
    response = client.delete(f"/api/v1/documents/{doc_id}")
    assert response.status_code == 204
    print(f"  [OK] Delete document")


def test_queries():
    """Test query endpoints."""
    print("\nTesting query endpoints...")

    # List queries
    response = client.get("/api/v1/queries")
    assert response.status_code == 200
    queries = response.json()
    print(f"  [OK] List queries - Found {len(queries)} query(ies)")

    # Create synchronous query
    response = client.post(
        "/api/v1/query",
        json={
            "question": "What are customers saying about delivery?",
            "collection": "olist_reviews",
        },
    )
    assert response.status_code == 200
    query_data = response.json()
    query_id = query_data["query_id"]
    print(f"  [OK] Create sync query - ID: {query_id[:8]}...")

    # Get query status
    response = client.get(f"/api/v1/query/{query_id}")
    assert response.status_code == 200
    data = response.json()
    print(f"  [OK] Get query status - Status: {data['status']}")

    # Create async query
    response = client.post(
        "/api/v1/query/async",
        json={
            "question": "How do customers rate product quality?",
            "collection": "olist_reviews",
        },
    )
    assert response.status_code == 202
    data = response.json()
    print(f"  [OK] Create async query - Status: {data['status']}")


if __name__ == "__main__":
    print("="*60)
    print("API ENDPOINTS TEST")
    print("="*60)

    try:
        test_root()
        test_health()
        test_collections()
        test_documents()
        test_queries()

        print("\n" + "="*60)
        print("SUCCESS: All API endpoint tests passed!")
        print("="*60)

    except AssertionError as e:
        print(f"\n[ERROR] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
