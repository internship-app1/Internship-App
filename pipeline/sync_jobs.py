"""
Hourly GitHub Actions pipeline: triggers an incremental job sync
via the production API. Auth via X-API-Key header.
"""
import os
import sys
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_URL = os.environ.get("API_URL", "https://internshipmatcher.com")
API_KEY = os.environ.get("CACHE_REFRESH_API_KEY")

if not API_KEY:
    print("ERROR: CACHE_REFRESH_API_KEY must be set", file=sys.stderr)
    sys.exit(1)

resp = requests.post(
    f"{API_URL}/api/refresh-cache-incremental",
    headers={"X-API-Key": API_KEY},
    timeout=120,
)
resp.raise_for_status()
data = resp.json()
print(f"Done: {data.get('new_jobs', 0)} new | {data.get('total_processed', 0)} processed")
