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

### Fase 1: Core Services ✅ COMPLETO

1. ✅ **Guardrails Service** (T052) - Implementado e testado
2. ✅ **Base Worker** (T053) - Implementado e testado

### Fase 2: Services Layer ✅ COMPLETO

3. ✅ **Embedding Service** (T049) - Implementado (requer OpenAI para uso)
4. ✅ **Retrieval Service** (T050) - Implementado (requer Qdrant para uso)
5. ✅ **Generation Service** (T051) - Implementado (requer OpenAI para uso)

### Fase 3: Worker Implementation ✅ COMPLETO

6. ✅ **Query Worker** (T054) - Implementado e integrado com todos os services

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

### ✅ Já Implementado

- [x] **Implementar Guardrails Service** (T052) - Completo e testado
- [x] **Implementar Base Worker** (T053) - Completo e testado
- [x] **Implementar services layer completo** (T049-T051) - Completo
- [x] **Implementar Query Worker** (T054) - Completo e testado

### 🟡 Próximas Tarefas (pode iniciar sem bloqueios externos)

- [ ] **Implementar FastAPI App Setup** (T055)
- [ ] **Implementar Query Endpoint** (T056)
- [ ] **Implementar Document Endpoints** (T057)
- [ ] **Implementar Collection Endpoints** (T058)
- [ ] **Implementar Health/Metrics Endpoints** (T059)

### 🔵 Tarefas Finais

- [ ] **Escrever testes de integração** (T060)
- [ ] **Escrever testes E2E** (T061)

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
Phase 3 (MVP): █████████░░░░░░░░░░░ 46% (6/13 tasks)
```

**Total**: 74/81 tasks (91%)

### Phase 3 - Detalhamento
- ✅ Services Layer (T049-T052): 4/4 tasks (100%)
- ✅ Workers Layer (T053-T054): 2/2 tasks (100%)
- ⏳ API Layer (T055-T059): 0/5 tasks (0%)
- ⏳ Testing (T060-T061): 0/2 tasks (0%)

---

## Próximo Comando a Executar

```bash
# Verificar implementação atual
python scripts/check_implementation.py

# Próximas tarefas:
# 1. Implementar FastAPI App Setup (T055)
# 2. Implementar API endpoints (T056-T059)
# 3. Escrever testes (T060-T061)

# Teste end-to-end (requer Qdrant + OpenAI ativos):
# python scripts/test_query_worker.py
```

## Arquivos Criados nesta Sessão

**Workers:**
- `src/workers/base_worker.py` - Base worker com RabbitMQ connection management
- `src/workers/query_worker.py` - Query worker com RAG pipeline completo

**Scripts de Teste:**
- `scripts/test_query_worker.py` - Publica queries de teste no RabbitMQ
- `scripts/check_query_status.py` - Verifica status de queries
- `scripts/check_implementation.py` - Verifica status da implementação
