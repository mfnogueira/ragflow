"""Test new worker with corrected ORM."""
import requests
import time

API_URL = "http://localhost:8000"

print("\n" + "="*80)
print("TESTE - Worker Novo com ORM Corrigido")
print("="*80 + "\n")

# Enviar query
print("Enviando query...")
response = requests.post(
    f"{API_URL}/api/v1/query/async",
    json={
        "question": "Teste: Quais produtos têm melhor avaliação?",
        "collection": "olist_reviews"
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

if response.status_code == 202:
    query_id = response.json()["query_id"]
    print(f"✓ Query criada: {query_id}\n")

    # Aguardar 10 segundos
    print("Aguardando processamento (10s)...")
    time.sleep(10)

    # Verificar status
    status_response = requests.get(f"{API_URL}/api/v1/query/{query_id}")
    print(f"\nStatus da query: {status_response.json()}\n")

    result = status_response.json()
    if result.get("status") == "completed":
        print("✅ SUCESSO! Query processada e salva com sucesso!")
        print(f"Resposta: {result.get('answer', 'N/A')[:100]}...")
    elif result.get("status") == "failed":
        print("❌ FALHOU! Query processada mas falhou ao salvar")
    else:
        print(f"⏳ Status: {result.get('status')}")
else:
    print("✗ Falhou ao criar query")
