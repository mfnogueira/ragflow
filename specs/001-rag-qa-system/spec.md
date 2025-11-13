# Feature Specification: RAG-Based Question Answering System

**Feature Branch**: `001-rag-qa-system`
**Created**: 2025-11-13
**Status**: Draft
**Input**: User description: "Ingestão — pega olist_order_reviews_dataset.csv (Kaggle) e outros documentos futuros. Pré-processa, faz chunking e normalização. Fila de mensagens (RabbitMQ) — recebe requisições de usuários / eventos. Workers / Consumers — processam mensagens. Vector DB (Qdrant) — armazena vetores + metadata. Orquestrador RAG (LangChain ou LlamaIndex) — coordena busca semântica. LLM (OpenAI) — realiza geração. Guardrails — camadas de segurança/validação. Observabilidade — logs estruturados, métricas. Fallback humano."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Query Order Review Insights (Priority: P1)

Users need to ask questions about Olist order reviews and receive accurate, contextual answers based on the ingested dataset. This enables quick access to insights without manual data analysis.

**Why this priority**: This is the core value proposition of the RAG system - providing intelligent answers to user queries is the primary reason the system exists. Without this working, no other feature delivers value.

**Independent Test**: Can be fully tested by submitting a question about Olist reviews (e.g., "Quais são as reclamações mais comuns?") and receiving a relevant answer with supporting context from the dataset within acceptable time limits.

**Acceptance Scenarios**:

1. **Given** the system has ingested and indexed the Olist review dataset, **When** a user submits the question "Quais são os 5 principais motivos de avaliações negativas?", **Then** the system returns a comprehensive answer with specific examples from the dataset within 5 seconds.

2. **Given** a user asks a question outside the dataset scope (e.g., "Qual é a previsão do tempo hoje?"), **When** the question cannot be answered with available data, **Then** the system responds with "Não tenho informações suficientes para responder essa pergunta" and suggests contacting support.

3. **Given** a user submits an ambiguous question (e.g., "O que os clientes acham?"), **When** the system processes the query, **Then** it either asks for clarification or interprets the question based on semantic understanding and provides the best possible answer with context.

4. **Given** the system generates an answer, **When** the confidence score is below 70%, **Then** the response includes a disclaimer "Esta resposta pode não estar completa. Deseja falar com um especialista?" with option to escalate.

---

### User Story 2 - Ingest New Documents (Priority: P2)

Administrators need to add new documents (CSV files, PDFs, text documents) to the knowledge base so the system can answer questions about newly available data.

**Why this priority**: While critical for system growth and long-term value, initial testing can proceed with only the Olist dataset. This enables MVP validation before scaling to multiple data sources.

**Independent Test**: Can be tested by uploading a new document through the ingestion queue, monitoring processing status, and verifying that queries about the new document content return accurate answers after indexing completes.

**Acceptance Scenarios**:

1. **Given** an administrator has a new CSV file with 50MB of order reviews, **When** they submit it to the ingestion queue, **Then** the system processes the file (preprocessing, chunking, embedding, indexing) and confirms successful completion within 10 minutes.

2. **Given** a document is being processed, **When** the administrator checks the ingestion status via monitoring interface, **Then** they see: file name, current processing stage (preprocessing/chunking/embedding/indexing), percentage complete, processed chunks count, and estimated time remaining.

3. **Given** an invalid file is submitted (corrupted CSV, unsupported format, or missing required columns), **When** the system attempts to process it, **Then** ingestion fails with a clear error message indicating the specific issue ("Invalid CSV format: missing 'review_text' column") and the file is moved to a failed ingestion queue for review.

4. **Given** multiple documents are submitted simultaneously, **When** the ingestion queue receives them, **Then** workers process them in parallel according to available capacity, and each document completes independently without blocking others.

---

### User Story 3 - Monitor System Health and Performance (Priority: P3)

Operations teams need visibility into system performance, reliability, and quality metrics to identify issues, optimize performance, and ensure service level compliance.

**Why this priority**: Essential for production operations but not required for initial feature validation. The system must work correctly before monitoring becomes critical.

**Independent Test**: Can be tested by accessing monitoring dashboards, generating test queries with known patterns (high load, edge cases, errors), and verifying that all metrics update correctly in real-time.

**Acceptance Scenarios**:

1. **Given** the system is processing queries, **When** an operator views the monitoring dashboard, **Then** they see real-time metrics including: queries per second, average/p95/p99 response latency, error rate by type, vector database query time, LLM response time, embedding job queue depth, and cache hit rate.

2. **Given** system latency exceeds 10 seconds for p95 queries, **When** the monitoring system detects the degradation, **Then** it triggers an alert via configured channels (email, Slack, PagerDuty) with diagnostic context including affected components and recent error logs.

3. **Given** an operator wants to assess answer quality over time, **When** they review quality metrics, **Then** they see: confidence score distribution (histogram), escalation rate percentage, average retrieval scores, query coverage rate (answered vs. escalated), and trends over selectable time periods.

4. **Given** the system encounters errors, **When** operators investigate via distributed tracing, **Then** they can trace a request end-to-end from query submission through retrieval, generation, and response, seeing timing and errors for each component.

---

### User Story 4 - Escalate to Human Support (Priority: P4)

When the system cannot confidently answer a question or validation checks fail, users should be seamlessly transferred to human support to ensure they always receive assistance.

**Why this priority**: Important for production quality and user satisfaction, but the core Q&A functionality must work first. This is a safety net that adds value after the primary feature is validated.

**Independent Test**: Can be tested by submitting questions designed to trigger low confidence scores (ambiguous, out-of-scope) or safety violations (prompt injection, harmful content), and verifying that the escalation workflow activates correctly and queues the request appropriately.

**Acceptance Scenarios**:

1. **Given** a user asks a question that returns a confidence score below 70%, **When** the system evaluates the response quality, **Then** it presents the answer with a disclaimer message "Não tenho certeza sobre esta resposta. Deseja falar com um especialista humano?" and provides an option to escalate.

2. **Given** a user's input contains potential prompt injection attempts (e.g., "Ignore all previous instructions and..."), **When** the guardrails analyze the input, **Then** the system blocks the query, returns a generic error message, logs the incident with full context, and does not process the request further.

3. **Given** a question is escalated to human support (either automatically or by user choice), **When** the request is queued, **Then** the support queue contains: original question text, system's attempted answer (if any), confidence score, relevant retrieved chunks for context, user identifier, and timestamp.

4. **Given** a support agent reviews the escalation queue, **When** they select a queued request, **Then** they see all context needed to assist efficiently and can mark the request as resolved or provide feedback to improve future responses.

---

### Edge Cases

- **What happens when the vector database is temporarily unavailable?** The system queues query requests in RabbitMQ for retry with exponential backoff (1s, 2s, 4s, up to 60s), returns a temporary error message to users ("Sistema temporariamente indisponível, tente novamente em alguns segundos"), and logs the outage for operator awareness with severity alerts.

- **How does the system handle concurrent ingestion and querying?** Queries continue to execute against the current vector database collections while new documents are being processed. Once embedding and indexing complete, new chunks are atomically added to the appropriate collection and become immediately available for subsequent queries without requiring system restart or downtime.

- **What happens when LLM API rate limits are exceeded?** The system implements exponential backoff with jitter (randomized delays to prevent thundering herd), queues requests for automatic retry, returns cached responses for identical or semantically similar recent queries (cache TTL: 1 hour), and logs rate limit incidents for capacity planning.

- **How are multilingual queries handled?** The system primarily supports Portuguese (given the Olist Brazilian dataset) with automatic language detection. If queries in other languages are detected, the system processes them using the same pipeline but returns answers based only on available Portuguese dataset content, with a note indicating potential language mismatch if confidence is low.

- **What happens when a document contains personally identifiable information (PII)?** The guardrails scan chunks during preprocessing and redact PII patterns (CPF, email, phone numbers) before generating embeddings and storing in the vector database. Redaction events are logged for compliance auditing, and the original unredacted text is not stored in the retrieval system.

- **How are conflicting or inconsistent information from multiple documents resolved?** When retrieval returns contradictory information, the system presents multiple perspectives in the generated answer, explicitly notes the sources and timestamps of each piece of information, and allows ranking by document recency or metadata-based authority scores if configured.

- **What happens if chunking splits critical information across chunk boundaries?** The chunking strategy uses overlapping windows (e.g., 10-20% overlap between adjacent chunks) to preserve context continuity. If critical entities or concepts span chunks, both chunks will contain partial context, and the retrieval ranking should surface both when relevant to a query.

- **How does the system handle malformed or incomplete messages in the queue?** Workers validate message schema on consumption. Invalid messages are rejected, moved to a dead-letter queue for manual review, and logged with full details. Processing continues with valid messages without blocking the entire queue.

- **What happens when embedding generation fails for specific chunks?** Failed chunks are logged with error details, marked for retry (up to 3 attempts with exponential backoff), and if still failing, moved to a failed chunks collection for investigation. The document is marked as partially indexed, and queries can still retrieve successfully embedded chunks.

## Requirements *(mandatory)*

### Functional Requirements

#### Document Ingestion & Processing

- **FR-001**: System MUST accept document uploads in multiple formats including CSV, PDF, DOCX, and plain text (TXT, MD) for ingestion into the knowledge base.

- **FR-002**: System MUST preprocess documents by performing: text extraction from binary formats, encoding detection and UTF-8 normalization, whitespace normalization, special character handling, and language detection.

- **FR-003**: System MUST split documents into semantically meaningful chunks with configurable size (default: 512 tokens, maximum: 1024 tokens) using overlapping windows (20% overlap) to preserve context across boundaries.

- **FR-004**: System MUST extract metadata during chunking including: source document identifier, chunk sequence position, section headings if available, detected entities (dates, product categories), and original character offsets.

- **FR-005**: System MUST detect and redact PII during preprocessing including: Brazilian CPF numbers, email addresses, phone numbers, and credit card numbers, logging redaction events for compliance auditing.

#### Message Queue & Asynchronous Processing

- **FR-006**: System MUST route incoming requests through separate RabbitMQ queues by operation type: `ingest` (document ingestion), `embed` (embedding generation), `query` (user questions), and `audit` (compliance events).

- **FR-007**: System MUST support topic-based routing to enable selective message consumption by worker pools (e.g., embedding workers subscribe only to `embed` queue).

- **FR-008**: System MUST persist messages in queues with durability guarantees to prevent data loss during system restarts or failures.

- **FR-009**: System MUST implement dead-letter queues for failed messages after maximum retry attempts (default: 3 retries), preserving original message content and error context for debugging.

#### Worker Pools & Scalability

- **FR-010**: System MUST maintain separate worker pools for: embedding generation (batch processing), query handling (retrieval + composition + generation), and document preprocessing (text extraction + chunking).

- **FR-011**: System MUST support horizontal scaling of worker pools by allowing dynamic addition of worker instances that automatically register as queue consumers.

- **FR-012**: System MUST distribute work across workers using fair dispatch (round-robin or least-busy) to balance load and prevent hot-spotting.

- **FR-013**: System MUST allow workers to process messages concurrently up to a configurable concurrency limit per worker (default: 5 concurrent tasks per worker).

#### Vector Database & Retrieval

- **FR-014**: System MUST store vector embeddings in Qdrant with associated metadata including: source document ID, chunk ID, timestamp, chunk text content (for display), and custom metadata fields (language, document type, domain).

- **FR-015**: System MUST organize vectors into separate collections by domain or data source (e.g., `olist_reviews`, `product_docs`, `support_articles`) to enable scoped queries and independent retention management.

- **FR-016**: System MUST perform semantic similarity search using cosine distance or dot product, returning the top K most relevant chunks (default K=10, configurable per query).

- **FR-017**: System MUST support metadata filtering during retrieval (e.g., filter by date range, document type, or domain) to constrain search scope.

- **FR-018**: System MUST implement retention policies per collection with configurable rules (e.g., delete chunks older than 365 days, or archive low-access chunks after 180 days).

#### RAG Orchestration

- **FR-019**: System MUST coordinate retrieval-augmented generation workflow: accept user query, generate query embedding, perform vector search, rank results by relevance, optionally rerank using cross-encoder or LLM, compose prompt with retrieved context, invoke LLM, and return generated answer.

- **FR-020**: System MUST perform reranking of retrieved chunks using relevance scoring that considers: vector similarity score, recency weighting (newer chunks ranked higher), metadata match bonuses, and cross-encoder semantic similarity if configured.

- **FR-021**: System MUST compose LLM prompts using templates that include: system instructions (role, constraints, tone), few-shot examples of high-quality answers, retrieved context chunks with source attribution, and the user's question.

- **FR-022**: System MUST limit total context size passed to LLM to stay within model token limits (e.g., 4000 tokens for context, 1000 tokens for answer generation), truncating or summarizing retrieved chunks if necessary.

#### LLM Integration

- **FR-023**: System MUST generate natural language answers by invoking LLM API with composed prompts, configurable model parameters (temperature, top_p, max_tokens), and streaming support for long responses.

- **FR-024**: System MUST implement request throttling to stay within LLM API rate limits using token bucket or leaky bucket algorithms, queueing excess requests for delayed processing.

- **FR-025**: System MUST cache generated answers for identical queries within a time window (default: 1 hour TTL) using query text hash as cache key, reducing API costs and latency.

- **FR-026**: System MUST detect and handle LLM API errors including: rate limit exceeded (retry with backoff), timeout (retry once then fail gracefully), invalid request (log and return error), and service unavailable (use cached responses if available).

#### Guardrails & Safety

- **FR-027**: System MUST validate user inputs before processing by checking for: excessive length (reject queries > 1000 characters), prompt injection patterns (e.g., "ignore previous instructions"), and harmful content using keyword filtering or LLM-based classification.

- **FR-028**: System MUST validate generated outputs before returning to users by checking for: hallucination indicators (statements not grounded in retrieved context), policy violations (harmful, biased, or inappropriate content), PII leakage, and coherence issues.

- **FR-029**: System MUST assign confidence scores to generated answers using a weighted combination of: average retrieval relevance score (0-1), LLM generation perplexity (0-1), context coverage (percentage of answer supported by retrieved chunks), and output validation pass/fail.

- **FR-030**: System MUST redact any remaining PII in generated outputs (defensive layer) even if not detected during preprocessing, using pattern matching and NER-based detection.

- **FR-031**: System MUST log all validation events (input rejections, output modifications, confidence scores, PII redactions) to the audit queue for compliance reporting and quality monitoring.

#### Escalation & Human Fallback

- **FR-032**: System MUST automatically escalate queries to human support when: confidence score falls below threshold (70%), input validation fails with high severity, output validation fails after regeneration attempts, or user explicitly requests human assistance.

- **FR-033**: System MUST queue escalated requests in a dedicated support queue with priority scoring based on: wait time, user tier (if applicable), confidence score gap, and validation failure severity.

- **FR-034**: System MUST include context for escalated requests: original query, system's attempted answer (if any), confidence score and contributing factors, relevant retrieved chunks, validation failure reasons, and user session metadata.

- **FR-035**: System MUST allow support agents to mark escalations as resolved and optionally provide feedback (correct answer, issue category) that can be used to improve the system through fine-tuning or retrieval improvements.

#### Observability & Monitoring

- **FR-036**: System MUST emit structured logs in JSON format for all operations including: document ingestion events, chunk processing, embedding generation, query processing, retrieval operations, LLM invocations, validation outcomes, escalations, errors, and cache operations.

- **FR-037**: System MUST track and expose metrics including: queries per second (QPS), query latency percentiles (p50, p95, p99), error rates by type and component, vector database operation times, LLM API latency, cache hit rate, escalation rate, queue depths by queue type, and worker utilization.

- **FR-038**: System MUST support distributed tracing using OpenTelemetry or compatible standards, propagating trace context across: message queue boundaries, worker processes, vector database calls, and LLM API calls to enable end-to-end request tracking.

- **FR-039**: System MUST provide monitoring dashboards displaying: real-time operational metrics, query volume trends, performance heatmaps, error rate alerts, queue health status, and answer quality metrics (confidence score distributions, escalation trends).

- **FR-040**: System MUST generate alerts when metrics exceed thresholds: latency p95 > 10 seconds, error rate > 5%, escalation rate > 20%, queue depth > 1000 messages, cache hit rate < 30%, or vector database query time > 2 seconds.

### Key Entities

- **Document**: Represents a source file (e.g., olist_order_reviews_dataset.csv) with attributes including: unique identifier (UUID), file name, file format (CSV/PDF/DOCX/TXT), upload timestamp, file size in bytes, detected language code (pt-BR, en-US), processing status (pending/processing/completed/failed), chunk count, and collection assignment. Related to multiple Chunks.

- **Chunk**: Represents a processed text segment with attributes including: unique identifier (UUID), source document reference (foreign key), text content (original after redaction), vector embedding (array of floats, dimensionality depends on model), sequence position in source document, token count, character start and end offsets in original document, extracted metadata (entities, keywords), creation timestamp, and language code. Related to one Document and multiple QueryResults.

- **Query**: Represents a user question with attributes including: unique identifier (UUID), query text (user's original question), query embedding (vector representation), user identifier (if authenticated, nullable), submission timestamp, detected language, processing status (pending/processing/completed/failed/escalated), assigned worker ID, and session correlation ID. Related to multiple QueryResults, one Answer (if generated), and optionally one EscalationRequest.

- **QueryResult**: Represents a retrieved chunk relevant to a query with attributes including: query reference (foreign key), chunk reference (foreign key), relevance score (0-1 from vector similarity), reranking score (if reranking applied), rank position (1-N in result set), retrieval timestamp, and metadata match flags (boolean indicators for filters). Links Query to Chunk with scoring context.

- **Answer**: Represents a generated response with attributes including: unique identifier (UUID), query reference (foreign key), answer text (LLM-generated response), confidence score (0-1 composite metric), generation timestamp, LLM model used, token count (input + output), latency breakdown (retrieval_ms, generation_ms, total_ms), cache hit flag (boolean), validation status (passed/failed/warnings), escalation flag (boolean), and redaction flag (boolean if PII removed). Related to one Query.

- **EscalationRequest**: Represents a query escalated to human support with attributes including: unique identifier (UUID), query reference (foreign key), answer reference (nullable if no answer generated), escalation reason (low_confidence/validation_failure/user_request), confidence score at escalation, escalation timestamp, priority score (calculated), assignment status (queued/assigned/resolved), assigned agent identifier (nullable), resolution timestamp (nullable), and agent feedback text (nullable). Related to one Query and optionally one Answer.

- **EmbeddingJob**: Represents a batch embedding task with attributes including: unique identifier (UUID), document references (array of foreign keys), chunk count (number to process), processing status (pending/processing/completed/failed), started timestamp, completed timestamp, worker identifier, batch size, processed count (progress tracking), failed count, and error messages (if any). Related to multiple Documents.

- **AuditEvent**: Represents a logged system action with attributes including: unique identifier (UUID), event type (ingestion/query/escalation/validation_failure/pii_detection/cache_hit), timestamp with millisecond precision, actor (user ID or system component name), affected entity IDs (query ID, document ID, etc.), severity level (info/warning/error/critical), event-specific metadata (JSON blob for flexible schema), and trace context (trace ID, span ID for distributed tracing).

- **Collection**: Represents a vector database collection for domain organization with attributes including: unique identifier (string name like `olist_reviews`), description, vector dimensionality, distance metric (cosine/dot_product), document count, total vector count, creation timestamp, last update timestamp, retention policy (days to retain or null for indefinite), and metadata schema (JSON schema for expected metadata fields). Related to multiple Chunks.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive answers to queries within 5 seconds for 95% of requests (p95 latency) under normal load conditions (up to 100 concurrent users, 10 QPS average).

- **SC-002**: System achieves answer relevance rating of 4 or higher on a 5-point scale for 85% of queries when evaluated by human raters against the Olist dataset using a standardized evaluation rubric.

- **SC-003**: System successfully ingests and indexes new documents with 99% success rate, with processing completing within 10 minutes for documents up to 100MB and 1 hour for documents up to 1GB.

- **SC-004**: Less than 15% of queries require escalation to human support due to low confidence or validation failures during normal operation with well-formed queries on in-scope topics.

- **SC-005**: System maintains 99.5% uptime for query processing capabilities, measured as the percentage of time the system can successfully process and return answers to valid queries over a rolling 30-day window.

- **SC-006**: Monitoring dashboards display operational metrics with less than 30 seconds staleness, enabling operators to detect and respond to issues in near real-time.

- **SC-007**: System handles peak load of 500 queries per minute (8.3 QPS sustained) without exceeding p95 latency target of 10 seconds or experiencing error rate increase above 5%.

- **SC-008**: Generated answers contain zero instances of exposed PII (CPF, email, phone, credit card) in production use, as verified by automated scanning and periodic manual audits.

- **SC-009**: Cache hit rate exceeds 30% for production query traffic, demonstrating effective caching of repeated or similar questions and reducing LLM API costs proportionally.

- **SC-010**: System correctly detects and blocks 95% of adversarial inputs (prompt injection, jailbreak attempts) in security testing scenarios, protecting against manipulation of answer generation.

- **SC-011**: Distributed tracing successfully correlates 100% of query requests across all system components (queue, workers, vector DB, LLM), enabling complete end-to-end debugging visibility.

- **SC-012**: Average confidence score for non-escalated queries exceeds 0.80 (80%), indicating the system generally produces high-quality answers when it chooses to respond directly rather than escalate.

## Assumptions

- **A-001**: The primary data source is the Olist order reviews dataset from Kaggle, which is publicly available, in CSV format, and does not contain highly sensitive personal information beyond customer feedback text.

- **A-002**: Users will primarily ask questions in Portuguese (pt-BR), given the Brazilian origin of the Olist dataset, but the system architecture supports future extension to other languages (English, Spanish) through language-agnostic embedding models.

- **A-003**: The system will use asynchronous message-based processing with RabbitMQ-compatible message queuing to enable horizontal scaling, fault tolerance, and decoupling of components.

- **A-004**: Vector storage and retrieval will use Qdrant vector database supporting high-dimensional embeddings (384-1536 dimensions depending on model), semantic similarity search, metadata filtering, and collection-based organization.

- **A-005**: Language model integration will use OpenAI API or compatible alternatives (Azure OpenAI, AWS Bedrock, self-hosted models via OpenAI-compatible endpoints) for answer generation with support for prompt templates, few-shot learning, and configurable generation parameters.

- **A-006**: Embedding generation will use models compatible with the chosen vector database, such as OpenAI text-embedding-ada-002 (1536 dimensions), sentence-transformers multilingual models (768 dimensions), or similar alternatives optimized for semantic search.

- **A-007**: Guardrails will include both rule-based validation (regex patterns for PII, input length limits, keyword blocklists) and model-based safety checks (LLM-based content classification, hallucination detection, prompt injection detection).

- **A-008**: The system will be deployed in a containerized environment (Docker, Kubernetes) supporting horizontal scaling of stateless worker components, with persistent storage for message queues and vector database.

- **A-009**: Initial deployment targets up to 1000 concurrent users with average query rate of 10 queries per second (QPS), peak load of 50 QPS, with architecture designed to scale linearly beyond this baseline through worker pool expansion.

- **A-010**: Confidence threshold for automatic human escalation is set at 0.7 (70%) based on industry best practices for production RAG systems, with this value configurable per deployment based on quality/cost trade-offs.

- **A-011**: Document retention policies default to indefinite storage unless explicitly configured, with support for time-based archival (move to cold storage after N days) and deletion (remove after M days) workflows per collection.

- **A-012**: Chunk size of 512 tokens with 20% overlap provides optimal balance between context preservation and retrieval precision for question-answering tasks on review text, based on published RAG research and benchmarks.

- **A-013**: Typical document processing time is approximately 5-10 minutes per 100MB of text content, accounting for: text extraction (30s), chunking (1min), embedding generation with batch processing (3-7min depending on chunk count), and vector indexing (30s).

- **A-014**: The system assumes UTF-8 text encoding for all documents, with automatic detection and conversion from other encodings (ISO-8859-1, Windows-1252) during preprocessing if needed.

- **A-015**: Average query length is 10-50 words (50-250 characters), with maximum supported query length of 200 words (1000 characters) to prevent abuse and manage embedding costs.

## Dependencies

- **D-001**: Access to Olist order reviews dataset from Kaggle (https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), including CSV file format specification, data dictionary, and usage rights under Kaggle dataset license.

- **D-002**: Message queue infrastructure supporting AMQP protocol (RabbitMQ or compatible alternative like ActiveMQ, Amazon MQ) with features: persistent queues, topic routing, dead-letter queues, message acknowledgments, and monitoring APIs.

- **D-003**: Vector database service providing Qdrant-compatible APIs (Qdrant self-hosted, Qdrant Cloud, or compatible alternative like Milvus, Weaviate) with capabilities: CRUD operations on vectors, similarity search with metadata filtering, collection management, and persistence guarantees.

- **D-004**: LLM API access via OpenAI API (gpt-4, gpt-3.5-turbo) or compatible alternative (Azure OpenAI, AWS Bedrock, Anthropic Claude, self-hosted models via vLLM/Ollama with OpenAI-compatible endpoints) with sufficient rate limits and quotas for expected query volume (minimum: 100 requests per minute).

- **D-005**: Embedding model service for generating vector representations of text, compatible with chosen vector database dimensionality. Options include: OpenAI embeddings API (text-embedding-ada-002), HuggingFace inference API (sentence-transformers models), or self-hosted embedding service.

- **D-006**: Observability infrastructure including: structured logging aggregation (ELK Stack, Loki, CloudWatch Logs), metrics collection and visualization (Prometheus + Grafana, Datadog, New Relic), and distributed tracing (Jaeger, Zipkin, AWS X-Ray) with OpenTelemetry SDK support.

- **D-007**: Authentication and authorization service for controlling access to administrative functions (document ingestion, system configuration, monitoring dashboards) and optionally for user identification in multi-tenant scenarios. Can use OAuth2, JWT, or API key-based authentication.

- **D-008**: Compute infrastructure for horizontally scalable worker pools, with container orchestration (Kubernetes, ECS, Docker Swarm) supporting: dynamic scaling based on queue depth and CPU/memory utilization, health checks, and rolling updates.

- **D-009**: Object storage or file system for temporary storage of uploaded documents before processing and optionally for archival of original documents. Options: AWS S3, Azure Blob Storage, MinIO, or network file system (NFS).

- **D-010**: Programming language runtime and libraries for RAG orchestration, with preference for Python ecosystem due to rich library support: LangChain or LlamaIndex for RAG primitives, sentence-transformers for embeddings, qdrant-client for vector DB, pika for RabbitMQ, and FastAPI or Flask for service endpoints.

- **D-011**: Guardrails implementation either through: dedicated library (LLM-Guard, NeMo Guardrails, Llama Guard), custom implementation using LLM-based classification, or hybrid approach combining rule-based and model-based checks.

- **D-012**: PII detection and redaction library or service supporting Brazilian data patterns, with capabilities for: CPF format detection, email/phone/credit card pattern matching, named entity recognition (NER) for person names, and configurable redaction policies.

## Scope

### In Scope

- Document ingestion pipeline supporting CSV, PDF, DOCX, and TXT formats
- Asynchronous processing using message queues (RabbitMQ) with separate queues for ingest, embed, query, and audit operations
- Document preprocessing including text extraction, cleaning, language detection, and PII redaction
- Text chunking with configurable size and overlapping windows for context preservation
- Vector embedding generation for chunks with batch processing capabilities
- Vector storage in Qdrant with metadata and collection-based organization
- Retention policies per collection with time-based archival and deletion rules
- Semantic search and retrieval from vector database with metadata filtering
- RAG orchestration coordinating retrieval, ranking, reranking, and generation
- LLM-based answer generation using OpenAI API with prompt templates and few-shot examples
- Request throttling, caching, and rate limit handling for LLM API
- Input validation and guardrails for prompt injection and harmful content detection
- Output validation for hallucination detection, PII leakage prevention, and quality checks
- Confidence scoring for generated answers based on multiple factors
- Automatic escalation to human support for low-confidence or validation-failed queries
- Escalation queue with context and priority scoring for support agents
- Structured logging for all system operations and events
- Metrics collection and exposure for performance, reliability, and quality monitoring
- Distributed tracing across system components for debugging and performance analysis
- Monitoring dashboards for operational visibility (Grafana or equivalent)
- Alerting for metric threshold violations
- Horizontal scalability for worker pools with dynamic scaling
- Support for Olist order reviews dataset as primary data source
- Support for adding additional documents and data sources to the knowledge base

### Out of Scope

- Custom web UI or mobile application for end users (system provides backend APIs and message queue interfaces only; UI is responsibility of consuming applications)
- User authentication and authorization for end-user queries (assumes pre-authenticated access or integration with external auth service; authentication for admin functions is in scope)
- Multi-tenancy with data isolation and tenant-specific configurations (initial version is single-tenant; multi-tenancy can be added in future iterations)
- Real-time collaborative editing or annotation of documents in the knowledge base
- Advanced analytics or business intelligence features beyond question-answering (e.g., trend analysis, predictive modeling, automated report generation)
- Integration with external CRM or ticketing systems for human support escalation workflow (escalation queue is provided, but integration with Zendesk, Salesforce, etc. is out of scope)
- Training, fine-tuning, or customization of language models and embedding models (assumes use of pre-trained models via API or self-hosted deployment)
- Support for multimedia content (images, audio, video) in documents (text-only for initial version)
- Optical character recognition (OCR) for scanned documents or images (assumes text-extractable PDFs and digital documents)
- Version control or change tracking for ingested documents (each ingestion is treated as a new document; versioning can be added later)
- Automated document collection, web scraping, or integration with external data sources (assumes manual upload or API-based ingestion)
- User feedback collection and active learning loop for continuous improvement (feedback mechanism for support agents is in scope, but systematic user feedback and model retraining is out of scope)
- Support for structured queries (SQL-like), graph-based queries, or non-natural-language query interfaces (natural language only)
- Real-time synchronization of document updates (documents are indexed asynchronously; real-time updates require re-ingestion)
- Custom ranking models or reranking algorithms beyond provided RAG orchestrator capabilities
- A/B testing infrastructure for comparing different retrieval or generation strategies
