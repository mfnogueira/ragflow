"""Test Supabase REST API connectivity."""

import requests

# Supabase details
supabase_url = "https://bxeyoqsgspfxaxgeckfo.supabase.co"
anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJ4ZXlvcXNnc3BmeGF4Z2Vja2ZvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMxMjUxMTksImV4cCI6MjA3ODcwMTExOX0.bZCBqT-zG7CmTvs_Y7wDX0pUjI7W3PjKZthARH43sFE"

try:
    print("Testing Supabase REST API connectivity...")
    print(f"URL: {supabase_url}")
    print()

    # Test REST API endpoint
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
    }

    # Try to access the REST API
    response = requests.get(
        f"{supabase_url}/rest/v1/",
        headers=headers,
        timeout=10,
    )

    print(f"Status Code: {response.status_code}")

    if response.status_code == 200:
        print("SUCCESS: Supabase REST API is accessible!")
        print()
        print("Project is active and responding.")
        print()
        print("Note: PostgreSQL direct connection may need:")
        print("  1. Check Supabase dashboard for exact connection string")
        print("  2. Use connection pooling URL instead of direct")
        print("  3. Verify your IP is allowed (check Supabase Network settings)")
    else:
        print(f"Response: {response.text}")

except requests.exceptions.Timeout:
    print("ERROR: Request timed out")
    print("Project may not be active yet")

except requests.exceptions.ConnectionError as e:
    print(f"ERROR: Connection failed: {e}")
    print()
    print("Possible issues:")
    print("  - Project may not be active")
    print("  - Check project URL is correct")
    print("  - Verify internet connection")

except Exception as e:
    print(f"ERROR: {e}")
