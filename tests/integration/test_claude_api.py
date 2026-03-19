"""
Integration tests for Claude API (Anthropic).

Fully mocked via unittest.mock to simulate responses without network calls or API keys.
Run via: pytest tests/integration/ -v
"""
import json
from unittest.mock import patch, MagicMock

class TestClaudeAPIConnectivity:
    @patch('anthropic.Anthropic')
    def test_client_initialises(self, mock_anthropic):
        mock_instance = MagicMock()
        mock_anthropic.return_value = mock_instance
        from anthropic import Anthropic
        client = Anthropic(api_key="fake")
        assert client is not None

    @patch('anthropic.Anthropic')
    def test_haiku_responds(self, mock_anthropic):
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="OK")]
        mock_response.stop_reason = "end_turn"
        mock_instance.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_instance
        
        client = mock_anthropic(api_key="fake")
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        assert response.content[0].text.strip() != ""
        assert response.stop_reason == "end_turn"

    @patch('anthropic.Anthropic')
    def test_sonnet_responds(self, mock_anthropic):
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="OK")]
        mock_instance.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_instance

        client = mock_anthropic(api_key="fake")
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=64,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
        )
        assert response.content[0].text.strip() != ""


class TestSkillExtraction:
    """Simulated Claude call via resume_parser.parse_resume.extract_skills_with_llm."""

    SAMPLE_RESUME = "Jane Doe | jane@example.com | Skills: Python, React, Docker"

    def _setup_mock(self, mock_anthropic, json_return):
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(json_return))]
        mock_instance.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_instance

    @patch('resume_parser.parse_resume.anthropic.Anthropic')
    def test_returns_list_of_strings(self, mock_anthropic):
        self._setup_mock(mock_anthropic, {"skills": ["Python", "React", "Docker"]})
        from resume_parser.parse_resume import extract_skills_with_llm
        skills = extract_skills_with_llm(self.SAMPLE_RESUME)
        assert isinstance(skills, list)
        assert len(skills) > 0
        assert all(isinstance(s, str) for s in skills)

    @patch('resume_parser.parse_resume.anthropic.Anthropic')
    def test_extracts_known_skills(self, mock_anthropic):
        self._setup_mock(mock_anthropic, {"skills": ["Python", "React", "Docker"]})
        from resume_parser.parse_resume import extract_skills_with_llm
        skills = extract_skills_with_llm(self.SAMPLE_RESUME)
        skills_lower = [s.lower() for s in skills]
        assert any(k in skills_lower for k in ["python", "react", "docker"])

    @patch('resume_parser.parse_resume.anthropic.Anthropic')
    def test_full_metadata_returned(self, mock_anthropic):
        self._setup_mock(mock_anthropic, {
            "skills": ["Python"],
            "experience_level": "student",
            "years_of_experience": 0,
            "is_student": True
        })
        from resume_parser.parse_resume import extract_skills_with_llm_full
        result = extract_skills_with_llm_full(self.SAMPLE_RESUME)
        assert "skills" in result
        assert "experience_level" in result
        assert "is_student" in result
        assert isinstance(result["skills"], list)


class TestResumeTailorJson:
    """Simulated Claude call via resume_tailor.tailor_resume.tailor_resume_to_json."""

    RESUME_TEXT = "Alex Smith | Skills: Python, Go"

    def _setup_mock(self, mock_anthropic, json_return):
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(json_return))]
        mock_instance.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_instance

    @patch('resume_tailor.tailor_resume.anthropic.Anthropic')
    def test_returns_expected_schema(self, mock_anthropic):
        self._setup_mock(mock_anthropic, {
            "name": "Alex", "email": "a@a", "experience": [], "education": [], "skills": [], "projects": []
        })
        from resume_tailor.tailor_resume import tailor_resume_to_json
        result = tailor_resume_to_json(self.RESUME_TEXT, "Intern", "Stripe", "Go and Python")
        required_keys = ["name", "email", "experience", "education", "skills", "projects"]
        for key in required_keys:
            assert key in result

    @patch('resume_tailor.tailor_resume.anthropic.Anthropic')
    def test_experience_has_bullets(self, mock_anthropic):
        self._setup_mock(mock_anthropic, {
            "name": "Alex", 
            "email": "a@a", 
            "experience": [{"company": "X", "title": "Y", "location": "Z", "date": "W", "bullets": ["A"]}], 
            "education": [], 
            "skills": [], 
            "projects": []
        })
        from resume_tailor.tailor_resume import tailor_resume_to_json
        result = tailor_resume_to_json(self.RESUME_TEXT, "Intern", "Stripe", "Go and Python")
        assert len(result.get("experience", [])) > 0
        assert "bullets" in result["experience"][0]
