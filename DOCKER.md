# Docker Deployment Guide - RAG Q&A System

## Estrutura do Projeto

```
ragFlow/
├── Dockerfile              # Multi-stage build para API e Worker
├── docker-compose.yml      # Orquestração dos serviços
├── .dockerignore          # Arquivos excluídos do build
├── .env                   # Variáveis de ambiente (não versionado)
└── .env.example           # Template de variáveis de ambiente
```

---

## Pré-requisitos

1. **Docker** instalado (>= 20.10)
   ```bash
   docker --version
   ```

2. **Docker Compose** instalado (>= 2.0)
   ```bash
   docker-compose --version
   ```

3. **Arquivo `.env` configurado** (copie do `.env.example`)
   ```bash
   cp .env.example .env
   # Edite .env com suas credenciais
   ```

---

## Comandos Principais

### 1. Build das Imagens

```bash
# Build de todas as imagens
docker-compose build

# Build apenas da API
docker-compose build api

# Build apenas do Worker
docker-compose build query-worker

# Build sem usar cache (rebuild completo)
docker-compose build --no-cache
```

### 2. Iniciar os Serviços

```bash
# Iniciar todos os serviços em background
docker-compose up -d

# Iniciar com logs visíveis
docker-compose up

# Iniciar apenas a API
docker-compose up -d api

# Iniciar apenas o Worker
docker-compose up -d query-worker
```

### 3. Verificar Status

```bash
# Ver containers rodando
docker-compose ps

# Ver logs de todos os serviços
docker-compose logs

# Ver logs da API
docker-compose logs api

# Ver logs do Worker
docker-compose logs query-worker

# Seguir logs em tempo real
docker-compose logs -f api
```

### 4. Parar os Serviços

```bash
# Parar todos os serviços
docker-compose stop

# Parar e remover containers
docker-compose down

# Parar, remover containers e volumes
docker-compose down -v

# Parar, remover tudo incluindo imagens
docker-compose down --rmi all
```

### 5. Restart de Serviços

```bash
# Restart de todos os serviços
docker-compose restart

# Restart apenas da API
docker-compose restart api

# Restart apenas do Worker
docker-compose restart query-worker
```

---

## Workflow Completo - Primeira Execução

```bash
# 1. Clonar o repositório
git clone https://github.com/mfnogueira/ragflow.git
cd ragflow

# 2. Configurar variáveis de ambiente
cp .env.example .env
nano .env  # ou vim, code, etc.

# 3. Build das imagens
docker-compose build

# 4. Iniciar os serviços
docker-compose up -d

# 5. Verificar se os serviços estão rodando
docker-compose ps

# 6. Ver logs
docker-compose logs -f

# 7. Testar a API
curl http://localhost:8000/health
```

---

## Testes e Validação

### 1. Health Check
```bash
# API Health
curl http://localhost:8000/health

# Readiness
curl http://localhost:8000/health/ready

# Liveness
curl http://localhost:8000/health/live
```

### 2. Enviar Query de Teste
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quais são os principais problemas relatados?"
  }'
```

### 3. Consultar Resultado
```bash
# Substitua QUERY_ID pelo ID retornado no passo anterior
curl http://localhost:8000/query/QUERY_ID
```

---

## Troubleshooting

### Problema: Container não inicia

**Diagnóstico:**
```bash
# Ver logs de erro
docker-compose logs api
docker-compose logs query-worker

# Inspecionar container
docker-compose ps
docker inspect ragflow-api
```

**Soluções comuns:**
1. Verificar se `.env` está configurado corretamente
2. Verificar se as portas 8000 não estão em uso
3. Verificar conexão com serviços externos (PostgreSQL, RabbitMQ, Qdrant)

### Problema: Erro de conexão com banco de dados

```bash
# Verificar logs
docker-compose logs api | grep -i database

# Testar conexão manualmente
docker-compose exec api python -c "
from src.lib.config import settings
from src.lib.database import get_db
print(settings.database_url)
"
```

### Problema: Worker não processa queries

```bash
# Verificar logs do worker
docker-compose logs query-worker

# Verificar se RabbitMQ está acessível
docker-compose exec query-worker python -c "
import pika
from src.lib.config import settings
connection = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
print('RabbitMQ OK')
"
```

### Problema: Porta 8000 já em uso

```bash
# Encontrar processo usando a porta
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Alterar porta no docker-compose.yml
# Mude de "8000:8000" para "8001:8000"
```

---

## Variáveis de Ambiente Importantes

Edite o arquivo `.env` com as seguintes variáveis:

```bash
# Ambiente
ENVIRONMENT=production
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql+psycopg://user:pass@host:port/db

# RabbitMQ (CloudAMQP)
RABBITMQ_URL=amqps://user:pass@host/vhost
RABBITMQ_PREFETCH_COUNT=5

# Qdrant Vector Database
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-api-key

# OpenAI
OPENAI_API_KEY=sk-proj-your-key-here
OPENAI_LLM_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# RAG Config
DEFAULT_COLLECTION=olist_reviews
MAX_CHUNKS_PER_QUERY=10
CONFIDENCE_THRESHOLD=0.7
QUERY_CONCURRENCY=10
```

---

## Comandos Úteis de Debug

```bash
# Entrar no container da API
docker-compose exec api bash

# Entrar no container do Worker
docker-compose exec query-worker bash

# Ver uso de recursos
docker stats

# Ver logs em tempo real de todos os serviços
docker-compose logs -f --tail=100

# Rebuild forçado após mudanças no código
docker-compose up -d --build

# Limpar recursos não utilizados
docker system prune -a
```

---

## Deployment em Produção

### 1. Build para Produção
```bash
# Definir ambiente como production no .env
ENVIRONMENT=production

# Build otimizado
docker-compose build --no-cache
```

### 2. Configurações de Segurança
- Não exponha portas desnecessárias
- Use secrets do Docker para credenciais sensíveis
- Configure HTTPS/TLS
- Use usuário não-root (já configurado no Dockerfile)
- Habilite health checks (já configurado)

### 3. Monitoramento
```bash
# Métricas Prometheus
curl http://localhost:8000/health/metrics

# Status dos containers
docker-compose ps

# Logs agregados
docker-compose logs --since 1h
```

---

## Escalonamento

Para escalar o número de workers:

```bash
# Escalar para 3 workers
docker-compose up -d --scale query-worker=3

# Verificar workers rodando
docker-compose ps
```

---

## Atualização de Código

```bash
# 1. Pull das mudanças
git pull origin main

# 2. Rebuild e restart
docker-compose up -d --build

# 3. Verificar logs
docker-compose logs -f
```

---

## Limpeza e Manutenção

```bash
# Parar e remover tudo
docker-compose down -v

# Limpar imagens não utilizadas
docker image prune -a

# Limpar volumes não utilizados
docker volume prune

# Limpar tudo (cuidado em produção!)
docker system prune -a --volumes
```

---

## Links Úteis

- **API Swagger Docs**: http://localhost:8000/docs
- **API ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health
- **Exemplos de API**: Ver `API_EXAMPLES.md`

---

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs: `docker-compose logs`
2. Consulte o troubleshooting acima
3. Abra uma issue no GitHub
