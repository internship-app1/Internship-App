"""
Lever ATS crawler.

Endpoint: GET https://api.lever.co/v0/postings/{slug}?mode=json&limit=100
Note: title field is 'text', not 'title'. Location/commitment/team nested in 'categories'.
EU companies use api.eu.lever.co.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from crawlers.greenhouse import CompanyNotFound, RateLimitError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lever.co/v0/postings"
EU_BASE_URL = "https://api.eu.lever.co/v0/postings"
RATE_LIMIT_DELAY = 0.2


async def fetch_jobs(company, since_hours: Optional[int] = None) -> List[dict]:
    """
    Fetch all Lever postings for a company slug.

    Title is at raw['text']; location/commitment at raw['categories']['location'/'commitment'].
    Handles EU tenants and pagination (skip/limit).
    Raises CompanyNotFound on 404, RateLimitError on 429.
    """
    slug = company.ats_board_id
    base = EU_BASE_URL if getattr(company, "is_eu", False) else BASE_URL

    since_ms: Optional[int] = None
    if since_hours is not None:
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        since_ms = int(cutoff.timestamp() * 1000)

    all_jobs: List[dict] = []
    skip = 0
    limit = 100

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {"mode": "json", "skip": skip, "limit": limit}
            for attempt in range(3):
                try:
                    resp = await client.get(f"{base}/{slug}", params=params)
                    break
                except httpx.RequestError as e:
                    logger.warning("Lever network error for %s: %s", slug, e)
                    await asyncio.sleep(2 ** attempt)
            else:
                return all_jobs

            if resp.status_code == 404:
                raise CompanyNotFound(f"Lever slug not found: {slug}")
            if resp.status_code == 429:
                raise RateLimitError(f"Lever rate limit for {slug}")
            if resp.status_code != 200:
                logger.warning("Lever %s returned %d — skipping", slug, resp.status_code)
                return all_jobs

            page = resp.json()
            if not isinstance(page, list):
                break

            for j in page:
                if j.get("state") != "published":
                    continue
                dist = j.get("distributionChannels", [])
                if dist and "public" not in dist:
                    continue
                if since_ms is not None:
                    updated_at = j.get("updatedAt") or j.get("createdAt", 0)
                    if updated_at and updated_at < since_ms:
                        continue
                j["_title"] = j.get("text", "")
                all_jobs.append(j)

            await asyncio.sleep(RATE_LIMIT_DELAY)

            if len(page) < limit:
                break
            skip += limit

    return all_jobs
