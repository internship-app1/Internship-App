"""
Integration tests for Claude API (Anthropic).

Requires a real CLAUDE_API_KEY in the environment.
Run via: pytest tests/integration/ -v
"""
import os
import json
import pytest
import anthropic

PLACEHOLDER_VALUES = {"", "test-key", "placeholder"}


def _has_real_claude_key() -> bool:
    api_key = os.getenv("CLAUDE_API_KEY", "")
    return bool(api_key and api_key not in PLACEHOLDER_VALUES)


SKIP_IF_NO_KEY = pytest.mark.skipif(
    not _has_real_claude_key(),
    reason="Real CLAUDE_API_KEY not configured",
)


@SKIP_IF_NO_KEY
class TestClaudeAPIConnectivity:
    def test_client_initialises(self):
        """API key is valid and client can be created."""
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        assert client is not None

    def test_haiku_responds(self):
        """Haiku model (used by resume parser) returns a response."""
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        assert response.content[0].text.strip() != ""
        assert response.stop_reason == "end_turn"

    def test_sonnet_responds(self):
        """Sonnet model (used by resume tailor) returns a response."""
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        assert response.content[0].text.strip() != ""


@SKIP_IF_NO_KEY
class TestSkillExtraction:
    """Real Claude call via resume_parser.parse_resume.extract_skills_with_llm."""

    SAMPLE_RESUME = """
    Jane Doe | jane@example.com | 555-123-4567
    Education: B.S. Computer Science, MIT, 2021-2025
    Experience:
      Software Engineering Intern at Google (May-Aug 2024)
      - Built REST APIs using Python and FastAPI
      - Optimised PostgreSQL queries reducing latency by 40%
      - Deployed services on AWS using Docker and Kubernetes
    Skills: Python, JavaScript, React, PostgreSQL, Docker
    Projects:
      InternTracker — full-stack app (React, FastAPI, PostgreSQL)
    """

    def test_returns_list_of_strings(self):
        from resume_parser.parse_resume import extract_skills_with_llm
        skills = extract_skills_with_llm(self.SAMPLE_RESUME)
        assert isinstance(skills, list)
        assert len(skills) > 0
        assert all(isinstance(s, str) for s in skills)

    def test_extracts_known_skills(self):
        from resume_parser.parse_resume import extract_skills_with_llm
        skills = extract_skills_with_llm(self.SAMPLE_RESUME)
        skills_lower = [s.lower() for s in skills]
        # At least one of these clearly-stated skills should be extracted
        assert any(k in skills_lower for k in ["python", "react", "docker", "postgresql"])

    def test_full_metadata_returned(self):
        from resume_parser.parse_resume import extract_skills_with_llm_full
        result = extract_skills_with_llm_full(self.SAMPLE_RESUME)
        assert "skills" in result
        assert "experience_level" in result
        assert "is_student" in result
        assert isinstance(result["skills"], list)


@SKIP_IF_NO_KEY
class TestResumeTailorJson:
    """Real Claude call via resume_tailor.tailor_resume.tailor_resume_to_json."""

    RESUME_TEXT = """
    Alex Smith | alex@email.com | 555-999-0000
    Education: B.S. Computer Science, Stanford, 2022-2026
    Experience:
      Backend Intern at Stripe (Summer 2024)
      - Wrote Go microservices handling 10k req/s
      - Improved CI pipeline speed by 30%
    Skills: Python, Go, PostgreSQL, Redis, Docker
    """

    def test_returns_expected_schema(self):
        from resume_tailor.tailor_resume import tailor_resume_to_json
        result = tailor_resume_to_json(
            self.RESUME_TEXT,
            job_title="Software Engineer Intern",
            company="Cloudflare",
            job_description="Build distributed systems in Go and Python.",
        )
        required_keys = ["name", "email", "experience", "education", "skills", "projects"]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_experience_has_bullets(self):
        from resume_tailor.tailor_resume import tailor_resume_to_json
        result = tailor_resume_to_json(
            self.RESUME_TEXT,
            job_title="Backend Engineer Intern",
            company="Stripe",
            job_description="Work on payment infrastructure using Go and Python.",
        )
        assert len(result.get("experience", [])) > 0
        first_job = result["experience"][0]
        assert "bullets" in first_job
        assert len(first_job["bullets"]) > 0
