"""
Tests for resume_parser/parse_resume.py

Claude API calls are always mocked — no real API key needed.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from resume_parser.parse_resume import (
    extract_json_from_response,
    is_valid_resume,
)


# ---------------------------------------------------------------------------
# extract_json_from_response
# ---------------------------------------------------------------------------

class TestExtractJsonFromResponse:
    def test_plain_json(self):
        raw = '{"skills": ["Python"]}'
        assert extract_json_from_response(raw) == raw.strip()

    def test_json_code_block(self):
        raw = '```json\n{"skills": ["Python"]}\n```'
        result = extract_json_from_response(raw)
        assert result == '{"skills": ["Python"]}'

    def test_plain_code_block(self):
        raw = '```\n{"skills": ["Go"]}\n```'
        result = extract_json_from_response(raw)
        assert result == '{"skills": ["Go"]}'

    def test_strips_whitespace(self):
        raw = '  {"a": 1}  '
        assert extract_json_from_response(raw) == '{"a": 1}'


# ---------------------------------------------------------------------------
# is_valid_resume
# ---------------------------------------------------------------------------

class TestIsValidResume:
    def test_empty_string(self):
        assert is_valid_resume("") is False

    def test_too_short(self):
        assert is_valid_resume("skills education") is False

    def test_valid_resume(self):
        text = (
            "John Smith | john@email.com | 555-1234\n"
            "Education: B.S. Computer Science, State University 2021-2025\n"
            "Work Experience: Software Engineering Intern at Acme Corp\n"
            "Skills: Python, JavaScript, React\n"
            "Projects: Built an internship tracker web application"
        )
        assert is_valid_resume(text) is True

    def test_insufficient_indicators(self):
        # Has some words but fewer than 3 resume indicators
        text = "A" * 200  # long enough but no resume keywords
        assert is_valid_resume(text) is False


# ---------------------------------------------------------------------------
# extract_skills_with_llm (mocked Claude)
# ---------------------------------------------------------------------------

class TestExtractSkillsWithLlm:
    def _mock_claude(self, payload: dict):
        msg = MagicMock()
        msg.content = [MagicMock(text=json.dumps(payload))]
        return msg

    def test_returns_skills_list(self):
        from resume_parser.parse_resume import extract_skills_with_llm

        payload = {
            "skills": ["Python", "React"],
            "experience_level": "student",
            "years_of_experience": 0,
            "is_student": True,
            "confidence_notes": "test",
        }

        with patch("resume_parser.parse_resume.anthropic.Anthropic") as MockClaude:
            MockClaude.return_value.messages.create.return_value = self._mock_claude(payload)
            skills = extract_skills_with_llm("resume text here")

        assert skills == ["Python", "React"]

    def test_empty_skills_list(self):
        from resume_parser.parse_resume import extract_skills_with_llm

        payload = {"skills": [], "experience_level": "student",
                   "years_of_experience": 0, "is_student": True, "confidence_notes": ""}

        with patch("resume_parser.parse_resume.anthropic.Anthropic") as MockClaude:
            MockClaude.return_value.messages.create.return_value = self._mock_claude(payload)
            skills = extract_skills_with_llm("short text")

        assert skills == []

    def test_raises_on_api_error(self):
        from resume_parser.parse_resume import extract_skills_with_llm

        with patch("resume_parser.parse_resume.anthropic.Anthropic") as MockClaude:
            MockClaude.return_value.messages.create.side_effect = Exception("API down")
            with pytest.raises(Exception, match="LLM skill extraction failed"):
                extract_skills_with_llm("text")


# ---------------------------------------------------------------------------
# parse_resume (mocked pdfplumber + Claude)
# ---------------------------------------------------------------------------

class TestParseResume:
    RESUME_TEXT = (
        "Jane Doe | jane@example.com\n"
        "Education: B.S. Computer Science, MIT 2021-2025\n"
        "Work Experience: Intern at Google — built production features\n"
        "Skills: Python, TypeScript, Docker, PostgreSQL\n"
        "Projects: Resume matcher using React and FastAPI"
    )

    def _mock_pdf(self, text: str):
        """Return a pdfplumber context-manager mock that yields the given text."""
        page = MagicMock()
        page.extract_text.return_value = text
        pdf = MagicMock()
        pdf.__enter__ = lambda s: s
        pdf.__exit__ = MagicMock(return_value=False)
        pdf.pages = [page]
        return pdf

    def _mock_llm_response(self, skills):
        payload = {
            "skills": skills,
            "experience_level": "student",
            "years_of_experience": 0,
            "is_student": True,
            "confidence_notes": "test",
        }
        msg = MagicMock()
        msg.content = [MagicMock(text=json.dumps(payload))]
        return msg

    def test_returns_skills_text_metadata(self):
        from resume_parser.parse_resume import parse_resume

        with patch("resume_parser.parse_resume.pdfplumber.open",
                   return_value=self._mock_pdf(self.RESUME_TEXT)), \
             patch("resume_parser.parse_resume.anthropic.Anthropic") as MockClaude:
            MockClaude.return_value.messages.create.return_value = \
                self._mock_llm_response(["Python", "TypeScript"])
            skills, text, metadata = parse_resume(b"fake-pdf", "resume.pdf")

        assert "Python" in skills
        assert "Jane Doe" in text
        assert "experience_level" in metadata

    def test_empty_pdf_returns_empty(self):
        from resume_parser.parse_resume import parse_resume

        with patch("resume_parser.parse_resume.pdfplumber.open",
                   return_value=self._mock_pdf("")):
            skills, text, metadata = parse_resume(b"fake-pdf", "resume.pdf")

        assert skills == []
        assert text == ""
        assert metadata == {}
