"""
Bootstrap script — seeds company_registry from curated community datasets.

Sources (all public, no auth required):
  Greenhouse: https://raw.githubusercontent.com/tramcar/greenhouse-tokens/main/tokens.txt
  Lever:      https://raw.githubusercontent.com/nicholasgriffen/lever-companies/main/companies.json
  Ashby:      https://jobs.ashbyhq.com/sitemap.xml
"""
import asyncio
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

GREENHOUSE_TOKENS_URL = (
    "https://raw.githubusercontent.com/tramcar/greenhouse-tokens/main/tokens.txt"
)
LEVER_SLUGS_URL = (
    "https://raw.githubusercontent.com/nicholasgriffen/lever-companies/main/companies.json"
)
ASHBY_SITEMAP_URL = "https://jobs.ashbyhq.com/sitemap.xml"

CONCURRENCY = 30
PROBE_TIMEOUT = 10


async def _probe_greenhouse(client: httpx.AsyncClient, token: str, registry, semaphore: asyncio.Semaphore) -> bool:
    async with semaphore:
        try:
            resp = await client.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                params={"limit": 1},
                timeout=PROBE_TIMEOUT,
            )
            if resp.status_code == 200:
                registry.upsert({
                    "company_id": token,
                    "display_name": token.replace("-", " ").title(),
                    "ats_type": "greenhouse",
                    "ats_board_id": token,
                    "careers_url": f"https://boards.greenhouse.io/{token}",
                })
                return True
        except Exception:
            pass
        return False


async def _probe_lever(client: httpx.AsyncClient, slug: str, registry, semaphore: asyncio.Semaphore) -> bool:
    async with semaphore:
        try:
            resp = await client.get(
                f"https://api.lever.co/v0/postings/{slug}",
                params={"limit": 1, "mode": "json"},
                timeout=PROBE_TIMEOUT,
            )
            if resp.status_code == 200:
                registry.upsert({
                    "company_id": f"lever_{slug}",
                    "display_name": slug.replace("-", " ").title(),
                    "ats_type": "lever",
                    "ats_board_id": slug,
                    "careers_url": f"https://jobs.lever.co/{slug}",
                })
                return True
        except Exception:
            pass
        return False


async def _probe_ashby(client: httpx.AsyncClient, slug: str, registry, semaphore: asyncio.Semaphore) -> bool:
    async with semaphore:
        try:
            resp = await client.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                timeout=PROBE_TIMEOUT,
            )
            if resp.status_code == 200:
                registry.upsert({
                    "company_id": f"ashby_{slug}",
                    "display_name": slug.replace("-", " ").title(),
                    "ats_type": "ashby",
                    "ats_board_id": slug,
                    "careers_url": f"https://jobs.ashbyhq.com/{slug}",
                })
                return True
        except Exception:
            pass
        return False


def _extract_ashby_slugs(sitemap_xml: str) -> list:
    matches = re.findall(r"https://jobs\.ashbyhq\.com/([^/<\s]+)", sitemap_xml)
    seen = set()
    slugs = []
    for m in matches:
        if m and m not in seen:
            seen.add(m)
            slugs.append(m)
    return slugs


async def run_bootstrap(registry, incremental: bool = False) -> dict:
    """
    Probe curated community datasets and upsert valid companies into company_registry.

    Args:
        registry: CompanyRegistryStore instance
        incremental: If True, only probe tokens/slugs not already in registry.
                     If False, probe all (one-time full bootstrap).

    Returns:
        dict with new_companies and total_active counts.
    """
    semaphore = asyncio.Semaphore(CONCURRENCY)
    new_companies = 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "internship-matcher-crawler/1.0"},
        follow_redirects=True,
    ) as client:

        # --- Greenhouse ---
        try:
            resp = await client.get(GREENHOUSE_TOKENS_URL, timeout=30)
            resp.raise_for_status()
            tokens = [t.strip() for t in resp.text.splitlines() if t.strip()]
            if incremental:
                known = set(registry.get_all_ids(ats_type="greenhouse"))
                tokens = [t for t in tokens if t not in known]
            logger.info("Bootstrap: probing %d Greenhouse tokens", len(tokens))
            tasks = [_probe_greenhouse(client, t, registry, semaphore) for t in tokens[:8000]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            new_companies += sum(1 for r in results if r is True)
        except Exception as e:
            logger.warning("Greenhouse bootstrap failed: %s", e)

        # --- Lever ---
        try:
            resp = await client.get(LEVER_SLUGS_URL, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            slugs = data if isinstance(data, list) else list(data.keys())
            if incremental:
                known = set(registry.get_all_ids(ats_type="lever"))
                slugs = [s for s in slugs if f"lever_{s}" not in known]
            logger.info("Bootstrap: probing %d Lever slugs", len(slugs))
            tasks = [_probe_lever(client, s, registry, semaphore) for s in slugs[:3000]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            new_companies += sum(1 for r in results if r is True)
        except Exception as e:
            logger.warning("Lever bootstrap failed: %s", e)

        # --- Ashby (via sitemap) ---
        try:
            resp = await client.get(ASHBY_SITEMAP_URL, timeout=30)
            resp.raise_for_status()
            slugs = _extract_ashby_slugs(resp.text)
            if incremental:
                known = set(registry.get_all_ids(ats_type="ashby"))
                slugs = [s for s in slugs if f"ashby_{s}" not in known]
            logger.info("Bootstrap: probing %d Ashby slugs", len(slugs))
            tasks = [_probe_ashby(client, s, registry, semaphore) for s in slugs[:2000]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            new_companies += sum(1 for r in results if r is True)
        except Exception as e:
            logger.warning("Ashby bootstrap failed: %s", e)

    stats = registry.get_stats()
    logger.info("Bootstrap complete: %d new companies, %d total active", new_companies, stats.get("total_active", 0))
    return {
        "new_companies": new_companies,
        "total_active": stats.get("total_active", 0),
    }
