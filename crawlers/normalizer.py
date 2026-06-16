"""
Normalizer — converts ATS-specific raw job dicts into the internal Job schema.

All ATS crawlers return a raw dict plus a "_title" convenience key so the
orchestrator can apply the intern filter before normalizing.
"""
import html as _html
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Word-boundary matching is essential: plain substring "intern" matches "Internal"
# and "International", which flooded results with non-internships. Boundaries are
# (?<![a-z]) / (?![a-z]) rather than \b so hyphenated forms like "co-op" still match.
_INTERN_TITLE_RE = re.compile(
    r"(?<![a-z])("
    r"intern(?:ship)?"
    r"|co[-\s]?op"
    r"|summer\s+(?:analyst|associate|program)"
    r"|graduate\s+trainee"
    r"|apprentice(?:ship)?"
    r"|student"
    r")(?![a-z])",
    re.I,
)


def is_intern_posting(title: str, employment_type: str = "") -> bool:
    return bool(_INTERN_TITLE_RE.search(title or "")) or bool(
        _INTERN_TITLE_RE.search(employment_type or "")
    )


def strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r"<[^>]+>", " ", raw_html)
    clean = _html.unescape(clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def canonicalize_apply_link(url: str, ats_type: str = "", ats_job_id: str = "", ats_board_id: str = "") -> str:
    """
    Normalize apply_link to a canonical form so cross-source duplicates hash identically.

    Strips /apply suffix (present on Greenhouse absolute_url and Lever applyUrl)
    and trailing slashes so the same job from two sources maps to one DB row.
    """
    if not url:
        return url
    url = url.rstrip("/")
    if url.endswith("/apply"):
        url = url[: -len("/apply")]
    return url


def _extract_title(raw: dict, ats_type: str) -> str:
    if ats_type == "lever":
        return raw.get("text") or raw.get("title", "")
    if ats_type == "smartrecruiters":
        return raw.get("name") or raw.get("title", "")
    return raw.get("title", "")


def _extract_location(raw: dict, ats_type: str) -> str:
    if ats_type == "greenhouse":
        loc = raw.get("location", {})
        return loc.get("name", "") if isinstance(loc, dict) else str(loc)
    if ats_type == "lever":
        cats = raw.get("categories", {})
        return cats.get("location", "") if isinstance(cats, dict) else ""
    if ats_type == "ashby":
        return raw.get("location", "")
    if ats_type == "workday":
        return raw.get("locationsText", "")
    if ats_type == "smartrecruiters":
        loc = raw.get("location", {})
        return loc.get("fullLocation", "") if isinstance(loc, dict) else ""
    if ats_type == "icims":
        return raw.get("location", "")
    return raw.get("location", "")


def _extract_apply_link(raw: dict, ats_type: str, company) -> str:
    if ats_type == "greenhouse":
        url = raw.get("absolute_url", "")
        return canonicalize_apply_link(url, ats_type)
    if ats_type == "lever":
        url = raw.get("hostedUrl") or raw.get("applyUrl", "")
        return canonicalize_apply_link(url, ats_type)
    if ats_type == "ashby":
        url = raw.get("jobUrl") or raw.get("applyUrl", "")
        return canonicalize_apply_link(url, ats_type)
    if ats_type == "workday":
        path = raw.get("externalPath", "")
        board_id = company.ats_board_id if company else ""
        return raw.get("_apply_link", "") or f"https://{board_id}{path}"
    if ats_type == "smartrecruiters":
        url = raw.get("applyUrl") or raw.get("postingUrl")
        if url:
            return url
        # applyUrl/postingUrl exist only in the detail response; fall back to the
        # canonical careers URL so a failed detail fetch never yields an empty link.
        board_id = company.ats_board_id if company else ""
        job_id = raw.get("id", "")
        if board_id and job_id:
            return f"https://jobs.smartrecruiters.com/{board_id}/{job_id}"
        return ""
    if ats_type == "icims":
        return raw.get("apply_link", "")
    return ""


def _extract_description(raw: dict, ats_type: str) -> str:
    if ats_type == "greenhouse":
        return strip_html(raw.get("content", ""))
    if ats_type == "lever":
        return raw.get("descriptionPlain") or strip_html(raw.get("description", ""))
    if ats_type == "ashby":
        return raw.get("descriptionPlain") or strip_html(raw.get("descriptionHtml", ""))
    if ats_type == "workday":
        job_info = raw.get("jobPostingInfo", {}) or {}
        return strip_html(job_info.get("jobDescription", ""))
    if ats_type == "smartrecruiters":
        job_ad = raw.get("jobAd", {}) or {}
        sections = job_ad.get("sections", {}) or {}
        parts = []
        for key in ("jobDescription", "qualifications", "additionalInformation"):
            sec = sections.get(key, {})
            if sec and sec.get("text"):
                parts.append(strip_html(sec["text"]))
        return "\n\n".join(parts)
    if ats_type == "icims":
        return strip_html(raw.get("description", ""))
    return ""


def _extract_posted_date(raw: dict, ats_type: str) -> Optional[str]:
    if ats_type == "greenhouse":
        val = raw.get("updated_at", "")
        if val:
            return val[:10]
    if ats_type == "lever":
        ts = raw.get("createdAt")
        if ts:
            try:
                dt = datetime.utcfromtimestamp(int(ts) / 1000)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
    if ats_type == "ashby":
        val = raw.get("publishedAt", "")
        if val:
            return val[:10]
    if ats_type == "workday":
        return None
    if ats_type == "smartrecruiters":
        val = raw.get("releasedDate", "")
        if val:
            return val[:10]
    if ats_type == "icims":
        return raw.get("date_posted")
    return None


def _calculate_days(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    try:
        posted = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.utcnow() - posted).days
    except Exception:
        return None


def _extract_department(raw: dict, ats_type: str) -> str:
    if ats_type == "greenhouse":
        depts = raw.get("departments", [])
        return depts[0].get("name", "") if depts else ""
    if ats_type == "lever":
        cats = raw.get("categories", {}) or {}
        return cats.get("team") or cats.get("department", "")
    if ats_type == "ashby":
        return raw.get("department") or raw.get("team", "")
    if ats_type == "smartrecruiters":
        dept = raw.get("department", {}) or {}
        return dept.get("label", "")
    return ""


def _extract_employment_type(raw: dict, ats_type: str) -> str:
    if ats_type == "lever":
        cats = raw.get("categories", {}) or {}
        return cats.get("commitment", "")
    if ats_type == "ashby":
        return raw.get("employmentType", "")
    if ats_type == "smartrecruiters":
        # Derive from experienceLevel (the field that admitted the job) so the stored
        # value can't contradict the internship filter; typeOfEmployment.label can be
        # "Permanent" even for an experienceLevel.id == "internship" posting.
        exp = raw.get("experienceLevel", {}) or {}
        return exp.get("label") or exp.get("id", "")
    return ""


def _extract_compensation(raw: dict, ats_type: str) -> str:
    if ats_type == "lever":
        sr = raw.get("salaryRange")
        if sr and isinstance(sr, dict):
            mn, mx, cur = sr.get("min"), sr.get("max"), sr.get("currency", "USD")
            intv = sr.get("interval", "")
            if mn and mx:
                return f"{cur} {mn}-{mx} {intv}".strip()
    if ats_type == "ashby":
        comp = raw.get("compensation")
        if comp and isinstance(comp, dict):
            return comp.get("compensationTierSummary", "")
    return ""


def _extract_remote_type(raw: dict, ats_type: str) -> str:
    if ats_type == "lever":
        # `or ""` (not a .get default): Ashby/Lever can send workplaceType: null,
        # so the key exists with a None value and the .get default never applies.
        wt = raw.get("workplaceType") or ""
        return wt.lower().replace("on-site", "onsite")
    if ats_type == "ashby":
        wt = raw.get("workplaceType") or ""
        # NB: dict.get evaluates its default eagerly, so wt.lower() must be safe
        # for every wt — hence the None-coercion above (was crashing all of Ashby).
        return {"OnSite": "onsite", "Remote": "remote", "Hybrid": "hybrid"}.get(wt, wt.lower())
    if ats_type == "workday":
        return raw.get("remoteType", "")
    if ats_type == "smartrecruiters":
        loc = raw.get("location", {}) or {}
        if loc.get("remote"):
            return "remote"
        if loc.get("hybrid"):
            return "hybrid"
        return "onsite"
    return ""


def _extract_ats_job_id(raw: dict, ats_type: str) -> str:
    if ats_type == "greenhouse":
        return str(raw.get("id", ""))
    if ats_type == "lever":
        return raw.get("id", "")
    if ats_type == "ashby":
        return raw.get("id", "")
    if ats_type == "workday":
        fields = raw.get("bulletFields", [])
        return fields[0] if fields else ""
    if ats_type == "smartrecruiters":
        return str(raw.get("id", ""))
    if ats_type == "icims":
        return str(raw.get("job_id", ""))
    return ""


def _extract_skills_from_text(text: str) -> list:
    """
    Lightweight keyword skill extraction from description text.
    Reuses the same approach as the existing scraper — returns a list of skill strings.
    For ATS jobs the MCP agent will do full extraction; this is a best-effort bootstrap.
    """
    COMMON_SKILLS = [
        "python", "java", "javascript", "typescript", "react", "node.js", "sql",
        "c++", "c#", "go", "rust", "swift", "kotlin", "ruby", "php", "r",
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "aws", "gcp", "azure", "docker", "kubernetes", "git",
        "data analysis", "pandas", "numpy", "spark", "hadoop",
        "html", "css", "vue", "angular", "django", "flask", "fastapi",
        "postgresql", "mysql", "mongodb", "redis",
    ]
    text_lower = text.lower()
    return [s for s in COMMON_SKILLS if s in text_lower]


# Headings that introduce a requirements/qualifications block in a JD.
_REQ_SECTION_KEYWORDS = (
    "requirement", "qualification", "what you", "what we're looking",
    "who you are", "you'll need", "you will need", "you have", "about you",
    "minimum", "preferred", "basic qualification", "skills and experience",
    "profile", "who we're looking",  # Lever boards label the section "Profile"
)


def _looks_like_req_heading(text: str) -> bool:
    t = (text or "").strip().lower()
    return bool(t) and len(t) <= 80 and any(k in t for k in _REQ_SECTION_KEYWORDS)


def _description_html(raw: dict, ats_type: str) -> str:
    """Return the richest HTML description available for the ATS type."""
    if ats_type == "greenhouse":
        return raw.get("content", "")
    if ats_type == "lever":
        return raw.get("description", "")
    if ats_type == "ashby":
        return raw.get("descriptionHtml", "")
    if ats_type == "workday":
        return (raw.get("jobPostingInfo") or {}).get("jobDescription", "")
    if ats_type == "icims":
        return raw.get("description", "")
    return ""


def _requirements_from_html(raw_html: str) -> str:
    """
    Parse a JD's HTML and pull out the requirement/qualification sections:
    for each matching heading, capture the list items / paragraphs that follow
    until the next heading. Returns a readable bullet block, or "" if none found.
    """
    if not raw_html:
        return ""
    html = _html.unescape(raw_html)  # greenhouse double-escapes its HTML
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "strong", "b", "p"]):
        if not _looks_like_req_heading(heading.get_text()):
            continue
        items, nxt, steps = [], heading.find_next_sibling(), 0
        while nxt is not None and steps < 8 and nxt.name not in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if nxt.name in ("ul", "ol"):
                for li in nxt.find_all("li"):
                    txt = li.get_text(" ", strip=True)
                    if len(txt) > 8:
                        items.append(f"• {txt}")
            elif nxt.name in ("p", "div"):
                txt = nxt.get_text(" ", strip=True)
                if len(txt) > 8:
                    items.append(txt)
            nxt, steps = nxt.find_next_sibling(), steps + 1
        if items:
            out.append(f"{heading.get_text(' ', strip=True)}:")
            out.extend(items[:8])
            out.append("")
    return "\n".join(out).strip()


def _extract_requirements(raw: dict, ats_type: str) -> str:
    """
    Best-effort deterministic requirements extraction from a JD — the ATS analog
    of the GitHub scraper's extract_detailed_requirements. SmartRecruiters and
    Lever expose the section as structured data; the rest are parsed from HTML.
    """
    if ats_type == "smartrecruiters":
        secs = ((raw.get("jobAd") or {}).get("sections") or {})
        qual = (secs.get("qualifications") or {}).get("text", "")
        if qual:
            return strip_html(qual)
    if ats_type == "lever":
        parts = []
        for lst in raw.get("lists", []) or []:
            if _looks_like_req_heading(lst.get("text", "")):
                body = strip_html(lst.get("content", ""))
                if body:
                    parts.append(f"{lst['text'].strip()}: {body}")
        if parts:
            return "\n".join(parts)
    return _requirements_from_html(_description_html(raw, ats_type))


def normalize_job(raw: dict, ats_type: str, company) -> dict:
    """Convert ATS-specific raw job dict to internal Job schema."""
    title = _extract_title(raw, ats_type)
    description = _extract_description(raw, ats_type)
    posted_date = _extract_posted_date(raw, ats_type)
    days_since = _calculate_days(posted_date)
    apply_link = _extract_apply_link(raw, ats_type, company)

    return {
        "company": company.display_name,
        "title": title,
        "location": _extract_location(raw, ats_type),
        "apply_link": apply_link,
        "description": description,
        "required_skills": _extract_skills_from_text(description),
        "job_requirements": _extract_requirements(raw, ats_type),
        "source": f"ats_{ats_type}",
        "days_since_posted": days_since,
        "date_posted": posted_date,
        "date_posted_raw": raw.get("updated_at") or raw.get("publishedAt") or raw.get("releasedDate") or "",
        # Rich ATS metadata lives under "metadata" (the existing scraper contract):
        # bulk_insert_jobs merges date_posted* fields in, json.dumps it into the
        # job_metadata column, and refreshes it on conflict. A separate pre-serialized
        # "job_metadata" key would be silently ignored by bulk_insert_jobs.
        "metadata": {
            "days_since_posted": days_since,
            "date_posted": posted_date,
            "date_posted_raw": raw.get("updated_at") or raw.get("publishedAt") or raw.get("releasedDate") or "",
            "ats_type": ats_type,
            "ats_job_id": _extract_ats_job_id(raw, ats_type),
            "ats_board_id": company.ats_board_id,
            "department": _extract_department(raw, ats_type),
            "employment_type": _extract_employment_type(raw, ats_type),
            "compensation": _extract_compensation(raw, ats_type),
            "remote_type": _extract_remote_type(raw, ats_type),
            "application_questions": [],
        },
    }
