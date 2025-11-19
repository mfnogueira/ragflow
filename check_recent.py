"""Check recent queries."""
from sqlalchemy import create_engine, text
from src.lib.config import settings

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT id, query_text, status, submitted_at "
        "FROM queries ORDER BY submitted_at DESC LIMIT 5"
    ))

    print("\nRecent Queries:")
    print("="*100)
    for row in result:
        query_text = row.query_text[:60] + "..." if len(row.query_text) > 60 else row.query_text
        print(f"{row.id} | {row.status:12} | {query_text}")
    print("="*100)
