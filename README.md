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

**Pré-requisitos**: Python 3.11+

### 1. Clone e Configuração

```bash
git clone https://github.com/mfnogueira/ragflow.git
cd ragflow
git checkout 001-rag-qa-system
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` e configure:
- `OPENAI_API_KEY` - Sua chave da OpenAI
- `SUPABASE_DATABASE_URL` - URL do banco Supabase
- `CLOUDAMQP_URL` - URL do RabbitMQ (CloudAMQP)
- `QDRANT_URL` e `QDRANT_API_KEY` - Credenciais do Qdrant Cloud

### 3. Executar Migrations do Banco de Dados

```bash
alembic upgrade head
```

### 4. Iniciar a API

```bash
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: http://localhost:8000

### 5. Testar os Endpoints

```bash
# Health check
curl http://localhost:8000/health/

# Listar coleções
curl http://localhost:8000/api/v1/collections

# Submeter query assíncrona
curl -X POST http://localhost:8000/api/v1/query/async \
  -H "Content-Type: application/json" \
  -d '{"question": "Quais são os principais motivos de avaliações negativas?"}'
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
- `POST /api/v1/query` - Query síncrona
- `POST /api/v1/query/async` - Query assíncrona (usa workers)
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

```bash
# Verificar implementação
python scripts/check_implementation.py

# Testar conexão com banco
python tests/test_database_schema.py

# Testar endpoints da API (requer servidor rodando)
curl http://localhost:8000/health/ready
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
