# Próximos Passos - ragFlow

## Status Atual da Infraestrutura

### ✅ Completado (Phase 2 - Foundational)

1. **Supabase PostgreSQL** - Totalmente funcional
   - 9 tabelas criadas via Alembic migrations
   - Conexão via pooler (melhor performance)
   - Collection padrão 'olist_reviews' criada

2. **RabbitMQ CloudAMQP** - Totalmente funcional
   - Conexão AMQPS com TLS
   - Testado: declarar/deletar queues

3. **Supabase REST API** - Totalmente funcional
   - Projeto ativo e respondendo

4. **Bibliotecas Compartilhadas** - 9 arquivos criados
   - config.py, exceptions.py, logger.py
   - database.py, queue.py, vector_db.py
   - cache.py, observability.py

5. **Modelos Pydantic** - 5 arquivos criados
   - document.py, query.py, escalation.py
   - audit.py, messages.py

6. **Repositórios** - 4 arquivos criados
   - document_repo.py, query_repo.py
   - vector_repo.py, cache_repo.py

### ⏳ Pendente - Requer Ação Manual

1. **Qdrant Cloud** - Configurado mas inativo
   - ❌ Status: 404 (cluster não ativado)
   - 📍 Ação: Ativar cluster no dashboard
   - 🔗 URL: https://cloud.qdrant.io
   - 📝 Cluster ID: 740e442b-1289-489d-86da-dd4786839615

2. **OpenAI API** - Configurado mas sem créditos
   - ❌ Status: 429 (quota excedida)
   - 📍 Ação: Adicionar créditos na conta OpenAI
   - 🔗 URL: https://platform.openai.com/account/billing
   - ✅ API Key: Configurada corretamente no .env

---

## Phase 3 (MVP) - User Story 1: Query Order Review Insights

**Objetivo**: Implementar sistema RAG completo para consultas em reviews da Olist

### Tarefas a Implementar (T049-T061)

#### 1. Services Layer (T049-T052)

**T049: Embedding Service** (`src/services/embedding_service.py`)
- Gerar embeddings usando OpenAI text-embedding-3-small
- Batching para otimização
- Retry logic com backoff exponencial
- Logging de métricas (tokens, latência)

**T050: Retrieval Service** (`src/services/retrieval_service.py`)
- Busca semântica no Qdrant
- Scoring e ranking de chunks
- Reranking opcional
- Cache de resultados

**T051: Generation Service** (`src/services/generation_service.py`)
- Geração de respostas com gpt-4o-mini
- Prompt engineering com contexto
- Streaming de respostas
- Detecção de baixa confiança para escalação

**T052: Guardrails Service** (`src/services/guardrails_service.py`)
- Validação de tamanho de query
- Detecção de PII (opcional)
- Detecção de prompt injection
- Rate limiting

#### 2. Workers Layer (T053-T054)

**T053: Base Worker** (`src/workers/base_worker.py`)
- Classe abstrata para workers RabbitMQ
- Connection pooling
- Retry logic
- Error handling e dead letter queue
- Graceful shutdown

**T054: Query Worker** (`src/workers/query_worker.py`)
- Consumir mensagens da queue 'queries'
- Orquestrar: guardrails → retrieval → generation
- Publicar resposta na queue 'answers'
- Audit logging

#### 3. API Layer (T055-T059)

**T055: FastAPI App Setup** (`src/api/app.py`)
- Configurar FastAPI application
- CORS, middleware
- Lifespan events (startup/shutdown)
- Health checks

**T056: Query Endpoint** (`src/api/routes/query.py`)
- POST /api/v1/query - Consulta síncrona
- POST /api/v1/query/async - Consulta assíncrona
- GET /api/v1/query/{query_id} - Status da query
- Validação com Pydantic

**T057: Document Endpoints** (`src/api/routes/documents.py`)
- POST /api/v1/documents - Upload de documentos
- GET /api/v1/documents - Listar documentos
- GET /api/v1/documents/{doc_id} - Detalhes
- DELETE /api/v1/documents/{doc_id} - Remover

**T058: Collection Endpoints** (`src/api/routes/collections.py`)
- GET /api/v1/collections - Listar collections
- POST /api/v1/collections - Criar collection
- GET /api/v1/collections/{name}/stats - Estatísticas

**T059: Health/Metrics Endpoints** (`src/api/routes/health.py`)
- GET /health - Health check
- GET /metrics - Prometheus metrics
- GET /ready - Readiness probe

#### 4. Testing (T060-T061)

**T060: Integration Tests** (`tests/integration/`)
- Test end-to-end flow: query → retrieval → generation
- Test com Supabase real
- Test com Qdrant real (mock se não disponível)
- Test error scenarios

**T061: E2E Tests** (`tests/e2e/`)
- Test API endpoints completos
- Test workers RabbitMQ
- Test escalation flow
- Performance/load testing

---

## Ordem de Implementação Recomendada

### Fase 1: Core Services (pode iniciar agora, sem Qdrant/OpenAI)

1. ✅ **Guardrails Service** (T052) - Sem dependências externas
2. ✅ **Base Worker** (T053) - Apenas RabbitMQ (já funcional)

### Fase 2: Aguardar Qdrant + OpenAI

3. ⏳ **Embedding Service** (T049) - Requer OpenAI
4. ⏳ **Retrieval Service** (T050) - Requer Qdrant
5. ⏳ **Generation Service** (T051) - Requer OpenAI

### Fase 3: Worker Implementation

6. **Query Worker** (T054) - Integra todos os services

### Fase 4: API Layer

7. **FastAPI App Setup** (T055)
8. **Query Endpoint** (T056)
9. **Document Endpoints** (T057)
10. **Collection Endpoints** (T058)
11. **Health/Metrics Endpoints** (T059)

### Fase 5: Testing

12. **Integration Tests** (T060)
13. **E2E Tests** (T061)

---

## Checklist de Ações Imediatas

### 🔴 Urgente - Bloqueia desenvolvimento

- [ ] **Ativar Qdrant Cloud cluster**
  - Acessar: https://cloud.qdrant.io
  - Ativar cluster: 740e442b-1289-489d-86da-dd4786839615
  - Verificar: rodar `python tests/test_qdrant_connection.py`

- [ ] **Adicionar créditos OpenAI**
  - Acessar: https://platform.openai.com/account/billing
  - Adicionar créditos ($5-10 suficiente para testes)
  - Verificar: rodar `python tests/test_openai_connection.py`

### 🟡 Pode iniciar agora

- [ ] **Implementar Guardrails Service** (T052)
  - Não depende de serviços externos
  - Validações podem ser testadas localmente

- [ ] **Implementar Base Worker** (T053)
  - Apenas RabbitMQ (já funcional)
  - Pode testar conexão e retry logic

### 🟢 Após resolver bloqueios

- [ ] **Implementar services layer completo** (T049-T051)
- [ ] **Implementar Query Worker** (T054)
- [ ] **Implementar API endpoints** (T055-T059)
- [ ] **Escrever testes** (T060-T061)

---

## Comandos Úteis

```bash
# Testar todos os serviços
python tests/test_all_services.py

# Testar Qdrant (após ativar cluster)
python tests/test_qdrant_connection.py

# Testar OpenAI (após adicionar créditos)
python tests/test_openai_connection.py

# Verificar schema do banco
python tests/test_database_schema.py

# Ver status das migrations
alembic current

# Instalar dependências que faltam
pip install -r requirements.txt
```

---

## Estimativa de Tempo

- **Ações urgentes**: 15-30 min (ativar Qdrant + adicionar créditos OpenAI)
- **Services Layer (T049-T052)**: 4-6 horas
- **Workers Layer (T053-T054)**: 2-3 horas
- **API Layer (T055-T059)**: 4-6 horas
- **Testing (T060-T061)**: 3-4 horas

**Total estimado**: 13-19 horas de desenvolvimento

---

## Progresso Geral do Projeto

```
Phase 1 (Planning): ████████████████████ 100% (20/20 tasks)
Phase 2 (Foundational): ████████████████████ 100% (48/48 tasks)
Phase 3 (MVP): ░░░░░░░░░░░░░░░░░░░░ 0% (0/60 tasks)
```

**Total**: 68/128 tasks (53%)

---

## Próximo Comando a Executar

```bash
# Depois de resolver Qdrant + OpenAI, começar com:
# Implementar Guardrails Service (pode fazer agora sem bloqueios)
```
