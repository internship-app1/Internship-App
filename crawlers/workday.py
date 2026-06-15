"""
Workday ATS crawler.

No documented public API — all tenants follow the same URL/request pattern.

Key notes:
- Tenant URL pattern: https://{company}.{wdN}.myworkdayjobs.com/wday/cxs/{company}/{site}/jobs
- wdN is data-center specific (wd5/wd1/wd3/wd12/wd103) — probe in that order
- Use searchText="intern" only; do NOT hardcode workerSubType UUIDs (tenant-specific)
- HTTP 422 = Cloudflare bot protection (enterprise tenants like Amazon/Microsoft) — skip these
- 10,000 result hard cap per query
- -impl suffix on subdomain = staging — skip
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta
from typing import List, Optional

import httpx

from crawlers.greenhouse import CompanyNotFound, RateLimitError

logger = logging.getLogger(__name__)

WD_CLUSTERS = ["wd5", "wd1", "wd3", "wd12", "wd103"]
COMMON_SITES = ["External_Career_Site", "Careers", "External", "Evergreen_Careers"]
RATE_LIMIT_DELAY = 0.5

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


async def _discover_tenant_url(client: httpx.AsyncClient, company: str) -> Optional[str]:
    """
    Probe wdN clusters × common site slugs to discover a valid tenant URL.
    Returns the first URL that responds 200 to a minimal POST, or None.
    """
    for wdn in WD_CLUSTERS:
        for site in COMMON_SITES:
            url = (
                f"https://{company}.{wdn}.myworkdayjobs.com"
                f"/wday/cxs/{company}/{site}/jobs"
            )
            try:
                resp = await client.post(
                    url,
                    json={"limit": 1, "offset": 0, "searchText": ""},
                    headers={"User-Agent": BROWSER_UA, "Content-Type": "application/json"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    return url
                if resp.status_code == 422:
                    logger.debug("Workday %s: 422 (Cloudflare) on %s — marking cloudflare_protected", company, url)
                    return None
            except httpx.RequestError:
                continue
    return None


async def fetch_jobs(company, since_hours: Optional[int] = None) -> List[dict]:
    """
    Fetch all intern jobs from a Workday tenant.

    Returns raw job dicts with '_title' and '_apply_link' keys set.
    Raises CompanyNotFound if no valid tenant URL found.
    On 422 (Cloudflare protection) marks the company and returns empty.
    """
    board_id = company.ats_board_id
    if board_id.endswith("-impl"):
        return []

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        tenant_url = await _discover_tenant_url(client, board_id)
        if tenant_url is None:
            logger.info("Workday: no tenant URL found for %s — skipping", board_id)
            return []

        all_jobs: List[dict] = []
        offset = 0
        limit = 20
        total = None

        while True:
            try:
                resp = await client.post(
                    tenant_url,
                    json={"appliedFacets": {}, "limit": limit, "offset": offset, "searchText": "intern"},
                    headers={"User-Agent": BROWSER_UA, "Content-Type": "application/json"},
                )
            except httpx.RequestError as e:
                logger.warning("Workday network error for %s: %s", board_id, e)
                break

            if resp.status_code == 422:
                logger.info("Workday 422 for %s — Cloudflare protected, skipping", board_id)
                return []
            if resp.status_code == 429:
                raise RateLimitError(f"Workday rate limit for {board_id}")
            if resp.status_code != 200:
                logger.warning("Workday %s returned %d", board_id, resp.status_code)
                break

            data = resp.json()
            if total is None:
                total = data.get("total", 0)

            postings = data.get("jobPostings", [])
            for p in postings:
                p["_title"] = p.get("title", "")
                external_path = p.get("externalPath", "")
                base_host = tenant_url.split("/wday/")[0]
                p["_apply_link"] = f"{base_host}{external_path}"
            all_jobs.extend(postings)

            await asyncio.sleep(RATE_LIMIT_DELAY)

            offset += limit
            if offset >= total or offset >= 10000 or not postings:
                break

        return all_jobs
