# Quickstart Guide: RAG Q&A System

**Feature**: 001-rag-qa-system
**Audience**: Developers onboarding to the project
**Time to complete**: 30-45 minutes

## Overview

This guide walks you through setting up a local development environment for the RAG Q&A System, running your first document ingestion, submitting queries, and understanding the system architecture.

**What you'll accomplish**:
1. ✅ Set up local development environment (Python, Docker, dependencies)
2. ✅ Start core services (RabbitMQ, Qdrant, PostgreSQL)
3. ✅ Ingest your first document
4. ✅ Submit a query and get an answer
5. ✅ Explore monitoring dashboards

---

## Prerequisites

- **OS**: macOS, Linux, or Windows (with WSL2)
- **Tools**:
  - Docker Desktop 4.20+ (with Docker Compose)
  - Python 3.11+ (preferably 3.12)
  - Git
  - 8GB RAM minimum (16GB recommended)
  - 10GB free disk space

- **Optional (for production)**:
  - Kubernetes cluster (Minikube, k3s, EKS, GKE)
  - OpenAI API key (can start with mocked responses)

---

## Step 1: Clone Repository & Install Dependencies

```bash
# Clone the repository
git clone https://github.com/your-org/ragflow.git
cd ragflow

# Checkout the feature branch (if working on this feature)
git checkout 001-rag-qa-system

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install development dependencies (testing, linting)
pip install -r requirements-dev.txt
```

**What's in requirements.txt**:
- `langchain>=0.1.0` - RAG orchestration framework
- `openai>=1.10.0` - OpenAI API client (LLM + embeddings)
- `qdrant-client>=1.7.0` - Vector database client
- `pika>=1.3.0` - RabbitMQ client
- `fastapi>=0.109.0` - API framework
- `pydantic>=2.5.0` - Data validation
- `psycopg[binary]>=3.1.0` - PostgreSQL client
- `redis>=5.0.0` - Caching layer
- `opentelemetry-api>=1.22.0` - Distributed tracing
- `prometheus-client>=0.19.0` - Metrics export

---

## Step 2: Start Infrastructure Services

We use Docker Compose to run all infrastructure locally.

```bash
# Start all services in detached mode
docker-compose up -d

# Check service health
docker-compose ps

# Expected output:
# NAME                COMMAND                  STATUS              PORTS
# rabbitmq            "docker-entrypoint.s…"   Up 10 seconds       0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
# qdrant              "./qdrant"               Up 10 seconds       0.0.0.0:6333->6333/tcp
# postgres            "docker-entrypoint.s…"   Up 10 seconds       0.0.0.0:5432->5432/tcp
# redis               "redis-server"           Up 10 seconds       0.0.0.0:6379->6379/tcp
```

**Service Endpoints**:
- **RabbitMQ Management UI**: http://localhost:15672 (user: `guest`, password: `guest`)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **PostgreSQL**: `postgres://postgres:postgres@localhost:5432/ragflow`
- **Redis**: `redis://localhost:6379`

**Verify services**:
```bash
# Test RabbitMQ
curl -u guest:guest http://localhost:15672/api/overview

# Test Qdrant
curl http://localhost:6333/

# Test PostgreSQL
psql postgres://postgres:postgres@localhost:5432/ragflow -c "SELECT version();"

# Test Redis
redis-cli ping  # Should return "PONG"
```

---

## Step 3: Database Migrations

Initialize the PostgreSQL schema with Alembic migrations.

```bash
# Run migrations to create tables
alembic upgrade head

# Verify tables were created
psql postgres://postgres:postgres@localhost:5432/ragflow -c "\dt"

# Expected tables:
# - documents
# - chunks (metadata only, vectors in Qdrant)
# - queries
# - answers
# - query_results
# - escalation_requests
# - embedding_jobs
# - audit_events
# - collections
```

**Seed default collections**:
```bash
# Create initial Qdrant collections
python scripts/seed_collections.py

# This creates:
# - olist_reviews (1536 dimensions, cosine distance)
# - product_docs (1536 dimensions, cosine distance)
# - support_articles (1536 dimensions, cosine distance)
```

---

## Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Copy template
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Minimal .env for local development**:
```env
# Application
ENVIRONMENT=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ragflow

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
RABBITMQ_PREFETCH_COUNT=5

# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Leave empty for local

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI API
OPENAI_API_KEY=sk-proj-...  # Your OpenAI API key
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Guardrails
CONFIDENCE_THRESHOLD=0.7
MAX_QUERY_LENGTH=1000

# Caching
CACHE_TTL_SECONDS=3600

# Monitoring
PROMETHEUS_PORT=9090
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
```

**Get OpenAI API Key** (if you don't have one):
1. Go to https://platform.openai.com/api-keys
2. Create a new secret key
3. Copy to `.env` file

**Local development without OpenAI** (use mocked LLM):
```env
OPENAI_API_KEY=mock
USE_MOCK_LLM=true
```

---

## Step 5: Start Workers

Workers consume messages from RabbitMQ queues. Start each worker type in separate terminal windows.

**Terminal 1 - Ingest Worker**:
```bash
source venv/bin/activate
python -m workers.ingest_worker

# Expected output:
# [INFO] Starting ingest worker (ID: ingest-worker-01)
# [INFO] Connected to RabbitMQ at amqp://guest:guest@localhost:5672/
# [INFO] Consuming from queue: ingest_queue
# [INFO] Worker ready. Waiting for messages...
```

**Terminal 2 - Embed Worker**:
```bash
source venv/bin/activate
python -m workers.embed_worker

# Expected output:
# [INFO] Starting embed worker (ID: embed-worker-01)
# [INFO] Connected to RabbitMQ at amqp://guest:guest@localhost:5672/
# [INFO] Consuming from queue: embed_queue
# [INFO] Worker ready. Waiting for messages...
```

**Terminal 3 - Query Worker**:
```bash
source venv/bin/activate
python -m workers.query_worker

# Expected output:
# [INFO] Starting query worker (ID: query-worker-01)
# [INFO] Connected to RabbitMQ at amqp://guest:guest@localhost:5672/
# [INFO] Consuming from queue: query_queue
# [INFO] Worker ready. Waiting for messages...
```

**Alternative: Run all workers in background** (for convenience):
```bash
# Use honcho or foreman to run all workers from Procfile
pip install honcho
honcho start

# Or use Docker Compose (workers as containers)
docker-compose -f docker-compose.workers.yml up -d
```

---

## Step 6: Start API Server

The API server exposes REST endpoints for document ingestion and query submission.

**Terminal 4 - API Server**:
```bash
source venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Expected output:
# INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
# INFO:     Started reloader process [12345] using StatReload
# INFO:     Started server process [12346]
# INFO:     Waiting for application startup.
# INFO:     Application startup complete.
```

**Test API**:
```bash
# Health check
curl http://localhost:8000/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2025-11-13T10:00:00Z",
#   "components": {
#     "database": "up",
#     "vector_db": "up",
#     "message_queue": "up",
#     "llm_api": "up"
#   }
# }
```

**API Documentation**:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Step 7: Ingest Your First Document

Let's ingest a sample CSV file with customer reviews.

**Option A: Use sample data** (included in repo):
```bash
# Sample file: sample_data/olist_reviews_sample.csv (1000 reviews)
curl -X POST http://localhost:8000/v1/documents \
  -H "X-API-Key: dev-api-key-12345" \
  -F "file=@sample_data/olist_reviews_sample.csv" \
  -F "collection_name=olist_reviews" \
  -F 'metadata={"source":"sample","env":"dev"}'

# Expected response:
# {
#   "document_id": "550e8400-e29b-41d4-a716-446655440000",
#   "file_name": "olist_reviews_sample.csv",
#   "status": "pending",
#   "message": "Document queued for processing.",
#   "estimated_processing_minutes": 2
# }
```

**Option B: Download full Olist dataset** (optional):
```bash
# Install Kaggle CLI
pip install kaggle

# Configure Kaggle credentials (get from https://www.kaggle.com/settings)
mkdir -p ~/.kaggle
cp kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json

# Download dataset
kaggle datasets download -d olistbr/brazilian-ecommerce
unzip brazilian-ecommerce.zip -d data/olist/

# Ingest order reviews file (~100MB)
curl -X POST http://localhost:8000/v1/documents \
  -H "X-API-Key: dev-api-key-12345" \
  -F "file=@data/olist/olist_order_reviews_dataset.csv" \
  -F "collection_name=olist_reviews"
```

**Monitor ingestion progress**:
```bash
# Poll document status
export DOC_ID="550e8400-e29b-41d4-a716-446655440000"
watch -n 5 "curl -s http://localhost:8000/v1/documents/$DOC_ID | jq"

# Check RabbitMQ queues
curl -u guest:guest http://localhost:15672/api/queues | jq '.[] | {name, messages}'

# Watch worker logs
tail -f logs/ingest_worker.log
tail -f logs/embed_worker.log
```

**Expected timeline** (for 1000 review CSV):
- `t+0s`: Document created, status=pending
- `t+5s`: Ingest worker picks up, status=processing, stage=preprocessing
- `t+10s`: Chunking complete (~250 chunks created)
- `t+15s`: Embedding job queued
- `t+20s`: Embed worker starts generating embeddings
- `t+50s`: Embeddings complete, vectors indexed in Qdrant
- `t+60s`: Document status=completed, chunk_count=250

---

## Step 8: Submit Your First Query

Now that we have indexed data, let's ask a question!

**Simple query** (Portuguese, matching Olist dataset language):
```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Quais são os principais motivos de avaliações negativas?",
    "user_id": "dev_user",
    "options": {
      "collection_filter": ["olist_reviews"],
      "max_chunks": 10
    }
  }'

# Expected response (within ~2-5 seconds):
# {
#   "query_id": "770e8400-e29b-41d4-a716-446655440002",
#   "answer_text": "Com base nas avaliações, os principais motivos de reclamações negativas são:\n1. Atraso na entrega (45%)\n2. Produto com defeito (30%)\n3. Atendimento ao cliente ruim (15%)\n4. Embalagem danificada (10%)",
#   "confidence_score": 0.85,
#   "status": "completed",
#   "escalation_suggested": false,
#   "sources": [
#     {
#       "chunk_id": "660e8400-e29b-41d4-a716-446655440001",
#       "relevance_score": 0.87,
#       "text_preview": "O produto chegou com defeito e o atendimento foi péssimo..."
#     }
#   ],
#   "latency_ms": 1250
# }
```

**Query in English** (will work but may have lower confidence):
```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "What are the most common complaints in negative reviews?",
    "user_id": "dev_user"
  }'
```

**Complex query with reranking**:
```bash
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "Compare a satisfação com entrega entre eletrônicos e móveis",
    "options": {
      "enable_reranking": true,
      "max_chunks": 15
    }
  }'
```

---

## Step 9: Explore Monitoring

**RabbitMQ Management UI**:
1. Open http://localhost:15672
2. Login with `guest`/`guest`
3. Navigate to "Queues" tab
4. View message rates, queue depths, consumer counts

**Qdrant Dashboard**:
1. Open http://localhost:6333/dashboard
2. View collections: `olist_reviews`, `product_docs`
3. Inspect vector count, index size, memory usage

**Prometheus Metrics** (if running):
```bash
# Start Prometheus
docker-compose -f docker-compose.monitoring.yml up -d prometheus

# View metrics
open http://localhost:9090

# Example queries:
# - query_latency_seconds_p95
# - rabbitmq_queue_messages_ready{queue="query_queue"}
# - qdrant_collection_vectors_count{collection="olist_reviews"}
```

**Grafana Dashboards** (if running):
```bash
# Start Grafana
docker-compose -f docker-compose.monitoring.yml up -d grafana

# Access dashboards
open http://localhost:3000  # Login: admin/admin

# Import pre-built dashboards from grafana/dashboards/
```

**Jaeger Tracing**:
```bash
# Start Jaeger
docker-compose -f docker-compose.monitoring.yml up -d jaeger

# View traces
open http://localhost:16686

# Search for traces by service: query-worker, embed-worker, etc.
```

---

## Step 10: Run Tests

Validate everything is working correctly.

**Unit tests** (fast, no external dependencies):
```bash
pytest tests/unit/ -v

# Expected output:
# tests/unit/test_chunking.py::test_chunk_text PASSED
# tests/unit/test_pii_detection.py::test_cpf_redaction PASSED
# tests/unit/test_confidence_scoring.py::test_score_calculation PASSED
# ... (500+ tests)
# ======================== 512 passed in 28.5s ========================
```

**Integration tests** (requires Docker services running):
```bash
pytest tests/integration/ -v

# Expected output:
# tests/integration/test_rabbitmq.py::test_message_routing PASSED
# tests/integration/test_qdrant.py::test_vector_insert_search PASSED
# tests/integration/test_embedding.py::test_batch_embedding PASSED
# ... (50+ tests)
# ======================== 53 passed in 5m12s ========================
```

**End-to-end tests** (full RAG pipeline):
```bash
pytest tests/e2e/ -v --slow

# Expected output:
# tests/e2e/test_rag_pipeline.py::test_query_flow PASSED
# tests/e2e/test_ingestion_flow.py::test_document_processing PASSED
# tests/e2e/test_escalation_flow.py::test_low_confidence_escalation PASSED
# ... (10+ tests)
# ======================== 10 passed in 8m45s ========================
```

---

## Troubleshooting

### Issue: "Connection refused" errors

**Symptoms**: Workers or API can't connect to RabbitMQ/Qdrant/PostgreSQL

**Solution**:
```bash
# Check if services are running
docker-compose ps

# Restart services
docker-compose restart

# Check service logs
docker-compose logs rabbitmq
docker-compose logs qdrant
docker-compose logs postgres

# Verify ports are not in use
lsof -i :5672  # RabbitMQ
lsof -i :6333  # Qdrant
lsof -i :5432  # PostgreSQL
```

### Issue: "OpenAI API key invalid"

**Symptoms**: Query worker fails with authentication error

**Solution**:
```bash
# Verify API key is set correctly
echo $OPENAI_API_KEY

# Test API key directly
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# If invalid, generate new key at https://platform.openai.com/api-keys
```

### Issue: "Out of memory" during ingestion

**Symptoms**: Ingest worker crashes with OOM error

**Solution**:
```bash
# Reduce batch size in .env
EMBEDDING_BATCH_SIZE=50  # Default is 100

# Increase Docker memory limit (Docker Desktop > Preferences > Resources)
# Recommended: 8GB minimum, 16GB for large files

# Process smaller files first (<50MB)
```

### Issue: "Slow query responses (>10 seconds)"

**Symptoms**: Queries take too long

**Solution**:
```bash
# Check Qdrant index health
curl http://localhost:6333/collections/olist_reviews

# Rebuild index if needed
python scripts/rebuild_index.py olist_reviews

# Check LLM API latency
curl -w "@curl-format.txt" -o /dev/null -s https://api.openai.com/v1/models

# Enable caching (should be on by default)
redis-cli INFO stats  # Check cache hit rate
```

---

## Next Steps

Now that you have a working local environment:

1. **Read the architecture docs**: `docs/architecture.md`
2. **Review the API contracts**: `specs/001-rag-qa-system/contracts/openapi.yaml`
3. **Explore the data model**: `specs/001-rag-qa-system/data-model.md`
4. **Review implementation tasks**: `specs/001-rag-qa-system/tasks.md` (generated via `/speckit.tasks`)
5. **Join the team chat**: [Link to Slack/Discord]

**Useful resources**:
- LangChain RAG tutorial: https://python.langchain.com/docs/use_cases/question_answering/
- Qdrant documentation: https://qdrant.tech/documentation/
- OpenAI API reference: https://platform.openai.com/docs/api-reference

---

## Development Workflow

### Making changes

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Write tests first** (TDD):
   ```bash
   # Create test file
   touch tests/unit/test_your_feature.py

   # Write failing test
   pytest tests/unit/test_your_feature.py  # Should fail
   ```

3. **Implement feature**:
   ```python
   # Your implementation in src/
   ```

4. **Run tests**:
   ```bash
   pytest tests/unit/test_your_feature.py  # Should pass now
   pytest tests/integration/  # Ensure no regressions
   ```

5. **Lint and format**:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   mypy src/
   ```

6. **Commit and push**:
   ```bash
   git add .
   git commit -m "Add your feature description"
   git push origin feature/your-feature-name
   ```

7. **Create pull request** and request review

### Testing specific components

**Test chunking logic**:
```bash
pytest tests/unit/test_chunking.py -v -k "test_overlap"
```

**Test guardrails**:
```bash
pytest tests/unit/test_guardrails.py -v -k "test_pii"
```

**Test RAG pipeline**:
```bash
pytest tests/e2e/test_rag_pipeline.py -v -k "test_query_flow" --log-cli-level=DEBUG
```

---

## Additional Tools

**Database inspection**:
```bash
# Connect to PostgreSQL
psql postgres://postgres:postgres@localhost:5432/ragflow

# Useful queries
SELECT COUNT(*) FROM documents WHERE processing_status='completed';
SELECT AVG(confidence_score) FROM answers WHERE generation_timestamp > NOW() - INTERVAL '1 hour';
SELECT * FROM escalation_requests WHERE assignment_status='queued' ORDER BY priority_score DESC LIMIT 10;
```

**Vector database inspection**:
```bash
# Connect to Qdrant via Python
python

>>> from qdrant_client import QdrantClient
>>> client = QdrantClient(url="http://localhost:6333")
>>> client.get_collections()
>>> client.count(collection_name="olist_reviews")
>>> client.scroll(collection_name="olist_reviews", limit=5)
```

**Message queue inspection**:
```bash
# List queues
curl -u guest:guest http://localhost:15672/api/queues | jq '.[] | {name, messages}'

# Purge queue (development only!)
curl -u guest:guest -X DELETE http://localhost:15672/api/queues/%2F/query_queue/contents
```

---

## FAQ

**Q: Can I use a different vector database?**
A: Yes, the vector DB is abstracted via LangChain VectorStore interface. Swap Qdrant for Pinecone, Weaviate, etc. by changing `src/vector_store.py`.

**Q: Can I use a different LLM?**
A: Yes, configure `OPENAI_API_BASE` to point to Azure OpenAI, AWS Bedrock, or self-hosted vLLM/Ollama with OpenAI-compatible endpoint.

**Q: How do I add a new collection?**
A: Run `python scripts/create_collection.py <collection_name> <dimension>`, then ingest documents with `collection_name` parameter.

**Q: How do I debug slow queries?**
A: Enable Jaeger tracing, view trace for query ID at http://localhost:16686, inspect span durations for retrieval, generation, validation stages.

**Q: Can I run this on Windows?**
A: Yes, use WSL2 for best compatibility. Native Windows works but requires adjustments to scripts (use `py` instead of `python3`, backslashes in paths).

---

## Summary

You've successfully set up the RAG Q&A System locally! You can now:
- ✅ Ingest documents into the knowledge base
- ✅ Submit queries and receive AI-generated answers
- ✅ Monitor system performance via dashboards
- ✅ Run tests to validate changes
- ✅ Contribute new features via pull requests

**Next**: Review `specs/001-rag-qa-system/tasks.md` to see implementation roadmap and pick up your first task!

---

**Need help?** Contact the team:
- Slack: #ragflow-dev
- Email: dev-team@example.com
- GitHub Issues: https://github.com/your-org/ragflow/issues
