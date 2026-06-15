"""
Bootstrap script — seeds company_registry from curated community datasets.

Sources (all public, no auth required):
  Greenhouse: Feashliaa/job-board-aggregator greenhouse_companies.json
              https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/greenhouse_companies.json
              JSON array of board token strings (~10,000+ entries, CC BY-NC 4.0)

  Lever:      Feashliaa/job-board-aggregator lever_companies.json
              https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/lever_companies.json
              JSON array of company slug strings (~3,000+ entries)

  Ashby:      Feashliaa/job-board-aggregator ashby_companies.json
              https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data/ashby_companies.json
              JSON array of org slug strings (~2,000+ entries)

Live-verified 2026-06-15: all three files return JSON arrays of lowercase string slugs/tokens.
"""
import asyncio
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://raw.githubusercontent.com/Feashliaa/job-board-aggregator/main/data"
GREENHOUSE_TOKENS_URL = f"{_BASE}/greenhouse_companies.json"
LEVER_SLUGS_URL = f"{_BASE}/lever_companies.json"
ASHBY_SLUGS_URL = f"{_BASE}/ashby_companies.json"

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
                data = resp.json()
                if isinstance(data, list):
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


async def run_bootstrap(registry, incremental: bool = False) -> dict:
    """
    Probe curated company slug datasets and upsert valid companies into company_registry.

    All datasets are JSON arrays of lowercase string slugs from:
    github.com/Feashliaa/job-board-aggregator (CC BY-NC 4.0, verified 2026-06-15)

    Args:
        registry: CompanyRegistryStore instance
        incremental: If True, skip slugs already in the registry.

    Returns:
        dict with new_companies and total_active counts.
    """
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def _run_greenhouse(client: httpx.AsyncClient) -> int:
        try:
            resp = await client.get(GREENHOUSE_TOKENS_URL, timeout=30)
            resp.raise_for_status()
            tokens = resp.json()
            if not isinstance(tokens, list):
                raise ValueError("Unexpected format: expected JSON array")
            if incremental:
                known = set(registry.get_all_ids(ats_type="greenhouse", active_only=True))
                tokens = [t for t in tokens if t not in known]
            logger.info("Bootstrap: probing %d Greenhouse tokens", len(tokens))
            tasks = [_probe_greenhouse(client, t, registry, semaphore) for t in tokens[:10000]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for r in results if r is True)
        except Exception as e:
            logger.warning("Greenhouse bootstrap failed: %s", e)
            return 0

    async def _run_lever(client: httpx.AsyncClient) -> int:
        try:
            resp = await client.get(LEVER_SLUGS_URL, timeout=30)
            resp.raise_for_status()
            slugs = resp.json()
            if not isinstance(slugs, list):
                raise ValueError("Unexpected format: expected JSON array")
            if incremental:
                known = set(registry.get_all_ids(ats_type="lever", active_only=True))
                slugs = [s for s in slugs if f"lever_{s}" not in known]
            logger.info("Bootstrap: probing %d Lever slugs", len(slugs))
            tasks = [_probe_lever(client, s, registry, semaphore) for s in slugs[:3000]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for r in results if r is True)
        except Exception as e:
            logger.warning("Lever bootstrap failed: %s", e)
            return 0

    async def _run_ashby(client: httpx.AsyncClient) -> int:
        try:
            resp = await client.get(ASHBY_SLUGS_URL, timeout=30)
            resp.raise_for_status()
            slugs = resp.json()
            if not isinstance(slugs, list):
                raise ValueError("Unexpected format: expected JSON array")
            if incremental:
                known = set(registry.get_all_ids(ats_type="ashby", active_only=True))
                slugs = [s for s in slugs if f"ashby_{s}" not in known]
            logger.info("Bootstrap: probing %d Ashby slugs", len(slugs))
            tasks = [_probe_ashby(client, s, registry, semaphore) for s in slugs[:2000]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            return sum(1 for r in results if r is True)
        except Exception as e:
            logger.warning("Ashby bootstrap failed: %s", e)
            return 0

    async with httpx.AsyncClient(
        headers={"User-Agent": "internship-matcher-crawler/1.0"},
        follow_redirects=True,
    ) as client:
        counts = await asyncio.gather(
            _run_greenhouse(client),
            _run_lever(client),
            _run_ashby(client),
        )
        new_companies = sum(counts)

    stats = registry.get_stats()
    logger.info("Bootstrap complete: %d new companies, %d total active", new_companies, stats.get("total_active", 0))
    return {
        "new_companies": new_companies,
        "total_active": stats.get("total_active", 0),
    }
