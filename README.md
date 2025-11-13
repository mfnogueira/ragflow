# RagFlow - RAG-Based Question Answering System

A production-ready Retrieval-Augmented Generation (RAG) system for question answering over the Olist order reviews dataset.

## 🎯 Overview

RagFlow enables users to ask natural language questions about e-commerce order reviews and receive AI-generated answers with supporting evidence. The system ingests documents (CSV, PDF, DOCX), processes them into vector embeddings, and uses OpenAI's LLM to generate contextual, accurate responses.

**Key Features**:
- 📄 Document ingestion pipeline (preprocessing, chunking, PII redaction)
- 🔍 Semantic search using vector embeddings (Qdrant)
- 🤖 LLM-based answer generation with confidence scoring
- 🛡️ Guardrails for input validation and output safety
- 📊 Comprehensive observability (Prometheus, Grafana, Jaeger)
- ⚖️ Human escalation for low-confidence queries
- 📈 Horizontally scalable with Kubernetes

## 🚀 Quick Start

**Prerequisites**: Docker, Python 3.11+, 8GB RAM

### 1. Clone & Setup

```bash
git checkout 001-rag-qa-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Infrastructure

```bash
docker-compose up -d
# Verify services: RabbitMQ (15672), Qdrant (6333), PostgreSQL (5432), Redis (6379)
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

### 4. Run Migrations

```bash
alembic upgrade head
python scripts/seed_collections.py
```

### 5. Start Workers & API

```bash
honcho start
# Or manually:
# Terminal 1: python -m src.workers.query_worker
# Terminal 2: python -m src.workers.embed_worker
# Terminal 3: python -m src.workers.ingest_worker
# Terminal 4: uvicorn src.api.main:app --reload
```

### 6. Test the System

```bash
# Ingest sample data
curl -X POST http://localhost:8000/v1/documents \
  -H "X-API-Key: dev-api-key-12345" \
  -F "file=@sample_data/olist_reviews_sample.csv" \
  -F "collection_name=olist_reviews"

# Submit query
curl -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query_text": "Quais são os principais motivos de avaliações negativas?"}'
```

**Full setup guide**: [specs/001-rag-qa-system/quickstart.md](specs/001-rag-qa-system/quickstart.md)

## 📚 Documentation

- **[Feature Specification](specs/001-rag-qa-system/spec.md)** - User stories, requirements, success criteria
- **[Implementation Plan](specs/001-rag-qa-system/plan.md)** - Architecture, tech stack, project structure
- **[Data Model](specs/001-rag-qa-system/data-model.md)** - Entities, relationships, storage strategy
- **[API Contracts](specs/001-rag-qa-system/contracts/openapi.yaml)** - REST API specification (OpenAPI 3.0)
- **[Message Schemas](specs/001-rag-qa-system/contracts/rabbitmq-messages.yaml)** - RabbitMQ message formats
- **[Tasks](specs/001-rag-qa-system/tasks.md)** - Implementation tasks (128 total, 66 for MVP)
- **[Research](specs/001-rag-qa-system/research.md)** - Technical decisions and rationale

## 🏗️ Architecture

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Documents  │─────▶│  RabbitMQ   │─────▶│   Workers   │
│  (CSV/PDF)  │      │   Queues    │      │ (Ingest/    │
└─────────────┘      └─────────────┘      │  Embed)     │
                                           └──────┬──────┘
                                                  │
                                                  ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   User      │─────▶│  FastAPI    │─────▶│   Qdrant    │
│   Query     │      │    API      │      │  (Vectors)  │
└─────────────┘      └──────┬──────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐      ┌─────────────┐
                     │ Query Worker│─────▶│   OpenAI    │
                     │ (RAG Logic) │      │ (LLM/Embed) │
                     └─────────────┘      └─────────────┘
```

**Technologies**:
- **Python 3.11+**: Application runtime
- **LangChain**: RAG orchestration framework
- **OpenAI**: LLM (GPT-4o-mini) + Embeddings (text-embedding-3-small)
- **Qdrant**: Vector database for semantic search
- **RabbitMQ**: Message queue for async processing
- **PostgreSQL**: Transactional data storage
- **Redis**: Semantic caching layer
- **FastAPI**: REST API framework
- **Kubernetes**: Container orchestration
- **Prometheus + Grafana**: Monitoring and alerting
- **Jaeger**: Distributed tracing

## 🧪 Testing

```bash
# Unit tests (fast, no external deps)
pytest tests/unit/ -v

# Integration tests (requires Docker services)
pytest tests/integration/ -v

# End-to-end tests (full pipeline)
pytest tests/e2e/ -v --slow

# All tests with coverage
pytest --cov=src --cov-report=html
```

## 📊 Monitoring

- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Prometheus**: http://localhost:9090 (if running monitoring stack)
- **Grafana**: http://localhost:3000 (admin/admin, if running monitoring stack)
- **Jaeger**: http://localhost:16686 (if running monitoring stack)

## 🚢 Deployment

### Docker Compose (Development)

```bash
docker-compose up -d
docker-compose logs -f
```

### Kubernetes (Production)

```bash
# Apply configurations
kubectl apply -f k8s/configmaps/
kubectl apply -f k8s/secrets/
kubectl apply -f k8s/deployments/
kubectl apply -f k8s/services/
kubectl apply -f k8s/hpa/

# Check status
kubectl get pods -l app=ragflow
kubectl logs -f deployment/api
```

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/your-feature`
2. Write tests first (TDD)
3. Implement feature
4. Run tests: `pytest tests/`
5. Lint: `ruff check src/ tests/`
6. Format: `ruff format src/ tests/`
7. Type check: `mypy src/`
8. Commit: `git commit -m "Add feature"`
9. Push: `git push origin feature/your-feature`
10. Create pull request

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 📧 Contact

- **Team**: dev-team@example.com
- **GitHub Issues**: [Issues](https://github.com/your-org/ragflow/issues)
- **Documentation**: [Quickstart Guide](specs/001-rag-qa-system/quickstart.md)

---

**Status**: 🚧 Phase 3 - MVP Implementation (User Story 1)
**Version**: 0.1.0
**Last Updated**: 2025-11-13
