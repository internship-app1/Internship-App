"""
Regression tests for crawlers.normalizer.

Covers the job_requirements fix: ATS jobs used to ship with an empty
job_requirements column (hardcoded ""), unlike github_internships jobs. The
normalizer now extracts a requirements/qualifications block from the JD —
from HTML headings (Greenhouse/Workday/iCIMS/Ashby), Lever's structured
`lists`, or SmartRecruiters' explicit `qualifications` section.
"""
from types import SimpleNamespace

from crawlers.normalizer import normalize_job, _extract_requirements


def _company(slug="acme", ats="greenhouse"):
    return SimpleNamespace(
        company_id=slug, display_name=slug.title(), ats_type=ats,
        ats_board_id=slug, careers_url="", industry="", company_size="",
    )


def test_greenhouse_requirements_extracted_from_html():
    raw = {
        "title": "Software Engineer Intern",
        "content": (
            "<p>We build things.</p>"
            "<h3>Minimum Qualifications</h3>"
            "<ul><li>Pursuing a BS in Computer Science</li>"
            "<li>Proficiency in Python and SQL</li></ul>"
            "<h3>Nice to have</h3><p>Internship experience</p>"
        ),
        "updated_at": "2026-06-01T00:00:00Z",
    }
    reqs = _extract_requirements(raw, "greenhouse")
    assert "Minimum Qualifications" in reqs
    assert "Python and SQL" in reqs
    # and it flows through normalize_job into the column
    job = normalize_job(raw, "greenhouse", _company())
    assert job["job_requirements"].strip()
    assert job["job_requirements"] == reqs


def test_greenhouse_handles_entity_escaped_html():
    # Greenhouse double-escapes its HTML (&lt;h3&gt;...); the extractor unescapes.
    raw = {
        "title": "Data Intern",
        "content": "&lt;h3&gt;Requirements&lt;/h3&gt;&lt;ul&gt;&lt;li&gt;Knows statistics&lt;/li&gt;&lt;/ul&gt;",
    }
    reqs = _extract_requirements(raw, "greenhouse")
    assert "Requirements" in reqs
    assert "statistics" in reqs


def test_lever_requirements_from_structured_lists():
    raw = {
        "text": "Business Development Intern",
        "lists": [
            {"text": "Missions", "content": "<li>Drive growth</li>"},
            {"text": "Profile", "content": "<li>Fluent in English</li><li>Detail-oriented</li>"},
        ],
        "description": "<p>Join us</p>",
    }
    reqs = _extract_requirements(raw, "lever")
    assert "Profile" in reqs
    assert "Fluent in English" in reqs
    # "Missions" (responsibilities) is not a requirements heading -> excluded
    assert "Drive growth" not in reqs


def test_smartrecruiters_uses_qualifications_section():
    raw = {
        "name": "ML Intern",
        "jobAd": {"sections": {
            "jobDescription": {"text": "<p>Cool team</p>"},
            "qualifications": {"text": "<ul><li>Knows PyTorch</li></ul>"},
        }},
    }
    reqs = _extract_requirements(raw, "smartrecruiters")
    assert "PyTorch" in reqs


def test_no_requirements_section_returns_empty_not_error():
    # A JD with no recognizable requirements block yields "" (not a crash) —
    # mirrors the github scraper's "not available" behavior.
    raw = {"title": "Workshop", "content": "<p>Come hang out with us for two days.</p>"}
    assert _extract_requirements(raw, "greenhouse") == ""
    job = normalize_job(raw, "greenhouse", _company())
    assert job["job_requirements"] == ""
    # the rest of the row is still well-formed
    assert job["title"] == "Workshop"
    assert job["source"] == "ats_greenhouse"
