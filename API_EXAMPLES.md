# RAG Q&A API - Exemplos de Requisições

## URL Base
```
http://localhost:8000
```

---

## 1. Health Checks

### Health Check
```bash
curl -X GET http://localhost:8000/health
```

### Readiness Check
```bash
curl -X GET http://localhost:8000/health/ready
```

### Liveness Check
```bash
curl -X GET http://localhost:8000/health/live
```

---

## 2. Query Endpoints

### Enviar uma Query (Assíncrona) - RECOMENDADO
```bash
curl -X POST http://localhost:8000/api/v1/query/async \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são os principais motivos de avaliações negativas?",
    "collection": "olist_reviews",
    "max_chunks": 10,
    "confidence_threshold": 0.7
  }'
```

**Resposta esperada (202 Accepted):**
```json
{
  "query_id": "bce31595-ac3e-4c06-8865-ae973c5826b6",
  "status": "accepted",
  "message": "Query accepted for processing. Use GET /api/v1/query/{query_id} to check status."
}
```

### Enviar Query Síncrona (Sem RabbitMQ)
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são os principais problemas relatados?"
  }'
```

**Nota:** Este endpoint NÃO publica para RabbitMQ. A query é salva no banco mas retorna status `pending` imediatamente. Use `/query/async` para processamento completo.

### Buscar Status de uma Query
```bash
curl -X GET http://localhost:8000/api/v1/query/{query_id}
```

Exemplo:
```bash
curl -X GET http://localhost:8000/api/v1/query/bce31595-ac3e-4c06-8865-ae973c5826b6
```

### Listar Queries Recentes
```bash
curl -X GET http://localhost:8000/queries
```

Com filtro por status:
```bash
curl -X GET "http://localhost:8000/queries?status=completed&limit=10"
```

### Query Síncrona (com resposta imediata - modo demo)
```bash
curl -X POST http://localhost:8000/query/sync \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Como melhorar a satisfação dos clientes?"
  }'
```

---

## 3. Collections Endpoints

### Listar Collections
```bash
curl -X GET http://localhost:8000/collections
```

### Obter Detalhes de uma Collection
```bash
curl -X GET http://localhost:8000/collections/olist_reviews
```

### Obter Estatísticas de uma Collection
```bash
curl -X GET http://localhost:8000/collections/olist_reviews/stats
```

### Criar Nova Collection
```bash
curl -X POST http://localhost:8000/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_collection",
    "description": "My custom collection",
    "vector_dimensionality": 1536,
    "distance_metric": "cosine"
  }'
```

### Deletar Collection
```bash
curl -X DELETE http://localhost:8000/collections/my_collection
```

---

## 4. Documents Endpoints

### Upload de Documento
```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@/path/to/document.txt" \
  -F "collection_name=olist_reviews" \
  -F "language_code=pt-BR"
```

### Listar Documentos
```bash
curl -X GET http://localhost:8000/documents
```

Com filtro por collection:
```bash
curl -X GET "http://localhost:8000/documents?collection=olist_reviews&limit=20"
```

### Obter Detalhes de um Documento
```bash
curl -X GET http://localhost:8000/documents/{document_id}
```

### Obter Chunks de um Documento
```bash
curl -X GET http://localhost:8000/documents/{document_id}/chunks
```

### Verificar Status de Processamento
```bash
curl -X GET http://localhost:8000/documents/{document_id}/status
```

### Deletar Documento
```bash
curl -X DELETE http://localhost:8000/documents/{document_id}
```

---

## Exemplos para Postman

### 1. Enviar Query - POST /query

**URL:** `http://localhost:8000/query`
**Method:** POST
**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "question": "Quais são os principais problemas relatados pelos clientes?",
  "collection": "olist_reviews",
  "max_chunks": 10,
  "confidence_threshold": 0.7
}
```

---

### 2. Consultar Status da Query - GET /query/{query_id}

**URL:** `http://localhost:8000/query/{{query_id}}`
**Method:** GET
**Headers:** Nenhum necessário

*(Substitua `{{query_id}}` pelo ID retornado na resposta anterior)*

---

### 3. Query Síncrona (Demo) - POST /query/sync

**URL:** `http://localhost:8000/query/sync`
**Method:** POST
**Headers:**
```
Content-Type: application/json
```

**Body (raw JSON):**
```json
{
  "question": "Quais categorias têm mais reclamações?"
}
```

---

### 4. Listar Queries - GET /queries

**URL:** `http://localhost:8000/queries?status=completed&limit=10`
**Method:** GET
**Headers:** Nenhum necessário

---

## Notas Importantes

1. **Query Assíncrona vs Síncrona:**
   - `/query` (POST): Retorna imediatamente com `query_id`. Use `/query/{query_id}` para obter resultado
   - `/query/sync` (POST): Aguarda processamento e retorna resposta completa (modo demo)

2. **Status da Query:**
   - `pending`: Query foi recebida e está na fila
   - `processing`: Worker está processando a query
   - `completed`: Resposta gerada com sucesso
   - `failed`: Erro no processamento

3. **Campos Opcionais:**
   - `collection`: Se omitido, usa `olist_reviews` (default)
   - `max_chunks`: Se omitido, usa 10 (default)
   - `confidence_threshold`: Se omitido, usa 0.7 (default)

4. **Autenticação:**
   - Atualmente a API não requer autenticação em desenvolvimento
   - Em produção, adicione header `X-API-Key` se configurado

---

## Testando o Pipeline Completo

1. **Enviar Query:**
```bash
QUERY_ID=$(curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Quais são as principais reclamações?"}' \
  | jq -r '.query_id')

echo "Query ID: $QUERY_ID"
```

2. **Aguardar e Consultar Resultado:**
```bash
# Aguardar 5 segundos
sleep 5

# Consultar resultado
curl -X GET "http://localhost:8000/query/$QUERY_ID" | jq
```

3. **Verificar Status:**
```bash
curl -X GET "http://localhost:8000/query/$QUERY_ID" | jq '.status'
```
