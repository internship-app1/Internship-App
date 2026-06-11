"""
Hosted MCP endpoint — the zero-install tier, mounted at /mcp.

Exposes ONLY the stateless data-plane tools (jobs_list, job_get,
jobs_prefilter) plus the tailoring-guide resource. Everything stateful or
heavy stays in the user-run internship-mcp server: the encrypted PII vault,
packet building, the application tracker, and resume compilation — the server
instructions below steer agents to the uvx install for those. NO model calls
here, ever (Prime Directive).

Auth is per-request: X-API-Key header, or ?key= query param for clients that
cannot send headers (claude.ai custom connectors). Token-in-URL is the
pragmatic v1; OAuth replaces it in v2.

Requires the `mcp` SDK (Python >= 3.10). app.py guards the import so the
3.9 dev venv still boots without it — production (3.11) serves it.
"""
import logging
from typing import Dict, List, Optional

from mcp.server.fastmcp import Context, FastMCP

from job_database import get_job_by_hash, verify_api_key
from matching.matcher import prefilter_and_score
from mcp_api import _fetch_jobs, _job_summary

logger = logging.getLogger(__name__)

INSTRUCTIONS = (
    "Internship Matcher — hosted search & scoring tier. YOU (the host agent) do all "
    "reasoning; these tools are deterministic data access.\n\n"
    "This hosted endpoint covers DISCOVERY only: list jobs, fetch full descriptions, "
    "and run deterministic fit scoring. The full apply agent — encrypted local "
    "profile, resume compilation, application packets, tracking, and browser "
    "prefill — runs on the user's machine. If the user wants to actually APPLY, "
    "tell them to install the full agent: one config block from "
    "https://internshipmatcher.com/developer (uvx, no Docker needed).\n\n"
    "Auth: every tool needs the user's API key, supplied as ?key=... in the "
    "connector URL or an X-API-Key header. Keys come from "
    "https://internshipmatcher.com/developer."
)

remote_mcp = FastMCP(
    "internship-matcher",
    instructions=INSTRUCTIONS,
    stateless_http=True,
)
# Serve the protocol at the mount root so app.mount("/mcp", ...) → /mcp
remote_mcp.settings.streamable_http_path = "/"


def _require_user(ctx: Context) -> str:
    """Resolve and verify the API key for this request (header or ?key=)."""
    request = ctx.request_context.request
    raw = None
    if request is not None:
        raw = request.headers.get("x-api-key") or request.query_params.get("key")
    user_id = verify_api_key(raw) if raw else None
    if not user_id:
        raise ValueError(
            "Missing or invalid API key. Add ?key=im_live_... to the connector URL "
            "(or send an X-API-Key header). Generate a key at "
            "https://internshipmatcher.com/developer"
        )
    return user_id


@remote_mcp.tool()
def jobs_list(
    ctx: Context,
    since_hours: Optional[int] = None,
    max_days_old: int = 30,
    location: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict:
    """List active internship postings (deterministic DB query, no AI).
    Start with since_hours=72 for fresh postings. Next: jobs_prefilter to score
    them against the candidate, or job_get for a full description."""
    _require_user(ctx)
    limit = max(1, min(limit, 200))
    jobs = _fetch_jobs(since_hours, max_days_old, location, q)
    return {
        "jobs": [_job_summary(j) for j in jobs[offset:offset + limit]],
        "total": len(jobs),
        "limit": limit,
        "offset": offset,
    }


@remote_mcp.tool()
def job_get(ctx: Context, job_hash: str) -> Dict:
    """Fetch one job with its FULL untruncated description — read this before
    judging fit deeply or advising the user on an application."""
    _require_user(ctx)
    job = get_job_by_hash(job_hash)
    if not job:
        raise ValueError("Unknown job_hash")
    return {
        "job_hash": job["job_hash"],
        "company": job["company"],
        "title": job["title"],
        "location": job["location"],
        "apply_link": job["apply_link"],
        "source": job.get("source"),
        "required_skills": job.get("required_skills") or [],
        "description": job.get("description"),
        "job_requirements": job.get("job_requirements"),
    }


@remote_mcp.tool()
def jobs_prefilter(
    ctx: Context,
    resume_profile: Dict,
    filters: Optional[Dict] = None,
    target_count: int = 40,
    exclude_hashes: Optional[List[str]] = None,
) -> Dict:
    """Deterministic keyword + metadata scoring against a small PII-free
    resume_profile: {skills: [...], experience_level: student|entry_level|
    experienced, years_of_experience, location, willing_to_relocate, remote_ok}.
    YOU extract the skills from the user's resume yourself — never send resume
    text anywhere. Treat combined_score as a prefilter; your judgment over the
    full descriptions (job_get) is the real ranking.
    exclude_hashes: optional list of job_hashes to omit (e.g. already-applied jobs)."""
    _require_user(ctx)
    _LEVEL_NORM = {
        "student": "student", "intern": "student", "undergraduate": "student",
        "entry_level": "entry_level", "entry": "entry_level", "junior": "entry_level",
        "recent_graduate": "entry_level", "new_grad": "entry_level",
        "experienced": "experienced", "mid": "experienced", "mid_level": "experienced",
        "senior": "experienced",
    }
    raw_level = str(resume_profile.get("experience_level") or "").lower().strip()
    normalized = _LEVEL_NORM.get(raw_level)
    if normalized is None:
        raise ValueError(
            f"resume_profile.experience_level must be one of "
            f"{sorted({'student', 'entry_level', 'experienced'})}; "
            f"got {resume_profile.get('experience_level')!r}"
        )
    resume_profile = {**resume_profile, "experience_level": normalized}
    f = filters or {}
    jobs = _fetch_jobs(
        f.get("since_hours"), f.get("max_days_old", 30), f.get("location"), f.get("q")
    )
    if exclude_hashes:
        excluded = set(exclude_hashes)
        jobs = [j for j in jobs if j.get("job_hash") not in excluded]
    scored = prefilter_and_score(resume_profile, jobs)
    target = max(1, min(target_count, 200))
    return {
        "candidates": scored[:target],
        "evaluated": len(jobs),
        "returned": min(target, len(scored)),
    }


@remote_mcp.resource("resume://tailoring-guide")
def tailoring_guide() -> str:
    """Resume JSON contract + density rules (used by the full local agent)."""
    return (
        "Tailoring and compiling resumes requires the full apply agent running on "
        "the user's machine (encrypted profile + local/quota'd compile). Install it "
        "with one config block from https://internshipmatcher.com/developer — then "
        "the local server provides resume_compile and the complete tailoring guide."
    )


def streamable_app():
    """The ASGI app for app.mount('/mcp', ...)."""
    return remote_mcp.streamable_http_app()
