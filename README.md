# RagFlow - Sistema de Perguntas e Respostas baseado em RAG

Um sistema de Retrieval-Augmented Generation (RAG) para responder perguntas sobre reviews de pedidos da Olist usando IA.

## 🎯 Visão Geral

O RagFlow permite fazer perguntas em linguagem natural sobre reviews de e-commerce e receber respostas geradas por IA com evidências de suporte. O sistema processa documentos em embeddings vetoriais e usa o LLM da OpenAI para gerar respostas contextuais e precisas.

**Funcionalidades Implementadas**:
- 📄 Processamento de documentos (chunking e tokenização)
- 🔍 Busca semântica usando embeddings vetoriais (Qdrant Cloud)
- 🤖 Geração de respostas com GPT-4o-mini
- 🛡️ Guardrails para validação de entrada
- ⚡ Processamento assíncrono com RabbitMQ
- 📊 API REST completa com FastAPI
- 🔐 Armazenamento seguro com Supabase PostgreSQL

## 🚀 Início Rápido

### Opção 1: Docker (Recomendado) 🐳

**Pré-requisitos**: Docker e Docker Compose

```bash
# Clone o repositório
git clone https://github.com/mfnogueira/ragflow.git
cd ragflow
git checkout 001-rag-qa-system

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# Construa e inicie os containers
docker-compose up --build -d

# Verifique os logs
docker-compose logs -f
```

A API estará disponível em: http://localhost:8000

### Opção 2: Instalação Local

**Pré-requisitos**: Python 3.11+

```bash
# Clone e configuração
git clone https://github.com/mfnogueira/ragflow.git
cd ragflow
git checkout 001-rag-qa-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas credenciais

# Execute migrations do banco de dados
alembic upgrade head

# Inicie a API
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

### Variáveis de Ambiente Necessárias

Edite o arquivo `.env` e configure:
- `OPENAI_API_KEY` - Sua chave da OpenAI
- `DATABASE_URL` - URL do banco Supabase PostgreSQL
- `RABBITMQ_URL` - URL do RabbitMQ (CloudAMQP)
- `QDRANT_URL` e `QDRANT_API_KEY` - Credenciais do Qdrant Cloud

### Testar a API

```bash
# Health check
curl http://localhost:8000/health/

# Opção 1: Query SÍNCRONA (resposta imediata, aguarda processamento)
# Recomendado para integrações que esperam resposta direta
curl --location 'http://localhost:8000/api/v1/query/sync' \
  --header 'Content-Type: application/json' \
  --data '{
    "question": "Quais são os principais problemas nos reviews?"
  }'

# Opção 2: Query ASSÍNCRONA (aceita query, processa em background)
# Recomendado para batch processing ou alta concorrência
curl --location 'http://localhost:8000/api/v1/query/async' \
  --header 'Content-Type: application/json' \
  --data '{
    "question": "Quais são os principais motivos de avaliações negativas?"
  }'

# Verificar resultado da query assíncrona (substitua {query_id} pelo ID retornado)
curl http://localhost:8000/api/v1/query/{query_id}
```

**Exemplo de resposta `/query/sync` (200 OK):**
```json
{
  "query_id": "c4ed148a-90af-4f43-b33a-6ca887824516",
  "question": "Quais são os principais problemas nos reviews?",
  "status": "completed",
  "answer": "Os principais problemas destacados nas avaliações incluem:\n\n1. **Problemas na entrega**: Avaliações na categoria móveis mencionam atrasos significativos na entrega...",
  "confidence_score": 0.576,
  "sources": [
    {
      "chunk_id": "30a0c86d-9cad-450d-ac5d-ce961a75ca2f",
      "similarity_score": 0.432,
      "rank": 1
    }
  ],
  "created_at": "2025-11-20T17:08:37.126177+00:00",
  "completed_at": "2025-11-20T17:08:58.238159"
}
```

**Exemplo de resposta `/query/async` (202 Accepted):**
```json
{
  "query_id": "583db1ab-69f9-44e5-b2ef-840d86ad9aed",
  "status": "accepted",
  "message": "Query accepted for processing. Use GET /api/v1/query/{id} to check status."
}
```

## 🏗️ Arquitetura

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Usuário   │─────▶│  FastAPI    │─────▶│  Supabase   │
│             │      │    API      │      │ PostgreSQL  │
└─────────────┘      └──────┬──────┘      └─────────────┘
                            │
                            ▼
                     ┌─────────────┐      ┌─────────────┐
                     │  RabbitMQ   │─────▶│   Workers   │
                     │ (CloudAMQP) │      │    Query    │
                     └─────────────┘      └──────┬──────┘
                                                 │
                                                 ▼
                     ┌─────────────┐      ┌─────────────┐
                     │   Qdrant    │◀─────│   OpenAI    │
                     │   Cloud     │      │   API       │
                     └─────────────┘      └─────────────┘
```

**Stack Tecnológica**:
- **Python 3.11+** - Linguagem de programação
- **FastAPI** - Framework web para API REST
- **OpenAI API** - LLM (GPT-4o-mini) e Embeddings (text-embedding-3-small)
- **Qdrant Cloud** - Banco de dados vetorial para busca semântica
- **Supabase** - PostgreSQL gerenciado na nuvem
- **CloudAMQP** - RabbitMQ gerenciado para filas de mensagens
- **SQLAlchemy** - ORM para acesso ao banco de dados
- **Pydantic** - Validação de dados e configuração
- **Alembic** - Migrations de banco de dados
- **Docker** - Containerização da aplicação

## 🐳 Docker

O projeto utiliza Docker para containerização, facilitando o deployment e garantindo consistência entre ambientes.

### Dockerfile Multi-Stage

O `Dockerfile` usa uma build multi-stage para otimizar o tamanho da imagem:

1. **Stage 1 (Builder)**: Instala dependências de build e pacotes Python
2. **Stage 2 (Runtime)**: Cria imagem mínima de produção
   - Copia apenas dependências necessárias
   - Cria usuário não-root para segurança
   - Expõe porta 8000

### Docker Compose

O `docker-compose.yml` orquestra dois serviços:

**Serviço `api`**:
- Container: `ragflow-api`
- Porta: `8000:8000`
- Comando: `uvicorn src.api.app:app --host 0.0.0.0 --port 8000`
- Healthcheck: Verifica `/health` a cada 30s

**Serviço `query-worker`**:
- Container: `ragflow-query-worker`
- Processa queries da fila RabbitMQ
- Comando: `python -m src.workers.query_worker`
- Escala: Configurável via `QUERY_CONCURRENCY`

### Comandos Docker Úteis

```bash
# Construir e iniciar
docker-compose up --build -d

# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f api
docker-compose logs -f query-worker

# Parar containers
docker-compose down

# Parar e remover volumes
docker-compose down -v

# Reconstruir imagens
docker-compose build --no-cache

# Verificar status dos containers
docker-compose ps

# Entrar no container da API
docker-compose exec api bash

# Ver uso de recursos
docker stats
```

## 📁 Estrutura do Projeto

```
ragFlow/
├── src/
│   ├── api/              # API REST (FastAPI)
│   │   ├── app.py        # Aplicação principal
│   │   └── routes/       # Endpoints organizados
│   ├── lib/              # Bibliotecas compartilhadas
│   │   ├── config.py     # Configurações (Pydantic Settings)
│   │   ├── database.py   # Conexão PostgreSQL
│   │   ├── queue.py      # Conexão RabbitMQ
│   │   ├── vector_db.py  # Cliente Qdrant
│   │   └── logger.py     # Logging estruturado
│   ├── models/           # Modelos Pydantic e ORM
│   │   ├── orm.py        # Modelos SQLAlchemy
│   │   ├── document.py   # Schemas de documentos
│   │   └── query.py      # Schemas de queries
│   ├── repositories/     # Camada de acesso a dados
│   │   ├── document_repo.py
│   │   ├── query_repo.py
│   │   └── vector_repo.py
│   ├── services/         # Lógica de negócio
│   │   ├── guardrails_service.py
│   │   ├── embedding_service.py
│   │   ├── retrieval_service.py
│   │   └── generation_service.py
│   └── workers/          # Workers assíncronos
│       ├── base_worker.py
│       └── query_worker.py
├── alembic/              # Migrations do banco
├── scripts/              # Scripts utilitários
├── data/                 # Dados de teste
└── .env                  # Configurações (não versionado)
```

## 🛠️ API Endpoints

### Health & Metrics
- `GET /health/` - Health check básico
- `GET /health/ready` - Readiness probe (verifica DB + RabbitMQ)
- `GET /health/live` - Liveness probe
- `GET /health/metrics` - Métricas do sistema

### Queries
- `POST /api/v1/query/sync` - Query síncrona (retorna resposta completa)
- `POST /api/v1/query/async` - Query assíncrona (usa workers, requer polling)
- `GET /api/v1/query/{id}` - Status e resultado da query
- `GET /api/v1/queries` - Listar queries

### Documentos
- `POST /api/v1/documents` - Criar documento
- `POST /api/v1/documents/upload` - Upload de arquivo
- `GET /api/v1/documents` - Listar documentos
- `GET /api/v1/documents/{id}` - Detalhes do documento
- `GET /api/v1/documents/{id}/chunks` - Chunks do documento
- `DELETE /api/v1/documents/{id}` - Deletar documento

### Coleções
- `GET /api/v1/collections` - Listar coleções
- `POST /api/v1/collections` - Criar coleção
- `GET /api/v1/collections/{name}` - Detalhes da coleção
- `GET /api/v1/collections/{name}/stats` - Estatísticas
- `DELETE /api/v1/collections/{name}` - Deletar coleção

**Documentação interativa**: http://localhost:8000/docs (Swagger UI)

## 📊 Serviços Externos Utilizados

### Supabase (PostgreSQL)
- Banco de dados relacional gerenciado
- Armazena documentos, chunks, queries e resultados
- 9 tabelas criadas via Alembic migrations

### Qdrant Cloud
- Banco de dados vetorial para busca semântica
- Armazena embeddings de 1536 dimensões
- Métrica de distância: Cosine Similarity

### CloudAMQP (RabbitMQ)
- Fila de mensagens gerenciada
- Processamento assíncrono de queries
- Fila principal: `queries`

### OpenAI API
- **Embeddings**: text-embedding-3-small (1536 dims)
- **LLM**: gpt-4o-mini
- Rate limiting: 3 requisições/min (tier free)

## 🧪 Testes

### Testar Endpoints da API

```bash
# 1. Health check básico
curl http://localhost:8000/health/

# 2. Health check com verificação de dependências
curl http://localhost:8000/health/ready

# 3. Ver métricas do sistema
curl http://localhost:8000/health/metrics

# 4. Listar coleções disponíveis
curl http://localhost:8000/api/v1/collections

# 5. Submeter query assíncrona (RAG completo)
curl --location 'http://localhost:8000/api/v1/query/async' \
  --header 'Content-Type: application/json' \
  --data '{
    "question": "Quais são os principais motivos de avaliações negativas?"
  }'

# Resposta esperada:
# {
#   "query_id": "abc-123-...",
#   "status": "accepted",
#   "message": "Query accepted for processing. Use GET /api/v1/query/{id} to check status."
# }

# 6. Consultar resultado da query (aguarde ~30-60 segundos)
curl http://localhost:8000/api/v1/query/{query_id}

# 7. Listar queries recentes
curl http://localhost:8000/api/v1/queries?limit=5
```

### Testes com Scripts Python

```bash
# Testar endpoint síncrono
python tests/test_sync_endpoint.py

# Testar todos os serviços async
python tests/test_async_validation.py

# Testar conexão com banco
python tests/test_database_schema.py

# Verificar implementação
python scripts/check_implementation.py
```

## 📊 Dados de Teste

O projeto inclui 30 reviews da Olist em português:
- 30 documentos no PostgreSQL
- 30 chunks processados
- 30 embeddings no Qdrant Cloud (quando ativado)

## 🤝 Contribuindo

1. Criar branch de feature: `git checkout -b feature/sua-feature`
2. Fazer alterações
3. Testar localmente
4. Commit: `git commit -m "feat: adiciona funcionalidade X"`
5. Push: `git push origin feature/sua-feature`
6. Criar pull request

## 📝 Licença

MIT License - veja o arquivo [LICENSE](LICENSE) para detalhes

---

## ⭐ Apoie o Projeto

Se este projeto foi útil para você, considere dar uma estrela no repositório!

👉 **https://github.com/mfnogueira/ragflow.git**

Sua estrela ajuda outros desenvolvedores a descobrir este projeto e motiva o desenvolvimento contínuo.

---

**Desenvolvido com ❤️ usando Python, FastAPI e OpenAI**
