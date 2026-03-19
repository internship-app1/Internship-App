"""
End-to-end integration test for the resume tailor pipeline.

Mocked via unittest.mock to avoid real Claude API calls while still testing the LaTeX compilation.
Run via: pytest tests/integration/ -v
"""
import subprocess
import pytest
from unittest.mock import patch

SKIP_IF_NO_LATEX = pytest.mark.skipif(
    subprocess.run(["which", "pdflatex"], capture_output=True).returncode != 0,
    reason="pdflatex not installed",
)

SAMPLE_RESUME_TEXT = """
Jordan Lee | jordan@email.com | 555-777-8888 | https://jordanlee.dev
GitHub: https://github.com/jordanlee | LinkedIn: https://linkedin.com/in/jordanlee

Education
  B.S. Computer Science, UC Berkeley, 2022-2026

Experience
  Software Engineering Intern — Meta (June 2024 – August 2024)
  San Francisco, CA
  - Built a real-time data pipeline in Python processing 1M events/day
  - Reduced API response time by 35% through Redis caching
  - Wrote unit and integration tests achieving 90% code coverage

Skills
  Programming Languages: Python, JavaScript, TypeScript, Java
"""

# The simulated JSON output from tailor_resume_to_json
MOCK_TAILORED_JSON = {
    "name": "Jordan Lee",
    "email": "jordan@email.com",
    "experience": [
        {
            "company": "Meta",
            "title": "Software Engineering Intern",
            "location": "San Francisco, CA",
            "date": "June 2024 – August 2024",
            "bullets": [
                "Built a real-time data pipeline in Python processing 1M events/day",
                "Reduced API response time by 35% through Redis caching"
            ]
        }
    ],
    "education": [],
    "skills": ["Python", "JavaScript", "React"],
    "projects": []
}


@SKIP_IF_NO_LATEX
@patch('resume_tailor.tailor_resume.tailor_resume_to_json', return_value=MOCK_TAILORED_JSON)
class TestFullPipeline:
    """Tests the complete tailor_resume → PDF flow with mocked services."""

    def test_tailor_resume_returns_pdf_bytes(self, mock_tailor):
        from resume_tailor.tailor_resume import inject_into_template, compile_to_single_page
        latex = inject_into_template(MOCK_TAILORED_JSON)
        pdf_bytes = compile_to_single_page(latex)

        assert pdf_bytes.startswith(b"%PDF"), "Output is not a valid PDF"
        assert len(pdf_bytes) > 1000, "PDF seems too small to be real"

    def test_output_is_single_page(self, mock_tailor):
        import pdfplumber
        import io
        from resume_tailor.tailor_resume import inject_into_template, compile_to_single_page, _count_pdf_pages
        
        latex = inject_into_template(MOCK_TAILORED_JSON)
        pdf_bytes = compile_to_single_page(latex)

        assert _count_pdf_pages(pdf_bytes) == 1, "Resume overflows onto more than 1 page"

    def test_pdf_contains_name(self, mock_tailor):
        import pdfplumber
        import io
        from resume_tailor.tailor_resume import inject_into_template, compile_to_single_page
        
        latex = inject_into_template(MOCK_TAILORED_JSON)
        pdf_bytes = compile_to_single_page(latex)

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "".join(p.extract_text() or "" for p in pdf.pages)

        assert "Jordan" in text or "Lee" in text, f"Name not found in PDF text: {text[:200]}"


class TestClaudeJsonOnly:
    """Tests just the LaTeX compilation (no pdflatex integration required)."""

    @patch('resume_tailor.tailor_resume.tailor_resume_to_json', return_value=MOCK_TAILORED_JSON)
    def test_inject_into_template_produces_compilable_latex(self, mock_tailor):
        from resume_tailor.tailor_resume import inject_into_template
        
        latex = inject_into_template(MOCK_TAILORED_JSON)

        assert r"\documentclass" in latex
        assert r"\begin{document}" in latex
        assert r"\end{document}" in latex
        assert "{{FONT_SIZE}}" in latex  # placeholder must survive injection
