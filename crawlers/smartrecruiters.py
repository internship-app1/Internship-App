"""
SmartRecruiters ATS crawler.

Endpoint: GET https://api.smartrecruiters.com/v1/companies/{identifier}/postings
Fully public API (no auth). companyIdentifier is an opaque SR account slug — must be
extracted from the company's career page URL, not derived from company name.

Filter by experienceLevel.id == "internship" (more reliable than typeOfEmployment).
Use releasedAfter for incremental crawls.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from crawlers.greenhouse import CompanyNotFound, RateLimitError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.smartrecruiters.com/v1/companies"
RATE_LIMIT_DELAY = 0.2


async def _fetch_detail(client: httpx.AsyncClient, identifier: str, posting_id: str) -> dict:
    """Fetch full job detail including jobAd sections."""
    url = f"{BASE_URL}/{identifier}/postings/{posting_id}"
    try:
        resp = await client.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.debug("SR detail fetch failed %s/%s: %s", identifier, posting_id, e)
    return {}


async def fetch_jobs(company, since_hours: Optional[int] = None) -> List[dict]:
    """
    Fetch all SmartRecruiters intern postings for a company identifier.

    Filters by experienceLevel.id == "internship".
    Fetches job detail for description (jobAd.sections).
    Raises CompanyNotFound on 404, RateLimitError on 429.
    """
    identifier = company.ats_board_id
    params: dict = {
        "q": "intern",
        "limit": 100,
        "offset": 0,
        "destination": "PUBLIC",
    }
    if since_hours is not None:
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        params["releasedAfter"] = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_listings: List[dict] = []

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            for attempt in range(3):
                try:
                    resp = await client.get(f"{BASE_URL}/{identifier}/postings", params=params)
                    break
                except httpx.RequestError as e:
                    logger.warning("SR network error for %s: %s", identifier, e)
                    await asyncio.sleep(2 ** attempt)
            else:
                return all_listings

            if resp.status_code == 404:
                raise CompanyNotFound(f"SmartRecruiters identifier not found: {identifier}")
            if resp.status_code == 429:
                raise RateLimitError(f"SmartRecruiters rate limit for {identifier}")
            if resp.status_code != 200:
                logger.warning("SR %s returned %d — skipping", identifier, resp.status_code)
                return all_listings

            data = resp.json()
            content = data.get("content", [])
            total_found = data.get("totalFound", 0)

            for item in content:
                exp = item.get("experienceLevel", {}) or {}
                if exp.get("id") != "internship":
                    continue
                if item.get("visibility") != "PUBLIC":
                    continue
                all_listings.append(item)

            await asyncio.sleep(RATE_LIMIT_DELAY)

            next_offset = params["offset"] + params["limit"]
            if next_offset >= total_found or not content:
                break
            params["offset"] = next_offset

    if not all_listings:
        return []

    # Fetch detail for each listing to get job description
    async with httpx.AsyncClient(timeout=30) as client:
        detail_tasks = [
            _fetch_detail(client, identifier, item["id"])
            for item in all_listings
        ]
        details = await asyncio.gather(*detail_tasks, return_exceptions=True)

    enriched = []
    for item, detail in zip(all_listings, details):
        if isinstance(detail, dict) and detail:
            item.update(detail)
        item["_title"] = item.get("name", "")
        enriched.append(item)

    return enriched
