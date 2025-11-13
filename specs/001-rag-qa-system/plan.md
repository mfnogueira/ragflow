# Implementation Plan: RAG-Based Question Answering System

**Branch**: `001-rag-qa-system` | **Date**: 2025-11-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-rag-qa-system/spec.md`

## Summary

Build a production-ready Retrieval-Augmented Generation (RAG) system for question answering over the Olist order reviews dataset. The system ingests documents (CSV, PDF, DOCX), processes them into vector embeddings, stores them in Qdrant, and uses OpenAI's LLM to generate contextual answers to user queries. The architecture is horizontally scalable using RabbitMQ for asynchronous message processing, with guardrails for safety, comprehensive observability, and human escalation fallback.

**Key Capabilities**:
- Document ingestion pipeline with preprocessing, chunking, and PII redaction
- Semantic search using vector embeddings (Qdrant)
- LLM-based answer generation with confidence scoring
- Guardrails for input validation and output safety
- Human escalation workflow for low-confidence queries
- Prometheus + Grafana + Jaeger observability stack
- Kubernetes-ready deployment with horizontal autoscaling

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: LangChain 0.1+, OpenAI SDK 1.10+, Qdrant Client 1.7+, Pika (RabbitMQ) 1.3+, FastAPI 0.109+, Pydantic 2.5+, PostgreSQL (psycopg 3.1+), Redis 5.0+
**Storage**: PostgreSQL 14+ (transactional data), Qdrant 1.7+ (vector embeddings), Redis 7+ (caching), S3/MinIO (document archival)
**Testing**: pytest (unit, integration, E2E), testcontainers (integration tests), OpenAPI validators (contract tests)
**Target Platform**: Kubernetes (AWS EKS, GCP GKE, or on-prem), Docker Compose (local dev)
**Project Type**: Distributed microservices (message-driven workers + REST API)
**Performance Goals**:
- Query latency p95 < 5s (normal load: 100 concurrent users, 10 QPS)
- Query latency p95 < 10s (peak load: 500 QPM)
- Document ingestion: 10 min per 100MB
**Constraints**:
- PII must be redacted before storage (LGPD compliance)
- Answers must cite source chunks (traceability)
- System must handle graceful degradation (cache fallback if LLM unavailable)
- Cost target: <$0.001 per query (embedding + LLM + infrastructure)
**Scale/Scope**:
- Initial: 1000 concurrent users, 10 QPS average, 50 QPS peak
- Target: 10k concurrent users, 100 QPS average, 500 QPS peak
- Data: 10GB-1TB indexed documents (100k-100M chunks)

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Constitution Status**: No project-specific constitution defined yet (constitution.md is template). Proceeding with industry best practices for RAG systems.

**Default Principles Applied**:
1. **Simplicity**: Start with monolithic workers (separate ingest/embed/query processes), avoid premature microservice splitting
2. **Testability**: TDD approach with unit → integration → E2E test pyramid
3. **Observability**: OpenTelemetry tracing, Prometheus metrics, structured logging from day 1
4. **Security**: Defense-in-depth (input sanitization, output filtering, PII redaction, audit logging)
5. **Scalability**: Stateless workers, horizontal scaling via Kubernetes HPA, message queue for decoupling

**No Gates Violated** - Complexity is justified by:
- Asynchronous processing (RabbitMQ) required for long-running ingestion tasks
- Vector database (Qdrant) required for semantic search (no simpler alternative for RAG)
- LLM integration (OpenAI) required for answer generation (core feature)
- Separate worker pools required for resource isolation (embedding vs query have different profiles)

---

## Project Structure

### Documentation (this feature)

```text
specs/001-rag-qa-system/
├── spec.md              # Feature specification (/speckit.specify output)
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0: Technical decisions and rationale
├── data-model.md        # Phase 1: Entity definitions and relationships
├── quickstart.md        # Phase 1: Developer onboarding guide
├── contracts/           # Phase 1: API and message schemas
│   ├── openapi.yaml     # REST API specification
│   └── rabbitmq-messages.yaml  # Message queue schemas
└── tasks.md             # Phase 2: Implementation tasks (/speckit.tasks - NOT YET CREATED)
```

### Source Code (repository root)

```text
ragflow/
├── src/
│   ├── api/                    # REST API (FastAPI)
│   │   ├── main.py             # FastAPI app entrypoint
│   │   ├── routers/            # Endpoint routers
│   │   │   ├── query.py        # /query endpoints
│   │   │   ├── documents.py    # /documents endpoints
│   │   │   ├── escalations.py  # /escalations endpoints
│   │   │   └── monitoring.py   # /health, /metrics endpoints
│   │   └── middleware/         # Auth, CORS, logging middleware
│   │
│   ├── workers/                # Message queue workers
│   │   ├── ingest_worker.py    # Document ingestion
│   │   ├── embed_worker.py     # Embedding generation
│   │   ├── query_worker.py     # Query processing
│   │   └── base_worker.py      # Shared worker logic
│   │
│   ├── services/               # Business logic
│   │   ├── ingestion_service.py   # Document preprocessing, chunking
│   │   ├── embedding_service.py   # Embedding generation (OpenAI)
│   │   ├── retrieval_service.py   # Vector search (Qdrant)
│   │   ├── generation_service.py  # LLM answer generation
│   │   ├── guardrails_service.py  # Input/output validation
│   │   └── escalation_service.py  # Human escalation logic
│   │
│   ├── models/                 # Data models (Pydantic)
│   │   ├── document.py         # Document, Chunk entities
│   │   ├── query.py            # Query, Answer, QueryResult entities
│   │   ├── escalation.py       # EscalationRequest entity
│   │   ├── audit.py            # AuditEvent entity
│   │   └── messages.py         # RabbitMQ message schemas
│   │
│   ├── repositories/           # Data access layer
│   │   ├── document_repo.py    # PostgreSQL CRUD for documents
│   │   ├── query_repo.py       # PostgreSQL CRUD for queries
│   │   ├── vector_repo.py      # Qdrant vector operations
│   │   └── cache_repo.py       # Redis caching
│   │
│   ├── lib/                    # Shared utilities
│   │   ├── config.py           # Environment variable management
│   │   ├── database.py         # PostgreSQL connection pooling
│   │   ├── queue.py            # RabbitMQ connection and helpers
│   │   ├── vector_db.py        # Qdrant client initialization
│   │   ├── cache.py            # Redis client initialization
│   │   ├── observability.py    # OpenTelemetry setup
│   │   ├── logger.py           # Structured logging (JSON)
│   │   └── exceptions.py       # Custom exception classes
│   │
│   └── cli/                    # Command-line tools
│       ├── create_collection.py  # Initialize Qdrant collection
│       ├── rebuild_index.py      # Reindex vectors
│       └── migrate_db.py         # Database migration helper
│
├── tests/
│   ├── unit/                   # Fast unit tests (no external deps)
│   │   ├── test_chunking.py
│   │   ├── test_pii_detection.py
│   │   ├── test_confidence_scoring.py
│   │   └── ...
│   ├── integration/            # Integration tests (testcontainers)
│   │   ├── test_rabbitmq.py
│   │   ├── test_qdrant.py
│   │   ├── test_embedding.py
│   │   └── ...
│   ├── e2e/                    # End-to-end tests (full pipeline)
│   │   ├── test_rag_pipeline.py
│   │   ├── test_ingestion_flow.py
│   │   └── test_escalation_flow.py
│   └── fixtures/               # Test data and utilities
│       ├── sample_reviews.csv
│       ├── mock_llm_responses.json
│       └── test_helpers.py
│
├── alembic/                    # Database migrations
│   ├── versions/               # Migration scripts
│   └── env.py                  # Alembic config
│
├── docker/
│   ├── Dockerfile.api          # API server image
│   ├── Dockerfile.workers      # Worker pool image
│   └── Dockerfile.dev          # Development image
│
├── k8s/                        # Kubernetes manifests
│   ├── deployments/
│   │   ├── api.yaml
│   │   ├── query-workers.yaml
│   │   ├── embed-workers.yaml
│   │   └── ingest-workers.yaml
│   ├── services/
│   │   ├── api-service.yaml
│   │   └── internal-services.yaml
│   ├── configmaps/
│   │   └── app-config.yaml
│   ├── secrets/
│   │   └── secrets.yaml.template
│   └── hpa/                    # HorizontalPodAutoscalers
│       ├── query-workers-hpa.yaml
│       └── embed-workers-hpa.yaml
│
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml      # Scrape configs
│   │   └── alerts.yml          # Alerting rules
│   ├── grafana/
│   │   └── dashboards/
│   │       ├── operations.json
│   │       ├── quality.json
│   │       └── infrastructure.json
│   └── jaeger/
│       └── jaeger-deployment.yaml
│
├── scripts/
│   ├── seed_collections.py     # Initialize Qdrant collections
│   ├── download_olist_data.sh  # Download Kaggle dataset
│   └── generate_sample_data.py # Create synthetic test data
│
├── sample_data/
│   └── olist_reviews_sample.csv  # 1000 sample reviews (for quickstart)
│
├── .env.example                # Environment variables template
├── docker-compose.yml          # Local dev infrastructure
├── docker-compose.workers.yml  # Workers as Docker containers
├── docker-compose.monitoring.yml  # Monitoring stack
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── pyproject.toml              # Python project metadata
├── Procfile                    # Heroku/honcho process definitions
├── alembic.ini                 # Alembic config
├── pytest.ini                  # Pytest config
├── mypy.ini                    # Type checking config
└── README.md                   # Project overview
```

**Structure Decision**: Single project (distributed workers) structure selected because:
- All components share Python runtime and dependencies
- Workers and API are tightly coupled via shared data models and RabbitMQ schemas
- Deployment is via Kubernetes (not separate repos per service)
- Monorepo simplifies development (single PR for cross-component changes)

---

## Complexity Tracking

**No Constitution violations to justify** - all architectural choices are standard for production RAG systems and necessary for scale/reliability requirements.

---

## Phase 0: Research Completed ✅

**Output**: [research.md](./research.md)

**Key Decisions Made**:
1. **Language**: Python 3.11+ (RAG ecosystem, async support, type safety)
2. **Message Queue**: RabbitMQ 3.12+ (topic routing, reliability, mature Python SDK)
3. **Vector DB**: Qdrant 1.7+ (performance, collections, metadata filtering)
4. **RAG Framework**: LangChain 0.1+ (maturity, observability, flexibility)
5. **LLM**: GPT-4o-mini primary, GPT-4o fallback (cost-performance balance)
6. **Embeddings**: text-embedding-3-small (multilingual, cost-effective)
7. **Guardrails**: Hybrid (rule-based + LLM-Guard for advanced checks)
8. **Observability**: Prometheus + Grafana + Jaeger + Loki (CNCF standard)
9. **Workers**: Kubernetes HPA (auto-scaling, fault-tolerant, stateless)
10. **Chunking**: 512 tokens, 20% overlap (research-backed optimal size)
11. **Reranking**: Optional Cohere Rerank (selective, for complex queries)
12. **Testing**: Multi-layer (pytest + testcontainers + E2E)
13. **Deployment**: Kubernetes on EKS/GKE/on-prem (scalable, vendor-agnostic)
14. **Security**: Defense-in-depth, LGPD-compliant
15. **Cost Optimization**: Caching (30%) + model selection (50%) + spot instances (50%)

All decisions documented with rationale and alternatives in research.md.

---

## Phase 1: Design Completed ✅

### 1.1 Data Model ✅

**Output**: [data-model.md](./data-model.md)

**Entities Defined**:
- **Document** (source files)
- **Chunk** (processed text segments with embeddings)
- **Query** (user questions)
- **Answer** (LLM-generated responses)
- **QueryResult** (retrieved chunks for a query, M:N link)
- **EscalationRequest** (human support escalations)
- **EmbeddingJob** (batch embedding tasks)
- **AuditEvent** (compliance logging)
- **Collection** (Qdrant collection metadata)

**Storage**:
- PostgreSQL 14+ for transactional data
- Qdrant 1.7+ for vector embeddings
- Redis 7+ for semantic caching

**Relationships**: All documented with ER diagram, validation rules, state transitions, retention policies.

### 1.2 API Contracts ✅

**Output**: [contracts/openapi.yaml](./contracts/openapi.yaml), [contracts/rabbitmq-messages.yaml](./contracts/rabbitmq-messages.yaml)

**REST API Endpoints** (OpenAPI 3.0):
- `POST /query` - Submit question
- `GET /query/{query_id}` - Get query status
- `POST /query/{query_id}/escalate` - Escalate to human
- `POST /documents` - Ingest document (admin)
- `GET /documents/{document_id}` - Get ingestion status
- `GET /escalations` - List escalation queue (admin)
- `POST /escalations/{escalation_id}/assign` - Assign to agent
- `POST /escalations/{escalation_id}/resolve` - Resolve escalation
- `GET /health` - Health check
- `GET /metrics` - System metrics (admin)

**RabbitMQ Message Schemas**:
- `IngestDocumentMessage` (ingest_queue)
- `EmbedChunksMessage` (embed_queue)
- `ProcessQueryMessage` (query_queue)
- `AuditEventMessage` (audit_queue)

All with JSON schemas, examples, consumer guidelines, monitoring setup.

### 1.3 Quickstart Guide ✅

**Output**: [quickstart.md](./quickstart.md)

**Contents**:
- Prerequisites and setup instructions
- Docker Compose infrastructure (RabbitMQ, Qdrant, PostgreSQL, Redis)
- Database migrations with Alembic
- Worker startup (ingest, embed, query)
- API server startup
- Document ingestion walkthrough (Olist sample data)
- Query submission examples
- Monitoring dashboards (RabbitMQ, Qdrant, Prometheus, Grafana, Jaeger)
- Testing instructions (unit, integration, E2E)
- Troubleshooting guide
- Development workflow

### 1.4 Agent Context ⚠️

**Status**: Script encountered error but CLAUDE.md should be updated manually if needed.

**Technologies to document**:
- Python 3.11+, LangChain, OpenAI SDK, Qdrant, Pika, FastAPI, Pydantic, PostgreSQL, Redis
- RabbitMQ, Kubernetes, Docker, Prometheus, Grafana, Jaeger, Loki
- pytest, testcontainers, OpenAPI validators, Alembic

---

## Phase 2: Task Generation (NOT YET COMPLETED)

**Next Step**: Run `/speckit.tasks` to generate dependency-ordered implementation tasks in `tasks.md`.

**Expected Task Categories**:
1. **Infrastructure Setup** (Docker Compose, Kubernetes manifests, database migrations)
2. **Core Data Models** (Pydantic models, PostgreSQL schema, Qdrant collections)
3. **Repository Layer** (CRUD operations for PostgreSQL, Qdrant, Redis)
4. **Service Layer** (ingestion, embedding, retrieval, generation, guardrails, escalation)
5. **Workers** (ingest worker, embed worker, query worker, base worker)
6. **API** (FastAPI routers, middleware, OpenAPI docs)
7. **Testing** (unit tests, integration tests, E2E tests)
8. **Observability** (OpenTelemetry tracing, Prometheus metrics, Grafana dashboards)
9. **Security & Compliance** (PII detection, input validation, output filtering, audit logging)
10. **Documentation** (README, API docs, runbooks)

---

## Success Criteria (from Spec)

The implementation will be considered successful when:

- **SC-001**: Query latency p95 < 5s for 95% of requests (100 concurrent users, 10 QPS)
- **SC-002**: Answer relevance rating ≥ 4/5 for 85% of queries (human evaluation)
- **SC-003**: Document ingestion success rate ≥ 99% (10 min per 100MB, 1 hour per 1GB)
- **SC-004**: Escalation rate < 15% (low confidence or validation failures)
- **SC-005**: System uptime ≥ 99.5% (rolling 30-day window)
- **SC-006**: Monitoring staleness < 30 seconds (real-time operational visibility)
- **SC-007**: Peak load handling: 500 QPM without degradation (p95 < 10s, error rate < 5%)
- **SC-008**: Zero PII leakage in generated answers (automated + manual audits)
- **SC-009**: Cache hit rate ≥ 30% (cost optimization)
- **SC-010**: Adversarial input detection ≥ 95% (prompt injection, jailbreak)
- **SC-011**: Distributed tracing coverage = 100% (end-to-end debugging)
- **SC-012**: Average confidence score for non-escalated queries ≥ 0.80 (quality threshold)

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **OpenAI API rate limits** | Medium | High | Implement aggressive caching (30% hit rate target), use exponential backoff, consider self-hosted LLM at >1M queries/month |
| **Vector DB performance degradation** | Low | High | Monitor Qdrant query latency, use HNSW index tuning, horizontal scaling via sharding |
| **PII leakage** | Low | Critical | Multi-layer redaction (input + output), automated scanning, regular audits, compliance logging |
| **Worker pod crashes** | Medium | Medium | Kubernetes self-healing, message acknowledgment ensures no data loss, alerting for high error rates |
| **Cost overruns** | Medium | Medium | Daily cost monitoring, alerts at $100/day, semantic caching, model selection (GPT-4o-mini vs GPT-4) |
| **Low answer quality** | Medium | High | Human evaluation, feedback loop, reranking for complex queries, confidence-based escalation |
| **Slow ingestion** | Low | Medium | Parallel chunk processing, batch embedding (100 chunks/call), horizontal scaling of embed workers |
| **Kubernetes complexity** | Medium | Medium | Start with Docker Compose for dev, comprehensive runbooks, gradual K8s rollout, managed K8s (EKS/GKE) |

---

## Next Steps

1. **Generate tasks**: Run `/speckit.tasks` to create `tasks.md` with ordered implementation steps
2. **Review tasks**: Team reviews tasks for completeness and estimates
3. **Sprint planning**: Assign tasks to developers, set milestones
4. **Infrastructure**: Provision Kubernetes cluster, set up monitoring stack
5. **Parallel development**:
   - Track 1: Core data models + repository layer
   - Track 2: API + workers (dependent on Track 1)
   - Track 3: Tests (unit tests alongside features, integration/E2E after)
6. **Continuous integration**: Set up CI pipeline (lint, test, build, deploy to staging)
7. **Staging deployment**: Deploy to staging K8s cluster, run E2E tests
8. **Production rollout**: Gradual rollout to production with monitoring
9. **Post-launch**: Monitor metrics, gather user feedback, iterate on quality

---

## Implementation Timeline Estimate

Based on research and design artifacts:

- **Weeks 1-2**: Infrastructure setup (Docker Compose, K8s, CI/CD) + Data models + Repository layer
- **Weeks 3-4**: Service layer (ingestion, embedding, retrieval, generation) + Unit tests
- **Weeks 5-6**: Workers (ingest, embed, query) + API endpoints + Integration tests
- **Weeks 7-8**: Guardrails, escalation, observability + E2E tests
- **Week 9**: Staging deployment, load testing, bug fixes
- **Week 10**: Production rollout, documentation, runbooks
- **Week 11-12**: Monitoring, user feedback, iteration

**Total**: 12 weeks (3 months) for MVP with 2-3 full-time engineers

---

## References

- [Feature Specification](./spec.md)
- [Research & Technical Decisions](./research.md)
- [Data Model](./data-model.md)
- [API Contracts](./contracts/openapi.yaml)
- [Message Schemas](./contracts/rabbitmq-messages.yaml)
- [Quickstart Guide](./quickstart.md)
- [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

---

**Plan Status**: ✅ **Phase 0 & Phase 1 Complete** - Ready for `/speckit.tasks` to generate implementation tasks.
