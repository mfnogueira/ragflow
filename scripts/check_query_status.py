"""Check the status of a query."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.test_query_worker import check_query_status

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_query_status.py <query_id>")
        sys.exit(1)

    query_id = sys.argv[1]
    check_query_status(query_id)
