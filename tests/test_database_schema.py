"""Verify all database tables were created successfully."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect

# Supabase PostgreSQL connection (using pooler)
database_url = "postgresql+psycopg://postgres.bxeyoqsgspfxaxgeckfo:%23%26QS5uH7CC_f-U%21@aws-0-us-west-2.pooler.supabase.com:6543/postgres"

try:
    print("Verifying Supabase database schema...")
    print()

    # Create engine
    engine = create_engine(database_url, pool_pre_ping=True, echo=False)

    # Get inspector to check schema
    inspector = inspect(engine)

    # Expected tables
    expected_tables = [
        'documents',
        'chunks',
        'queries',
        'answers',
        'query_results',
        'escalation_requests',
        'embedding_jobs',
        'audit_events',
        'collections',
        'alembic_version',  # Alembic tracking table
    ]

    # Get actual tables
    actual_tables = inspector.get_table_names()

    print("Tables in database:")
    for table in sorted(actual_tables):
        print(f"  [OK] {table}")
    print()

    # Verify all expected tables exist
    missing_tables = set(expected_tables) - set(actual_tables)
    extra_tables = set(actual_tables) - set(expected_tables)

    if missing_tables:
        print(f"ERROR: Missing tables: {missing_tables}")
    else:
        print("[OK] All expected tables exist!")
    print()

    # Check collections table has default collection
    with engine.connect() as connection:
        result = connection.execute(text("SELECT * FROM collections"))
        collections = result.fetchall()

        print("Collections in database:")
        for coll in collections:
            print(f"  - {coll[0]}: {coll[1]}")
            print(f"    Vector dim: {coll[2]}, Distance: {coll[3]}")
            print(f"    Documents: {coll[4]}, Vectors: {coll[5]}")
        print()

        if any(coll[0] == 'olist_reviews' for coll in collections):
            print("[OK] Default 'olist_reviews' collection created!")
        else:
            print("ERROR: Default collection 'olist_reviews' not found")

    # Check alembic version
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"\n[OK] Alembic migration version: {version}")

    print("\n" + "="*50)
    print("SUCCESS: Database schema verification complete!")
    print("="*50)

except Exception as e:
    print(f"ERROR: Verification failed: {e}")
    import traceback
    traceback.print_exc()
