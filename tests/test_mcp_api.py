"""
Tests for the MCP /api/v1 surface: ApiKey auth plane, deterministic
endpoints, prefilter scoring, and the compile core.

NO Anthropic calls anywhere in this path — if one of these tests triggers a
model call, the Prime Directive is broken.
"""
import shutil

import pytest
from fastapi.testclient import TestClient

from job_database import (
    create_api_key,
    init_database,
    list_api_keys,
    revoke_api_key,
    verify_api_key,
)
from matching.matcher import prefilter_and_score


@pytest.fixture(scope="module", autouse=True)
def _file_backed_db(tmp_path_factory):
    """The conftest-wide :memory: SQLite is per-connection, so tables vanish
    across the threads TestClient/asyncio.to_thread use. Point job_database at
    a temp FILE database for this module instead."""
    import job_database as jd
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path_factory.mktemp("mcpdb") / "test.db"
    old_engine, old_sessionlocal = jd.engine, jd.SessionLocal
    jd.engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    jd.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=jd.engine)
    jd.Base.metadata.create_all(jd.engine)
    yield
    jd.engine, jd.SessionLocal = old_engine, old_sessionlocal


@pytest.fixture()
def client():
    import app as appmod
    return TestClient(appmod.app)


@pytest.fixture()
def api_key():
    raw, _meta = create_api_key("user_mcp_test", "pytest key")
    return raw


SAMPLE_JOBS = [
    {
        "job_hash": "a" * 64,
        "company": "Acme",
        "title": "Software Engineer Intern",
        "location": "San Francisco, CA",
        "apply_link": "https://boards.greenhouse.io/acme/jobs/1",
        "description": "Build web apps with React and Python. Internship for students.",
        "required_skills": ["Python", "React"],
        "metadata": {"days_since_posted": 2},
    },
    {
        "job_hash": "b" * 64,
        "company": "BigCo",
        "title": "Senior Staff Architect",
        "location": "New York, NY",
        "apply_link": "https://jobs.lever.co/bigco/2",
        "description": "10+ years of experience required.",
        "required_skills": ["Go", "Kubernetes"],
        "metadata": {"days_since_posted": 5},
    },
]


# ---------------------------------------------------------------------------
# ApiKey lifecycle
# ---------------------------------------------------------------------------

class TestApiKeyLifecycle:
    def test_create_returns_raw_once_and_stores_hash_only(self):
        raw, meta = create_api_key("user_a", "k1")
        assert raw.startswith("im_live_") and len(raw) == 8 + 32
        assert meta["key_prefix"] == raw[:12]
        # Raw key never appears in listings
        for k in list_api_keys("user_a"):
            assert raw not in str(k)

    def test_verify_roundtrip_and_revoke(self):
        raw, meta = create_api_key("user_b", None)
        assert verify_api_key(raw) == "user_b"
        assert revoke_api_key("user_b", meta["id"]) is True
        assert verify_api_key(raw) is None

    def test_verify_rejects_garbage(self):
        assert verify_api_key("") is None
        assert verify_api_key(None) is None
        assert verify_api_key("im_live_" + "x" * 32) is None
        assert verify_api_key("not-even-the-right-shape") is None

    def test_revoke_other_users_key_fails(self):
        _raw, meta = create_api_key("owner", "k")
        assert revoke_api_key("attacker", meta["id"]) is False


# ---------------------------------------------------------------------------
# /api/v1 endpoints
# ---------------------------------------------------------------------------

class TestV1Endpoints:
    def test_jobs_requires_key(self, client):
        assert client.get("/api/v1/jobs").status_code == 401
        assert client.get(
            "/api/v1/jobs", headers={"X-API-Key": "im_live_" + "z" * 32}
        ).status_code == 401

    def test_jobs_with_valid_key(self, client, api_key):
        r = client.get("/api/v1/jobs", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        body = r.json()
        assert set(body) == {"jobs", "total", "limit", "offset"}

    def test_job_detail_404(self, client, api_key):
        r = client.get("/api/v1/jobs/" + "f" * 64, headers={"X-API-Key": api_key})
        assert r.status_code == 404

    def test_prefilter_validates_experience_level(self, client, api_key):
        r = client.post(
            "/api/v1/jobs/prefilter",
            headers={"X-API-Key": api_key},
            json={"resume_profile": {"skills": ["python"],
                                     "experience_level": "recent_graduate"}},
        )
        assert r.status_code == 422  # enum is exactly student|entry_level|experienced

    def test_prefilter_happy_path(self, client, api_key):
        r = client.post(
            "/api/v1/jobs/prefilter",
            headers={"X-API-Key": api_key},
            json={
                "resume_profile": {"skills": ["python", "react"],
                                   "experience_level": "student"},
                "target_count": 10,
            },
        )
        assert r.status_code == 200
        assert set(r.json()) == {"candidates", "evaluated", "returned"}

    def test_rate_limit_buckets_unique_per_key(self):
        """Regression: raw[:12] only carried 4 random chars past 'im_live_',
        so distinct keys could collide into one throttle bucket."""
        from types import SimpleNamespace

        from mcp_api import _api_key_rate_limit_key

        def req(key=None):
            return SimpleNamespace(
                headers={"X-API-Key": key} if key else {}, client=None
            )

        # Two distinct keys sharing the same first 12 chars → distinct buckets
        a = "im_live_abcd" + "1" * 28
        b = "im_live_abcd" + "2" * 28
        assert _api_key_rate_limit_key(req(a)) != _api_key_rate_limit_key(req(b))
        # Same key → stable bucket
        assert _api_key_rate_limit_key(req(a)) == _api_key_rate_limit_key(req(a))
        # No key → IP bucket, not an apikey bucket
        assert _api_key_rate_limit_key(req()).startswith("ip:")

    def test_concurrent_compiles_shed_excess_with_429(self, api_key, monkeypatch):
        """Regression: Semaphore.locked() was a point-in-time check, so
        concurrent requests could queue instead of receiving 429. With bounded
        admission, exactly COMPILE_CONCURRENCY requests run and the rest are
        rejected with Retry-After."""
        import asyncio
        import time

        import httpx

        import app as appmod
        import mcp_api

        def slow_compile(resume_json, font_anchor, spacing):
            time.sleep(0.4)
            return b"%PDF-fake", {"pages": 1}

        monkeypatch.setattr(mcp_api, "compile_resume_json_to_pdf", slow_compile)
        n_extra = 2
        n_total = mcp_api.COMPILE_CONCURRENCY + n_extra

        async def run():
            transport = httpx.ASGITransport(app=appmod.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as ac:
                return await asyncio.gather(*[
                    ac.post(
                        "/api/v1/resume/compile",
                        headers={"X-API-Key": api_key},
                        # distinct payloads so the content cache can't satisfy any
                        json={"resume_json": {"name": f"r{i}"}},
                    )
                    for i in range(n_total)
                ])

        responses = asyncio.run(run())
        codes = [r.status_code for r in responses]
        assert codes.count(200) == mcp_api.COMPILE_CONCURRENCY, codes
        assert codes.count(429) == n_extra, codes
        rejected = next(r for r in responses if r.status_code == 429)
        assert "Retry-After" in rejected.headers
        # Slots were released — a follow-up request is admitted again
        async def one_more():
            transport = httpx.ASGITransport(app=appmod.app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as ac:
                return await ac.post(
                    "/api/v1/resume/compile",
                    headers={"X-API-Key": api_key},
                    json={"resume_json": {"name": "after"}},
                )
        assert asyncio.run(one_more()).status_code == 200

    def test_openapi_contract_published(self, client):
        r = client.get("/api/v1/openapi.json")
        assert r.status_code == 200
        paths = r.json()["paths"]
        for p in ("/jobs", "/jobs/{job_hash}", "/jobs/prefilter", "/resume/compile"):
            assert p in paths


# ---------------------------------------------------------------------------
# prefilter_and_score (deterministic, LLM-free)
# ---------------------------------------------------------------------------

class TestPrefilterAndScore:
    PROFILE = {
        "skills": ["python", "react"],
        "experience_level": "student",
        "years_of_experience": 1,
        "location": "San Francisco, CA",
        "willing_to_relocate": True,
        "remote_ok": True,
    }

    def test_scores_and_shape(self):
        out = prefilter_and_score(self.PROFILE, SAMPLE_JOBS)
        assert len(out) == 2
        for row in out:
            assert {"job_hash", "keyword_score", "metadata_score",
                    "combined_score", "skill_matches", "skill_gaps",
                    "hard_filter_passed"} <= set(row)

    def test_hard_filter_excludes_senior_role_for_student(self):
        out = {r["job_hash"]: r for r in prefilter_and_score(self.PROFILE, SAMPLE_JOBS)}
        assert out["a" * 64]["hard_filter_passed"] is True
        assert out["b" * 64]["hard_filter_passed"] is False

    def test_skill_matching(self):
        out = {r["job_hash"]: r for r in prefilter_and_score(self.PROFILE, SAMPLE_JOBS)}
        assert set(out["a" * 64]["skill_matches"]) == {"Python", "React"}
        assert out["a" * 64]["skill_gaps"] == []
        assert set(out["b" * 64]["skill_gaps"]) == {"Go", "Kubernetes"}

    def test_deterministic(self):
        assert prefilter_and_score(self.PROFILE, SAMPLE_JOBS) == \
            prefilter_and_score(self.PROFILE, SAMPLE_JOBS)


# ---------------------------------------------------------------------------
# Weekly remote-compile quota (15/week per user, API-key plane)
# ---------------------------------------------------------------------------

class TestRemoteCompileQuota:
    def _fill_quota(self, user_id):
        from job_database import get_db
        from quota import WEEKLY_REMOTE_COMPILE_LIMIT, record_remote_compile

        db = get_db()
        try:
            for _ in range(WEEKLY_REMOTE_COMPILE_LIMIT):
                record_remote_compile(db, user_id, key_prefix="im_live_test")
            db.commit()
        finally:
            db.close()

    def test_quota_status_counts_and_resets(self):
        from job_database import get_db
        from quota import (
            WEEKLY_REMOTE_COMPILE_LIMIT,
            get_remote_compile_quota_status,
            record_remote_compile,
        )

        db = get_db()
        try:
            status = get_remote_compile_quota_status(db, "quota_user")
            assert status == {"limit": WEEKLY_REMOTE_COMPILE_LIMIT, "used": 0,
                              "remaining": WEEKLY_REMOTE_COMPILE_LIMIT, "reset_at": None}
            record_remote_compile(db, "quota_user", key_prefix="im_live_abcd")
            db.commit()
            status = get_remote_compile_quota_status(db, "quota_user")
            assert status["used"] == 1
            assert status["remaining"] == WEEKLY_REMOTE_COMPILE_LIMIT - 1
            assert status["reset_at"] is not None
        finally:
            db.close()

    def test_quota_is_per_user(self):
        from job_database import get_db
        from quota import get_remote_compile_quota_status

        self._fill_quota("user_full")
        db = get_db()
        try:
            assert get_remote_compile_quota_status(db, "user_full")["remaining"] == 0
            assert get_remote_compile_quota_status(db, "user_other")["used"] == 0
        finally:
            db.close()

    def test_exhausted_quota_returns_429_before_compiling(self, client, monkeypatch):
        import mcp_api

        raw, _ = create_api_key("user_quota_429", "q")
        self._fill_quota("user_quota_429")

        def _boom(*a, **k):
            raise AssertionError("compile must not run once quota is exhausted")

        monkeypatch.setattr(mcp_api, "compile_resume_json_to_pdf", _boom)
        r = client.post(
            "/api/v1/resume/compile",
            headers={"X-API-Key": raw},
            json={"resume_json": {"name": "x"}},
        )
        assert r.status_code == 429
        assert "Weekly remote-compile quota" in r.json()["detail"]

    def test_successful_compile_records_usage_with_key_prefix(self, client, monkeypatch):
        import mcp_api
        from job_database import RemoteCompileLog, get_db

        raw, _ = create_api_key("user_quota_rec", "q")
        monkeypatch.setattr(
            mcp_api, "compile_resume_json_to_pdf",
            lambda *a, **k: (b"%PDF-fake", {"pages": 1}),
        )
        r = client.post(
            "/api/v1/resume/compile",
            headers={"X-API-Key": raw},
            json={"resume_json": {"name": "record-me"}},
        )
        assert r.status_code == 200
        db = get_db()
        try:
            row = db.query(RemoteCompileLog).filter(
                RemoteCompileLog.user_id == "user_quota_rec"
            ).one()
            assert row.key_prefix == raw[:12]
        finally:
            db.close()

    def test_cache_hit_does_not_consume_quota(self, client, monkeypatch):
        import mcp_api
        from job_database import get_db
        from quota import get_remote_compile_quota_status

        raw, _ = create_api_key("user_quota_cache", "q")
        monkeypatch.setattr(
            mcp_api, "compile_resume_json_to_pdf",
            lambda *a, **k: (b"%PDF-fake", {"pages": 1}),
        )
        payload = {"resume_json": {"name": "cache-me"}}
        assert client.post("/api/v1/resume/compile",
                           headers={"X-API-Key": raw}, json=payload).status_code == 200
        assert client.post("/api/v1/resume/compile",
                           headers={"X-API-Key": raw}, json=payload).status_code == 200
        db = get_db()
        try:
            assert get_remote_compile_quota_status(db, "user_quota_cache")["used"] == 1
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Compile core (requires pdflatex — skipped on machines without TeX)
# ---------------------------------------------------------------------------

needs_pdflatex = pytest.mark.skipif(
    shutil.which("pdflatex") is None, reason="pdflatex not installed"
)


@needs_pdflatex
class TestCompileCore:
    def test_compile_core_no_llm(self, sample_resume_data, monkeypatch):
        """The deterministic core must never construct an Anthropic client."""
        import anthropic
        from resume_tailor.tailor_resume import compile_resume_json_to_pdf

        def _boom(*a, **k):
            raise AssertionError("Prime Directive violation: model call in compile core")

        monkeypatch.setattr(anthropic, "Anthropic", _boom)
        pdf, diag = compile_resume_json_to_pdf(sample_resume_data)
        assert pdf.startswith(b"%PDF")
        assert diag["pages"] == 1
        assert diag["font_size"] in (14, 12, 11, 10, 9, 8)
        assert diag["spacing"] in ("tight", "normal", "relaxed")
        assert isinstance(diag["widows"], list)

    def test_compile_is_deterministic_input_to_latex(self, sample_resume_data):
        """Golden seam: the LaTeX injected for a fixed JSON is byte-stable."""
        from resume_tailor.tailor_resume import inject_into_template

        assert inject_into_template(sample_resume_data) == \
            inject_into_template(sample_resume_data)
