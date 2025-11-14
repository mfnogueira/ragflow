"""Test script to verify Qdrant Cloud connection."""

from qdrant_client import QdrantClient

# Qdrant Cloud credentials
# Testing with and without port
url_with_port = "https://740e442b-1289-489d-86da-dd4786839615.us-west-2-0.aws.cloud.qdrant.io:6333"
url_without_port = "https://740e442b-1289-489d-86da-dd4786839615.us-west-2-0.aws.cloud.qdrant.io"

print(f"Trying URL without port: {url_without_port}")
qdrant_client = QdrantClient(
    url=url_without_port,
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.GzaoBx61S0KgEmQKqSfb8fvY8g3Yhry_FH5U7Mpzy2Q",
    timeout=30,
)

try:
    print("Testing Qdrant Cloud connection...")
    collections = qdrant_client.get_collections()
    print("SUCCESS: Connection successful!")
    print(f"Collections: {collections}")

    if collections.collections:
        print(f"\nFound {len(collections.collections)} collection(s):")
        for col in collections.collections:
            print(f"  - {col.name}")
    else:
        print("\nNo collections found yet.")

except Exception as e:
    print(f"ERROR: Connection failed: {e}")
