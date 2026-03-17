"""
End-to-end integration test for the resume tailor pipeline.

Requires:
  - CLAUDE_API_KEY  (real Claude API call)
  - pdflatex        (system binary, installed in CI via texlive)

Run via: pytest tests/integration/ -v
"""
import os
import subprocess
import pytest

SKIP_IF_NO_KEY = pytest.mark.skipif(
    not os.getenv("CLAUDE_API_KEY"),
    reason="CLAUDE_API_KEY not set",
)

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

  Teaching Assistant — UC Berkeley (Jan 2024 – May 2024)
  Berkeley, CA
  - Led weekly labs for 60 students on data structures and algorithms
  - Graded assignments and provided written feedback

Skills
  Programming Languages: Python, JavaScript, TypeScript, Java
  Frameworks: React, FastAPI, Django, Node.js
  Tools: Git, Docker, PostgreSQL, Redis, AWS

Projects
  internshipmatcher (Python, React, PostgreSQL) — 2024
  - Full-stack job matching app with AI-powered resume analysis
  - Deployed on AWS with Docker; 200+ active users

  AlgoVisualiser (TypeScript, React) — 2023
  - Interactive algorithm visualisation tool with 500 GitHub stars
"""


@SKIP_IF_NO_KEY
@SKIP_IF_NO_LATEX
class TestFullPipeline:
    """Tests the complete tailor_resume → PDF flow with real services."""

    def test_tailor_resume_returns_pdf_bytes(self):
        """Full pipeline: resume text → Claude JSON → LaTeX → PDF bytes."""
        from resume_tailor.tailor_resume import tailor_resume_to_json, inject_into_template, compile_to_single_page

        data = tailor_resume_to_json(
            SAMPLE_RESUME_TEXT,
            job_title="Software Engineer Intern",
            company="Stripe",
            job_description=(
                "Build reliable payment infrastructure using Python and Go. "
                "Work with distributed systems, REST APIs, and PostgreSQL."
            ),
        )
        latex = inject_into_template(data)
        pdf_bytes = compile_to_single_page(latex)

        assert pdf_bytes.startswith(b"%PDF"), "Output is not a valid PDF"
        assert len(pdf_bytes) > 1000, "PDF seems too small to be real"

    def test_output_is_single_page(self):
        """PDF produced by compile_to_single_page must be exactly 1 page."""
        import pdfplumber
        import io
        from resume_tailor.tailor_resume import (
            tailor_resume_to_json,
            inject_into_template,
            compile_to_single_page,
            _count_pdf_pages,
        )

        data = tailor_resume_to_json(
            SAMPLE_RESUME_TEXT,
            job_title="Backend Engineer Intern",
            company="Cloudflare",
            job_description="Distributed systems, Python, Go, networking.",
        )
        latex = inject_into_template(data)
        pdf_bytes = compile_to_single_page(latex)

        assert _count_pdf_pages(pdf_bytes) == 1, "Resume overflows onto more than 1 page"

    def test_pdf_contains_name(self):
        """Candidate name from resume should appear in the compiled PDF text."""
        import pdfplumber
        import io
        from resume_tailor.tailor_resume import (
            tailor_resume_to_json,
            inject_into_template,
            compile_to_single_page,
        )

        data = tailor_resume_to_json(
            SAMPLE_RESUME_TEXT,
            job_title="SWE Intern",
            company="Acme",
            job_description="Python, React, APIs.",
        )
        latex = inject_into_template(data)
        pdf_bytes = compile_to_single_page(latex)

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text = "".join(p.extract_text() or "" for p in pdf.pages)

        # Claude should preserve the candidate's name
        assert "Jordan" in text or "Lee" in text, f"Name not found in PDF text: {text[:200]}"


@SKIP_IF_NO_KEY
class TestClaudeJsonOnly:
    """Tests just the Claude call (no pdflatex required)."""

    def test_inject_into_template_produces_compilable_latex(self):
        """inject_into_template output should contain valid LaTeX structure."""
        from resume_tailor.tailor_resume import tailor_resume_to_json, inject_into_template

        data = tailor_resume_to_json(
            SAMPLE_RESUME_TEXT,
            job_title="SWE Intern",
            company="Acme",
            job_description="Python, APIs, distributed systems.",
        )
        latex = inject_into_template(data)

        assert r"\documentclass" in latex
        assert r"\begin{document}" in latex
        assert r"\end{document}" in latex
        assert "{{FONT_SIZE}}" in latex  # placeholder must survive injection
