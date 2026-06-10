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
