"""
MCP /api/v1 surface — deterministic, per-user-API-key-authenticated endpoints
consumed by the internship-mcp client.

Prime Directive: NO Claude calls anywhere in this module. All inference
(skill extraction, ranking, bullet rewriting) is done by the calling agent;
these endpoints only expose data and deterministic computation.

Two routers live here:
  - v1_app           — FastAPI sub-app mounted at /api/v1 (X-API-Key auth).
                       Being a sub-app gives it its own OpenAPI spec at
                       /api/v1/openapi.json — the published MCP contract.
  - developer_router — Clerk-JWT-authenticated key CRUD for the /developer page,
                       included on the main app.
"""
import asyncio
import hashlib
import json
import logging
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from auth import require_api_key_user, require_user
from job_database import (
    create_api_key,
    get_active_jobs,
    get_job_by_hash,
    get_new_jobs_since,
    list_api_keys,
    revoke_api_key,
)
from matching.matcher import prefilter_and_score
from resume_tailor.tailor_resume import compile_resume_json_to_pdf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiting — keyed by API-key prefix so limits are per key, not per IP
# ---------------------------------------------------------------------------

def _api_key_rate_limit_key(request: Request) -> str:
    raw = request.headers.get("X-API-Key", "")
    return f"apikey:{raw[:12]}" if raw else f"ip:{request.client.host if request.client else 'unknown'}"


_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
_TRACK_USAGE = os.getenv("TRACK_USAGE", "true").strip().lower() == "true"
v1_limiter = Limiter(
    key_func=_api_key_rate_limit_key, storage_uri=_REDIS_URL, enabled=_TRACK_USAGE
)

v1_app = FastAPI(
    title="Internship Matcher MCP API",
    version="1.0.0",
    description=(
        "Deterministic data plane for the internship-mcp client. "
        "All AI reasoning happens in the calling agent — these endpoints never "
        "invoke a model. Auth: per-user X-API-Key from /developer."
    ),
)
v1_app.state.limiter = v1_limiter
v1_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Schemas (the OpenAPI contract internship-mcp validates against in CI)
# ---------------------------------------------------------------------------

class JobSummary(BaseModel):
    job_hash: str
    company: str
    title: str
    location: str
    apply_link: str
    source: Optional[str] = None
    required_skills: List[str] = []
    days_since_posted: Optional[int] = None
    date_posted: Optional[str] = None
    description_preview: str = ""


class JobsResponse(BaseModel):
    jobs: List[JobSummary]
    total: int
    limit: int
    offset: int


class JobDetail(BaseModel):
    job_hash: str
    company: str
    title: str
    location: str
    apply_link: str
    source: Optional[str] = None
    required_skills: List[str] = []
    description: Optional[str] = None
    job_requirements: Optional[str] = None


class ResumeProfile(BaseModel):
    """Small PII-free profile object — the ONLY resume-derived data allowed
    across the wire on the prefilter path."""
    skills: List[str]
    experience_level: str = Field(pattern="^(student|entry_level|experienced)$")
    years_of_experience: int = 0
    location: Optional[str] = None
    willing_to_relocate: bool = False
    remote_ok: bool = False


class PrefilterFilters(BaseModel):
    since_hours: Optional[int] = None
    max_days_old: int = 30
    location: Optional[str] = None
    q: Optional[str] = None


class PrefilterRequest(BaseModel):
    resume_profile: ResumeProfile
    filters: Optional[PrefilterFilters] = None
    target_count: int = 40


class PrefilterCandidate(BaseModel):
    job_hash: str
    company: str
    title: str
    location: str
    apply_link: str
    keyword_score: int
    metadata_score: int
    combined_score: int
    skill_matches: List[str]
    skill_gaps: List[str]
    hard_filter_passed: bool
    description_preview: str


class PrefilterResponse(BaseModel):
    candidates: List[PrefilterCandidate]
    evaluated: int
    returned: int


class CompileOptions(BaseModel):
    font_anchor: int = 11
    spacing: str = Field(default="tight", pattern="^(tight|normal|relaxed)$")


class CompileRequest(BaseModel):
    resume_json: dict
    options: CompileOptions = CompileOptions()


class CompileResponse(BaseModel):
    pdf_base64: str
    diagnostics: dict


# ---------------------------------------------------------------------------
# Shared job fetch/filter helpers
# ---------------------------------------------------------------------------

def _job_days_since_posted(job: Dict) -> Optional[int]:
    meta = job.get("metadata") or {}
    return meta.get("days_since_posted")


def _fetch_jobs(
    since_hours: Optional[int],
    max_days_old: int,
    location: Optional[str],
    q: Optional[str],
) -> List[Dict]:
    if since_hours:
        jobs = get_new_jobs_since(hours=since_hours, max_days_old=max_days_old)
    else:
        jobs = get_active_jobs(max_days_old=max_days_old)
    if location:
        loc = location.lower()
        jobs = [j for j in jobs if loc in (j.get("location") or "").lower()]
    if q:
        needle = q.lower()
        jobs = [
            j for j in jobs
            if needle in (j.get("title") or "").lower()
            or needle in (j.get("company") or "").lower()
            or needle in (j.get("description") or "").lower()
        ]
    return jobs


def _job_summary(job: Dict) -> Dict:
    meta = job.get("metadata") or {}
    return {
        "job_hash": job.get("job_hash", ""),
        "company": job.get("company", ""),
        "title": job.get("title", ""),
        "location": job.get("location", ""),
        "apply_link": job.get("apply_link", ""),
        "source": job.get("source"),
        "required_skills": job.get("required_skills") or [],
        "days_since_posted": meta.get("days_since_posted"),
        "date_posted": meta.get("date_posted"),
        "description_preview": (job.get("description") or "")[:500],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@v1_app.get("/jobs", response_model=JobsResponse)
@v1_limiter.limit("120/hour")
async def v1_jobs(
    request: Request,
    since_hours: Optional[int] = None,
    max_days_old: int = 30,
    location: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
    user_id: str = Depends(require_api_key_user),
):
    """List active internship listings (deterministic — straight from the jobs DB)."""
    limit = max(1, min(limit, 500))
    jobs = await asyncio.to_thread(_fetch_jobs, since_hours, max_days_old, location, q)
    page = jobs[offset:offset + limit]
    return {
        "jobs": [_job_summary(j) for j in page],
        "total": len(jobs),
        "limit": limit,
        "offset": offset,
    }


@v1_app.get("/jobs/{job_hash}", response_model=JobDetail)
@v1_limiter.limit("120/hour")
async def v1_job_detail(
    request: Request,
    job_hash: str,
    user_id: str = Depends(require_api_key_user),
):
    """Full job record including the untruncated description."""
    job = await asyncio.to_thread(get_job_by_hash, job_hash)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job_hash")
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


@v1_app.post("/jobs/prefilter", response_model=PrefilterResponse)
@v1_limiter.limit("120/hour")
async def v1_prefilter(
    request: Request,
    body: PrefilterRequest,
    user_id: str = Depends(require_api_key_user),
):
    """Deterministic prefilter + scoring. Quick mode = trust combined_score;
    think-deeper = the agent fetches full JDs for its shortlist and re-ranks itself."""
    f = body.filters or PrefilterFilters()
    jobs = await asyncio.to_thread(
        _fetch_jobs, f.since_hours, f.max_days_old, f.location, f.q
    )
    scored = await asyncio.to_thread(
        prefilter_and_score, body.resume_profile.model_dump(), jobs
    )
    target = max(1, min(body.target_count, 200))
    return {
        "candidates": scored[:target],
        "evaluated": len(jobs),
        "returned": min(target, len(scored)),
    }


# ---- Remote compile fallback (opt-in, rate-limited, concurrency-capped) ----

COMPILE_CONCURRENCY = int(os.getenv("COMPILE_CONCURRENCY", "3"))
_compile_semaphore = asyncio.Semaphore(COMPILE_CONCURRENCY)
_compile_cache: Dict[str, tuple] = {}   # sha256(resume_json+options) -> (pdf, diag)
_COMPILE_CACHE_MAX = 64


def _compile_cache_key(resume_json: dict, options: CompileOptions) -> str:
    payload = json.dumps(
        {"resume_json": resume_json, "options": options.model_dump()},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@v1_app.post("/resume/compile", response_model=CompileResponse)
@v1_limiter.limit("60/day")
async def v1_compile(
    request: Request,
    body: CompileRequest,
    response: Response,
    user_id: str = Depends(require_api_key_user),
):
    """FALLBACK compile path for uvx users without local TeX. Docker users
    compile locally — keep it that way; this endpoint is concurrency-capped."""
    import base64

    cache_key = _compile_cache_key(body.resume_json, body.options)
    cached = _compile_cache.get(cache_key)
    if cached:
        pdf_bytes, diagnostics = cached
        return {"pdf_base64": base64.b64encode(pdf_bytes).decode(), "diagnostics": diagnostics}

    if _compile_semaphore.locked():
        # All compile slots busy — shed load instead of queueing unboundedly.
        raise HTTPException(
            status_code=429,
            detail="Compile capacity busy — retry shortly or compile locally (Docker)",
            headers={"Retry-After": "10"},
        )

    async with _compile_semaphore:
        try:
            pdf_bytes, diagnostics = await asyncio.to_thread(
                compile_resume_json_to_pdf,
                body.resume_json,
                body.options.font_anchor,
                body.options.spacing,
            )
        except Exception as e:
            logger.error("remote compile failed: %s", e)
            raise HTTPException(status_code=422, detail=f"Compile failed: {e}")

    if len(_compile_cache) >= _COMPILE_CACHE_MAX:
        _compile_cache.pop(next(iter(_compile_cache)))
    _compile_cache[cache_key] = (pdf_bytes, diagnostics)
    return {"pdf_base64": base64.b64encode(pdf_bytes).decode(), "diagnostics": diagnostics}


# ---------------------------------------------------------------------------
# Developer key CRUD (Clerk JWT auth — used by the /developer page)
# ---------------------------------------------------------------------------

developer_router = APIRouter(prefix="/api/developer", tags=["developer"])


class CreateKeyRequest(BaseModel):
    name: Optional[str] = None


@developer_router.get("/keys")
async def developer_list_keys(user_id: str = Depends(require_user)):
    return {"keys": await asyncio.to_thread(list_api_keys, user_id)}


@developer_router.post("/keys")
async def developer_create_key(
    body: CreateKeyRequest, user_id: str = Depends(require_user)
):
    raw, meta = await asyncio.to_thread(create_api_key, user_id, body.name)
    # raw is returned exactly once and never stored
    return {"key": raw, "meta": meta}


@developer_router.delete("/keys/{key_id}")
async def developer_revoke_key(key_id: int, user_id: str = Depends(require_user)):
    ok = await asyncio.to_thread(revoke_api_key, user_id, key_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"ok": True}
