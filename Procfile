# Procfile for running RagFlow workers and API locally with honcho
# Usage: honcho start
# Or run individually: honcho start api, honcho start query_worker, etc.

api: uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
query_worker: python -m src.workers.query_worker
embed_worker: python -m src.workers.embed_worker
ingest_worker: python -m src.workers.ingest_worker
