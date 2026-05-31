"""
Deterministic, user-controlled job filters applied BEFORE the LLM matching stage.

These filters are hard constraints supplied by the user on the frontend (location,
position, company size, U.S. citizenship eligibility, companies to avoid). Applying
them before scoring keeps results relevant and avoids paying for LLM analysis on jobs
the user has explicitly excluded.

All filters are optional — an empty/None value for a given dimension means "no filtering"
on that dimension, so the default behaviour is unchanged (every job passes).
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Position categories — map a user-facing category to title keywords.
# A job passes the position filter if its title matches ANY selected category.
# ---------------------------------------------------------------------------
POSITION_KEYWORDS: Dict[str, List[str]] = {
    "software_engineer": ["software engineer", "swe", "software development", "software developer", "programmer"],
    "frontend": ["frontend", "front-end", "front end", "ui engineer", "web developer"],
    "backend": ["backend", "back-end", "back end", "api"],
    "fullstack": ["full stack", "fullstack", "full-stack"],
    "data_science": ["data scien", "data analy", "analytics", "analyst"],
    "data_engineering": ["data engineer", "etl", "data platform"],
    "machine_learning": ["machine learning", "ml engineer", " ml ", "artificial intelligence", " ai ", "deep learning", "nlp", "computer vision"],
    "mobile": ["mobile", "ios", "android", "react native", "flutter"],
    "devops": ["devops", "sre", "site reliability", "infrastructure", "platform engineer"],
    "security": ["security", "cyber", "infosec"],
    "qa": ["qa", "sdet", "test", "quality"],
    "hardware": ["hardware", "embedded", "firmware", "fpga", "asic"],
}


# ---------------------------------------------------------------------------
# Company size — we don't scrape headcount, so "large/enterprise" is identified
# via a curated set of well-known large companies. Everything else is treated as
# "startup / mid-size". This is a best-effort heuristic surfaced as such in the UI.
# ---------------------------------------------------------------------------
LARGE_COMPANIES = {
    "google", "alphabet", "meta", "facebook", "amazon", "aws", "apple", "microsoft",
    "netflix", "nvidia", "intel", "ibm", "oracle", "salesforce", "adobe", "cisco",
    "qualcomm", "broadcom", "amd", "dell", "hp", "hewlett packard", "hpe", "sap",
    "vmware", "uber", "lyft", "airbnb", "tesla", "spacex", "paypal", "block", "square",
    "stripe", "snap", "snapchat", "pinterest", "twitter", "x", "linkedin", "tiktok",
    "bytedance", "tencent", "alibaba", "samsung", "sony", "spotify", "atlassian",
    "servicenow", "workday", "snowflake", "databricks", "palantir", "twilio", "shopify",
    "doordash", "instacart", "robinhood", "coinbase", "datadog", "cloudflare",
    "jpmorgan", "jpmorgan chase", "chase", "goldman sachs", "morgan stanley",
    "bank of america", "wells fargo", "citi", "citigroup", "capital one", "american express",
    "visa", "mastercard", "fidelity", "blackrock", "deloitte", "accenture", "pwc", "ey",
    "kpmg", "mckinsey", "boston consulting group", "bcg", "bain",
    "boeing", "lockheed martin", "northrop grumman", "raytheon", "rtx", "general dynamics",
    "general motors", "gm", "ford", "general electric", "ge", "honeywell", "3m", "caterpillar",
    "johnson & johnson", "pfizer", "merck", "abbvie", "medtronic", "unitedhealth", "cvs",
    "walmart", "target", "costco", "home depot", "nike", "disney", "comcast", "nbcuniversal",
    "at&t", "verizon", "t-mobile", "exxonmobil", "chevron", "procter & gamble", "p&g",
    "coca-cola", "pepsico", "mcdonald's", "starbucks", "fedex", "ups", "kbr", "gdit",
    "booz allen hamilton", "leidos", "saic", "mitre", "intuit", "ebay", "yahoo", "dropbox",
    "zoom", "okta", "splunk", "mongodb", "roblox", "epic games", "electronic arts", "ea",
    "activision", "blizzard", "nintendo", "siemens", "bosch", "philips", "schneider electric",
}


def _normalize(text: str) -> str:
    return (text or "").strip().lower()


def _company_is_large(company: str) -> bool:
    c = _normalize(company)
    if not c:
        return False
    if c in LARGE_COMPANIES:
        return True
    # Substring match so "Google LLC" / "Amazon.com" / "Meta Platforms" still resolve.
    for known in LARGE_COMPANIES:
        if known in c or c in known:
            return True
    return False


def _job_requires_citizenship(job: Dict[str, Any]) -> bool:
    """True if the posting requires U.S. citizenship (🇺🇸 marker or explicit text)."""
    title = job.get("title", "") or ""
    text = f"{title} {job.get('description', '')}".lower()
    if "🇺🇸" in title or "🇺🇸" in text:
        return True
    citizenship_phrases = [
        "u.s. citizen", "us citizen", "u.s. citizenship", "us citizenship",
        "must be a citizen", "citizenship required", "citizenship is required",
        "security clearance", "active clearance", "secret clearance", "ts/sci",
    ]
    return any(p in text for p in citizenship_phrases)


def _job_offers_no_sponsorship(job: Dict[str, Any]) -> bool:
    """True if the posting explicitly does NOT offer visa sponsorship (🛂 marker or text)."""
    title = job.get("title", "") or ""
    text = f"{title} {job.get('description', '')}".lower()
    if "🛂" in title or "🛂" in text:
        return True
    no_sponsor_phrases = [
        "no sponsorship", "does not offer sponsorship", "not offer sponsorship",
        "will not sponsor", "do not sponsor", "unable to sponsor",
        "without sponsorship", "no visa sponsorship", "sponsorship is not available",
    ]
    return any(p in text for p in no_sponsor_phrases)


def normalize_filters(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Coerce a raw filters dict (e.g. parsed from a JSON form field) into a clean,
    validated structure. Returns a dict with consistent types and lowercased values.
    """
    raw = raw or {}

    def _as_str_list(value) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            parts = re.split(r"[,\n;]", value)
        elif isinstance(value, (list, tuple)):
            parts = [str(v) for v in value]
        else:
            return []
        return [p.strip() for p in parts if p and p.strip()]

    citizenship = _normalize(raw.get("citizenship", "any")) or "any"
    if citizenship not in ("any", "citizen", "non_citizen"):
        citizenship = "any"

    company_sizes = {s for s in (_normalize(x) for x in _as_str_list(raw.get("company_sizes"))) if s in ("startup", "midsize", "large")}

    positions = {p for p in (_normalize(x) for x in _as_str_list(raw.get("positions"))) if p in POSITION_KEYWORDS}

    return {
        "locations": _as_str_list(raw.get("locations")),
        "positions": positions,
        "company_sizes": company_sizes,
        "citizenship": citizenship,
        "avoid_companies": _as_str_list(raw.get("avoid_companies")),
    }


def has_active_filters(filters: Dict[str, Any]) -> bool:
    if not filters:
        return False
    return bool(
        filters.get("locations")
        or filters.get("positions")
        or filters.get("company_sizes")
        or filters.get("avoid_companies")
        or filters.get("citizenship", "any") != "any"
    )


def _passes_location(job: Dict[str, Any], locations: List[str]) -> bool:
    if not locations:
        return True
    job_location = _normalize(job.get("location", ""))
    for loc in locations:
        loc_l = _normalize(loc)
        if not loc_l:
            continue
        if loc_l in ("remote", "remote only"):
            if "remote" in job_location:
                return True
            continue
        if loc_l in job_location:
            return True
    return False


def _passes_position(job: Dict[str, Any], positions) -> bool:
    if not positions:
        return True
    title = _normalize(job.get("title", ""))
    for category in positions:
        for kw in POSITION_KEYWORDS.get(category, []):
            if kw in title:
                return True
    return False


def _passes_company_size(job: Dict[str, Any], company_sizes) -> bool:
    if not company_sizes:
        return True
    is_large = _company_is_large(job.get("company", ""))
    allow_large = "large" in company_sizes
    allow_other = bool(company_sizes & {"startup", "midsize"})
    if is_large:
        return allow_large
    return allow_other


def _passes_citizenship(job: Dict[str, Any], citizenship: str) -> bool:
    if citizenship != "non_citizen":
        return True
    # A non-citizen / sponsorship-dependent applicant can't take roles that require
    # citizenship or that explicitly refuse sponsorship.
    if _job_requires_citizenship(job) or _job_offers_no_sponsorship(job):
        return False
    return True


def _passes_avoid_companies(job: Dict[str, Any], avoid_companies: List[str]) -> bool:
    if not avoid_companies:
        return True
    company = _normalize(job.get("company", ""))
    if not company:
        return True
    for avoided in avoid_companies:
        a = _normalize(avoided)
        if a and (a in company or company in a):
            return False
    return True


def apply_filters(jobs: List[Dict[str, Any]], raw_filters: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter the job list according to user-supplied preferences.

    Args:
        jobs: List of job dicts.
        raw_filters: Raw (possibly partial) filters dict — normalized internally.

    Returns:
        The subset of jobs passing every active filter. If no filters are active,
        the original list is returned unchanged.
    """
    filters = normalize_filters(raw_filters)
    if not has_active_filters(filters):
        return jobs

    locations = filters["locations"]
    positions = filters["positions"]
    company_sizes = filters["company_sizes"]
    citizenship = filters["citizenship"]
    avoid_companies = filters["avoid_companies"]

    filtered = [
        job for job in jobs
        if _passes_avoid_companies(job, avoid_companies)
        and _passes_location(job, locations)
        and _passes_position(job, positions)
        and _passes_company_size(job, company_sizes)
        and _passes_citizenship(job, citizenship)
    ]

    logger.info(
        f"[Filters] {len(filtered)}/{len(jobs)} jobs passed "
        f"(locations={locations}, positions={sorted(positions)}, "
        f"company_sizes={sorted(company_sizes)}, citizenship={citizenship}, "
        f"avoid={avoid_companies})"
    )
    return filtered
