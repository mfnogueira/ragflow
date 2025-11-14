"""Add missing columns to queries table."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lib.database import get_db
from sqlalchemy import text

print("Adding missing columns to queries table...")

db = next(get_db())
try:
    # Add completed_at column
    db.execute(text("ALTER TABLE queries ADD COLUMN IF NOT EXISTS completed_at TIMESTAMP"))
    print("[OK] completed_at column added/checked")

    # Add metadata column
    db.execute(text("ALTER TABLE queries ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'"))
    print("[OK] metadata column added/checked")

    db.commit()
    print("\n[SUCCESS] All columns added successfully!")

except Exception as e:
    print(f"\n[ERROR] {e}")
    db.rollback()
finally:
    db.close()
