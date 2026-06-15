"""
iCIMS ATS crawler — sitemap-based discovery + HTML job page parsing.

No public JSON API exists. The reliable approach is:
1. Fetch /{tenant}.icims.com/sitemap.xml to enumerate job URLs
2. Filter by lastmod for incremental crawls and by slug for intern keywords
3. Fetch each job page with in_iframe=1 and parse with BeautifulSoup

Tenant URL pattern: https://{tenant}.icims.com
(subdomain is an opaque slug, NOT careers.{company}.icims.com)
"""
import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from urllib.parse import urljoin
from xml.etree import ElementTree

import httpx

logger = logging.getLogger(__name__)

RATE_LIMIT_DELAY = 0.5
SITEMAP_TIMEOUT = 15
PAGE_TIMEOUT = 20

INTERN_SLUG_KEYWORDS = {
    "intern", "internship", "co-op", "coop", "summer", "apprentice",
}


def _slug_is_intern(url: str) -> bool:
    url_lower = url.lower()
    return any(kw in url_lower for kw in INTERN_SLUG_KEYWORDS)


def _parse_sitemap(xml_text: str) -> List[dict]:
    """Return list of {loc, lastmod} dicts from sitemap XML."""
    entries = []
    try:
        root = ElementTree.fromstring(xml_text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        for url_el in root.findall("sm:url", ns):
            loc = url_el.findtext("sm:loc", default="", namespaces=ns)
            lastmod = url_el.findtext("sm:lastmod", default="", namespaces=ns)
            if loc:
                entries.append({"loc": loc, "lastmod": lastmod})
    except Exception as e:
        logger.warning("Failed to parse iCIMS sitemap: %s", e)
    return entries


def _is_job_url(loc: str) -> bool:
    return bool(re.search(r"/jobs/\d+/.+/job$", loc))


def _parse_job_html(html: str, loc: str) -> dict:
    """
    Extract job fields from iCIMS HTML page.
    Uses BeautifulSoup when available; falls back to regex.
    """
    job = {"apply_link": loc}
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        h1 = soup.find("h1", class_=re.compile(r"iCIMS_Header", re.I))
        if h1:
            job["title"] = h1.get_text(strip=True)

        loc_div = soup.find("div", class_=re.compile(r"iCIMS_Locations", re.I))
        if loc_div:
            job["location"] = loc_div.get_text(separator=", ", strip=True)

        desc_div = soup.find("div", class_=re.compile(r"iCIMS_InfoMsg_Job", re.I))
        if desc_div:
            job["description"] = desc_div.get_text(separator="\n", strip=True)
    except ImportError:
        title_m = re.search(r'<h1[^>]*iCIMS_Header[^>]*>(.*?)</h1>', html, re.S)
        if title_m:
            job["title"] = re.sub(r"<[^>]+>", "", title_m.group(1)).strip()
        desc_m = re.search(r'<div[^>]*iCIMS_InfoMsg_Job[^>]*>(.*?)</div>', html, re.S | re.I)
        if desc_m:
            job["description"] = re.sub(r"<[^>]+>", " ", desc_m.group(1)).strip()
    except Exception as e:
        logger.debug("iCIMS HTML parse error for %s: %s", loc, e)

    return job


async def fetch_jobs(company, since_hours: Optional[int] = None) -> List[dict]:
    """
    Fetch intern jobs from an iCIMS tenant via sitemap + HTML scraping.

    Returns raw dicts with '_title' key. No exception raised for missing data;
    returns empty list on network failure.
    """
    tenant = company.ats_board_id
    sitemap_url = f"https://{tenant}.icims.com/sitemap.xml"

    since_dt: Optional[datetime] = None
    if since_hours is not None:
        since_dt = datetime.utcnow() - timedelta(hours=since_hours)

    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=SITEMAP_TIMEOUT,
        headers={"User-Agent": "Mozilla/5.0 (compatible; internship-matcher-crawler/1.0)"},
    ) as client:
        try:
            resp = await client.get(sitemap_url)
            if resp.status_code != 200:
                logger.info("iCIMS sitemap %s returned %d — skipping", tenant, resp.status_code)
                return []
        except httpx.RequestError as e:
            logger.warning("iCIMS sitemap network error for %s: %s", tenant, e)
            return []

        entries = _parse_sitemap(resp.text)

        job_entries = []
        for e in entries:
            loc = e["loc"]
            if not _is_job_url(loc):
                continue
            if not _slug_is_intern(loc):
                continue
            if since_dt is not None and e.get("lastmod"):
                try:
                    lm = datetime.fromisoformat(e["lastmod"].replace("Z", "+00:00")).replace(tzinfo=None)
                    if lm < since_dt:
                        continue
                except Exception:
                    pass
            job_entries.append(e)

        if not job_entries:
            return []

        results = []
        for entry in job_entries:
            loc = entry["loc"]
            page_url = loc + "?in_iframe=1"
            try:
                page_resp = await client.get(page_url, timeout=PAGE_TIMEOUT)
                if page_resp.status_code != 200:
                    continue
                job = _parse_job_html(page_resp.text, loc)
                date_str = None
                if entry.get("lastmod"):
                    date_str = entry["lastmod"][:10]
                job["date_posted"] = date_str
                job["job_id"] = re.search(r"/jobs/(\d+)/", loc)
                if job["job_id"]:
                    job["job_id"] = job["job_id"].group(1)
                job["_title"] = job.get("title", "")
                results.append(job)
            except Exception as e:
                logger.debug("iCIMS page fetch error %s: %s", loc, e)
            await asyncio.sleep(RATE_LIMIT_DELAY)

        return results
