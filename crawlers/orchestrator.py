"""
Crawl orchestrator — manages schedule, concurrency, and error tracking per company.

Replaces the current dispatcher.py for ATS sources. The SimplifyJobs scraper
continues to run in parallel via job_scrapers/dispatcher.py.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from crawlers.company_registry import CompanyRegistryStore, CompanyRecord
from crawlers.normalizer import is_intern_posting, normalize_job
from job_database import bulk_insert_jobs

logger = logging.getLogger(__name__)

CONCURRENCY = 20
RATE_LIMIT_DELAY = 0.2
BACKOFF_ON_429 = 60
MAX_RETRIES = 3


def _get_crawler(ats_type: str):
    """Return the crawler module for the given ATS type."""
    if ats_type == "greenhouse":
        import crawlers.greenhouse as m
    elif ats_type == "lever":
        import crawlers.lever as m
    elif ats_type == "ashby":
        import crawlers.ashby as m
    elif ats_type == "workday":
        import crawlers.workday as m
    elif ats_type == "smartrecruiters":
        import crawlers.smartrecruiters as m
    elif ats_type == "icims":
        import crawlers.icims as m
    else:
        return None
    return m


class CrawlOrchestrator:
    """
    Manages crawl schedule, concurrency, and error tracking per company.
    """

    def __init__(self):
        self.registry = CompanyRegistryStore()

    async def run_incremental(self, max_age_hours: int = 1, ats_types: List[str] = None) -> dict:
        """Fetch only jobs updated in last N hours. Designed to run every 15 min."""
        companies = self.registry.get_due_for_crawl(priority=[1, 2, 3])
        if ats_types:
            companies = [c for c in companies if c.ats_type in ats_types]
        return await self._crawl_batch(companies, since_hours=max_age_hours)

    async def run_full(self, ats_types: List[str] = None) -> dict:
        """Re-crawl all companies. Designed to run nightly."""
        companies = self.registry.get_all_active()
        if ats_types:
            companies = [c for c in companies if c.ats_type in ats_types]
        return await self._crawl_batch(companies, since_hours=None)

    async def _crawl_batch(self, companies: List[CompanyRecord], since_hours: Optional[int]) -> dict:
        start = datetime.utcnow()
        semaphore = asyncio.Semaphore(CONCURRENCY)
        tasks = [self._crawl_company(c, since_hours, semaphore) for c in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        jobs_flat: List[dict] = []
        for r in results:
            if isinstance(r, list):
                jobs_flat.extend(r)

        insert_result = bulk_insert_jobs(jobs_flat) if jobs_flat else {"new_jobs": 0}
        if companies:
            self.registry.update_last_crawled(companies)

        duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
        return {
            "companies_crawled": len(companies),
            "jobs_found": len(jobs_flat),
            "new_jobs": insert_result.get("new_jobs", 0),
            "duration_ms": duration_ms,
        }

    async def _crawl_company(
        self,
        company: CompanyRecord,
        since_hours: Optional[int],
        semaphore: asyncio.Semaphore,
    ) -> List[dict]:
        async with semaphore:
            module = _get_crawler(company.ats_type)
            if module is None:
                logger.warning("No crawler for ats_type=%s", company.ats_type)
                return []

            for attempt in range(MAX_RETRIES):
                try:
                    raw_jobs = await module.fetch_jobs(company, since_hours=since_hours)
                    intern_jobs = [j for j in raw_jobs if is_intern_posting(j.get("_title", ""))]
                    return [normalize_job(j, company.ats_type, company) for j in intern_jobs]
                except Exception as exc:
                    cls_name = type(exc).__name__
                    if "CompanyNotFound" in cls_name:
                        self.registry.mark_inactive(company.company_id)
                        return []
                    if "RateLimitError" in cls_name:
                        wait = BACKOFF_ON_429 * (attempt + 1)
                        logger.info("Rate limit for %s — sleeping %ds", company.company_id, wait)
                        await asyncio.sleep(wait)
                        if attempt == MAX_RETRIES - 1:
                            return []
                    else:
                        logger.error(
                            "Crawl error for %s (%s): %s",
                            company.company_id, company.ats_type, exc,
                        )
                        return []
        return []

    async def discover_new_companies(self) -> dict:
        """
        Discover companies not yet in the registry by probing apply_link referrals
        and delegating to the bootstrap module.
        """
        from crawlers.bootstrap import run_bootstrap
        return await run_bootstrap(registry=self.registry, incremental=True)
