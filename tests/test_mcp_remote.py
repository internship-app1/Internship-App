"""Tests for the hosted /mcp zero-install tier.

The backend's default local venv may be Python 3.9, where the mcp SDK is not
installed. These tests run when mcp is available (prod/3.11 path) and skip
cleanly otherwise.
"""
from types import SimpleNamespace

import pytest

mcp_remote = pytest.importorskip("mcp_remote")


def _ctx(key=None, header_key=None):
    headers = {}
    query_params = {}
    if header_key:
        headers["x-api-key"] = header_key
    if key:
        query_params["key"] = key
    request = SimpleNamespace(headers=headers, query_params=query_params)
    return SimpleNamespace(request_context=SimpleNamespace(request=request))


class TestHostedMcpAuth:
    def test_key_from_query_param(self, monkeypatch):
        seen = {}

        def verify(raw):
            seen["raw"] = raw
            return "user_query"

        monkeypatch.setattr(mcp_remote, "verify_api_key", verify)
        assert mcp_remote._require_user(_ctx(key="im_live_query")) == "user_query"
        assert seen["raw"] == "im_live_query"

    def test_header_takes_precedence_over_query(self, monkeypatch):
        seen = {}

        def verify(raw):
            seen["raw"] = raw
            return "user_header"

        monkeypatch.setattr(mcp_remote, "verify_api_key", verify)
        assert mcp_remote._require_user(
            _ctx(key="im_live_query", header_key="im_live_header")
        ) == "user_header"
        assert seen["raw"] == "im_live_header"

    def test_bad_key_has_actionable_error(self, monkeypatch):
        monkeypatch.setattr(mcp_remote, "verify_api_key", lambda raw: None)
        with pytest.raises(ValueError) as exc:
            mcp_remote._require_user(_ctx(key="bad"))
        assert "Generate a key" in str(exc.value)
        assert "/developer" in str(exc.value)


class TestHostedMcpTools:
    def test_jobs_list_is_discovery_only_and_authenticates(self, monkeypatch):
        monkeypatch.setattr(mcp_remote, "verify_api_key", lambda raw: "user")
        monkeypatch.setattr(
            mcp_remote,
            "_fetch_jobs",
            lambda *args: [{"job_hash": "h1", "company": "Acme", "title": "SWE Intern"}],
        )
        monkeypatch.setattr(mcp_remote, "_job_summary", lambda job: {"job_hash": job["job_hash"]})

        out = mcp_remote.jobs_list(_ctx(key="im_live_ok"), limit=10)

        assert out == {
            "jobs": [{"job_hash": "h1"}],
            "total": 1,
            "limit": 10,
            "offset": 0,
        }

    def test_jobs_prefilter_uses_small_profile_not_resume_text(self, monkeypatch):
        monkeypatch.setattr(mcp_remote, "verify_api_key", lambda raw: "user")
        monkeypatch.setattr(mcp_remote, "_fetch_jobs", lambda *args: [{"job_hash": "h1"}])

        seen = {}

        def score(profile, jobs):
            seen["profile"] = profile
            seen["jobs"] = jobs
            return [{"job_hash": "h1", "combined_score": 90}]

        monkeypatch.setattr(mcp_remote, "prefilter_and_score", score)

        out = mcp_remote.jobs_prefilter(
            _ctx(key="im_live_ok"),
            resume_profile={"skills": ["python"], "experience_level": "student"},
            target_count=5,
        )

        assert seen["profile"] == {"skills": ["python"], "experience_level": "student"}
        assert out["candidates"][0]["combined_score"] == 90
