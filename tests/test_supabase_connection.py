"""Test script to verify Supabase PostgreSQL connection."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

# Supabase PostgreSQL connection (using pooler)
# User: postgres.bxeyoqsgspfxaxgeckfo
# Host: aws-0-us-west-2.pooler.supabase.com
# Port: 6543 (pooler)
# Password URL-encoded: #&QS5uH7CC_f-U! -> %23%26QS5uH7CC_f-U%21
database_url = "postgresql+psycopg://postgres.bxeyoqsgspfxaxgeckfo:%23%26QS5uH7CC_f-U%21@aws-0-us-west-2.pooler.supabase.com:6543/postgres"

try:
    print("Testing Supabase PostgreSQL connection...")
    print("Project: ragFlow")
    print("Host: aws-0-us-west-2.pooler.supabase.com (pooler)")
    print("Port: 6543")
    print()

    # Create engine
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        echo=False,
    )

    # Test connection
    with engine.connect() as connection:
        # Run a simple query
        result = connection.execute(text("SELECT version()"))
        version = result.scalar()

        print("SUCCESS: Connected to Supabase PostgreSQL!")
        print(f"PostgreSQL Version: {version}")
        print()

        # Check current database
        result = connection.execute(text("SELECT current_database()"))
        db_name = result.scalar()
        print(f"Current Database: {db_name}")

        # Check if we can create a test table
        print()
        print("Testing table creation...")
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS connection_test (
                id SERIAL PRIMARY KEY,
                test_value TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        connection.commit()
        print("SUCCESS: Test table created")

        # Insert test data
        connection.execute(text("""
            INSERT INTO connection_test (test_value)
            VALUES ('Connection test from Python')
        """))
        connection.commit()
        print("SUCCESS: Test data inserted")

        # Query test data
        result = connection.execute(text("""
            SELECT test_value, created_at
            FROM connection_test
            ORDER BY created_at DESC
            LIMIT 1
        """))
        row = result.fetchone()
        print(f"SUCCESS: Retrieved data: {row[0]}")

        # Clean up test table
        connection.execute(text("DROP TABLE IF EXISTS connection_test"))
        connection.commit()
        print("SUCCESS: Test table cleaned up")

    print()
    print("All Supabase PostgreSQL tests passed!")

except Exception as e:
    print(f"ERROR: Connection failed: {e}")
    print()
    print("Possible issues:")
    print("  - Check if password is correct")
    print("  - Verify Supabase project is active")
    print("  - Check network connectivity")
    print("  - Ensure database allows connections from your IP")
