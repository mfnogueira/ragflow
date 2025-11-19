"""Ver queries que falharam e os motivos."""
import sys
import logging
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Disable SQLAlchemy logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from sqlalchemy import text
from src.lib.database import get_db

db = next(get_db())

# Buscar queries failed com suas mensagens de erro
result = db.execute(text("""
    SELECT id, query_text, status, metadata
    FROM queries
    WHERE status = 'failed'
    ORDER BY submitted_at DESC
    LIMIT 5
"""))

queries = result.fetchall()

print("\nQUERIES QUE FALHARAM:\n")
for idx, (qid, qtext, status, metadata) in enumerate(queries, 1):
    qid_str = str(qid)
    print(f"{idx}. ID: {qid_str[:8]}...")
    print(f"   Pergunta: {qtext[:80]}")
    print(f"   Status: {status}")
    if metadata:
        print(f"   Metadata: {metadata}")
    print()

# Verificar se há queries pending
result2 = db.execute(text("""
    SELECT id, query_text, submitted_at
    FROM queries
    WHERE status = 'pending'
    ORDER BY submitted_at DESC
"""))

pending = result2.fetchall()

if pending:
    print(f"\nQUERIES PENDENTES: {len(pending)}\n")
    for idx, (qid, qtext, submitted) in enumerate(pending, 1):
        qid_str = str(qid)
        print(f"{idx}. ID: {qid_str[:8]}... | {qtext[:60]}...")
        print(f"   Enviado: {submitted}")
        print()

db.close()
