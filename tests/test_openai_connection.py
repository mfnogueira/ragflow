"""Test OpenAI API connectivity and configuration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import OpenAI

# OpenAI configuration from .env
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
llm_model = os.getenv("OPENAI_LLM_MODEL", "gpt-4o-mini")
embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

try:
    print("Testing OpenAI API connectivity...")
    print(f"LLM Model: {llm_model}")
    print(f"Embedding Model: {embedding_model}")
    print()

    # Initialize client
    client = OpenAI(api_key=api_key)

    # Test 1: Embedding API
    print("1. Testing Embedding API...")
    response = client.embeddings.create(
        model=embedding_model,
        input="Test embedding for ragFlow system",
    )

    embedding = response.data[0].embedding
    print(f"   [OK] Embedding created successfully")
    print(f"   [OK] Vector dimension: {len(embedding)}")
    print(f"   [OK] Model: {response.model}")
    print()

    # Test 2: LLM API
    print("2. Testing LLM API...")
    response = client.chat.completions.create(
        model=llm_model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'API test successful' in one sentence."}
        ],
        max_tokens=50,
    )

    answer = response.choices[0].message.content
    print(f"   [OK] LLM response received")
    print(f"   [OK] Model: {response.model}")
    print(f"   [OK] Response: {answer}")
    print()

    print("="*60)
    print("SUCCESS: OpenAI API is fully functional!")
    print("="*60)
    print()
    print("Configuration:")
    print(f"  - LLM Model: {llm_model}")
    print(f"  - Embedding Model: {embedding_model}")
    print(f"  - Embedding Dimension: {len(embedding)} (matches VECTOR_DIMENSION in .env)")

except Exception as e:
    print(f"ERROR: OpenAI API test failed: {e}")
    print()
    print("Possible issues:")
    print("  - Check if API key is valid")
    print("  - Verify you have credits in your OpenAI account")
    print("  - Check internet connectivity")
    print("  - Ensure models are available in your account")
