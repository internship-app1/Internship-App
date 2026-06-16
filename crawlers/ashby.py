"""
Ashby ATS crawler.

Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{org_slug}
One request returns all jobs with full description — very efficient.

Note: api.ashbyhq.com is the correct base (jobs.ashbyhq.com/api/non-user-facing/ returns 404).
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from crawlers.greenhouse import CompanyNotFound, RateLimitError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"
RATE_LIMIT_DELAY = 0.3


async def fetch_jobs(company, since_hours: Optional[int] = None) -> List[dict]:
    """
    Fetch all Ashby job board postings for an org slug.

    Full description is included in the list response — no N+1 detail requests.
    Raises CompanyNotFound on 404, RateLimitError on 429.
    """
    slug = company.ats_board_id
    url = f"{BASE_URL}/{slug}"
    params = {"includeCompensation": "true"}

    since_dt: Optional[datetime] = None
    if since_hours is not None:
        since_dt = datetime.utcnow() - timedelta(hours=since_hours)

    async with httpx.AsyncClient(timeout=30) as client:
        for attempt in range(3):
            try:
                resp = await client.get(url, params=params)
            except httpx.RequestError as e:
                logger.warning("Ashby network error for %s: %s", slug, e)
                await asyncio.sleep(2 ** attempt)
                continue

            if resp.status_code == 404:
                raise CompanyNotFound(f"Ashby org not found: {slug}")
            if resp.status_code == 429:
                raise RateLimitError(f"Ashby rate limit for {slug}")
            if resp.status_code != 200:
                logger.warning("Ashby %s returned %d — skipping", slug, resp.status_code)
                return []

            data = resp.json()
            jobs = data.get("jobs", [])

            result = []
            for j in jobs:
                if not j.get("isListed", True):
                    continue
                if since_dt is not None:
                    published_raw = j.get("publishedAt", "")
                    if published_raw:
                        try:
                            published = datetime.fromisoformat(
                                published_raw.replace("Z", "+00:00")
                            ).replace(tzinfo=None)
                            if published < since_dt:
                                continue
                        except Exception:
                            pass
                j["_title"] = j.get("title", "")
                result.append(j)

            await asyncio.sleep(RATE_LIMIT_DELAY)
            return result

    return []
