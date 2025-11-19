"""Teste simples - enviar UMA query e aguardar resultado."""
import requests
import time

API_URL = "http://localhost:8001"

print("\n" + "="*80)
print("TESTE SIMPLES - 1 QUERY")
print("="*80 + "\n")

# Enviar query
print("Enviando query...")
response = requests.post(
    f"{API_URL}/api/v1/query/async",
    json={
        "question": "Quais são os principais motivos de avaliações negativas?",
        "collection": "olist_reviews"
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

if response.status_code == 202:
    query_id = response.json()["query_id"]
    print(f"✓ Query criada: {query_id}\n")

    # Aguardar 5 segundos
    print("Aguardando processamento...")
    time.sleep(5)

    # Verificar status
    status_response = requests.get(f"{API_URL}/api/v1/query/{query_id}")
    print(f"\nStatus da query: {status_response.json()}")
else:
    print("✗ Falhou ao criar query")
