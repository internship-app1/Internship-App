"""
Greenhouse ATS crawler.

Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
One request per company returns all jobs including full description.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from crawlers.normalizer import is_intern_posting

logger = logging.getLogger(__name__)

BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
RATE_LIMIT_DELAY = 0.2


class CompanyNotFound(Exception):
    pass


class RateLimitError(Exception):
    pass


async def fetch_jobs(company, since_hours: Optional[int] = None) -> List[dict]:
    """
    Fetch all intern jobs for a Greenhouse company.

    Returns a list of raw dicts with a '_title' convenience key set.
    Raises CompanyNotFound on 404, RateLimitError on 429.
    """
    token = company.ats_board_id
    url = f"{BASE_URL}/{token}/jobs"
    params = {"content": "true"}

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, params=params)
            except httpx.RequestError as e:
                logger.warning("Greenhouse network error for %s: %s", token, e)
                await asyncio.sleep(2 ** attempt)
                continue

            if resp.status_code == 404:
                raise CompanyNotFound(f"Greenhouse board not found: {token}")
            if resp.status_code == 429:
                raise RateLimitError(f"Greenhouse rate limit for {token}")
            if resp.status_code != 200:
                logger.warning("Greenhouse %s returned %d — skipping", token, resp.status_code)
                return []

            data = resp.json()
            jobs = data.get("jobs", [])

            if since_hours is not None:
                cutoff = datetime.utcnow() - timedelta(hours=since_hours)
                filtered = []
                for j in jobs:
                    updated_raw = j.get("updated_at", "")
                    try:
                        updated = datetime.fromisoformat(updated_raw.replace("Z", "+00:00")).replace(tzinfo=None)
                        if updated >= cutoff:
                            filtered.append(j)
                    except Exception:
                        filtered.append(j)
                jobs = filtered

            for j in jobs:
                j["_title"] = j.get("title", "")

            await asyncio.sleep(RATE_LIMIT_DELAY)
            return jobs

    return []
