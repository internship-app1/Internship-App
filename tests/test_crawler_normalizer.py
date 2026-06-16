"""
Regression tests for crawlers.normalizer.

Covers the job_requirements fix: ATS jobs used to ship with an empty
job_requirements column (hardcoded ""), unlike github_internships jobs. The
normalizer now extracts a requirements/qualifications block from the JD —
from HTML headings (Greenhouse/Workday/iCIMS/Ashby), Lever's structured
`lists`, or SmartRecruiters' explicit `qualifications` section.
"""
from types import SimpleNamespace

from crawlers.normalizer import (
    normalize_job,
    _extract_requirements,
    _extract_remote_type,
    _extract_skills_from_text,
)


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


def test_ashby_null_workplace_type_does_not_crash():
    # Regression: Ashby sends workplaceType: null, so raw.get("workplaceType","")
    # returned None and the eager dict.get default `wt.lower()` crashed the whole
    # normalize for every Ashby posting ('NoneType' object has no attribute 'lower').
    assert _extract_remote_type({"workplaceType": None}, "ashby") == ""
    assert _extract_remote_type({"workplaceType": None}, "lever") == ""
    # known values still map correctly
    assert _extract_remote_type({"workplaceType": "Remote"}, "ashby") == "remote"
    # and a full Ashby job normalizes without raising
    raw = {"title": "ML Intern", "workplaceType": None,
           "descriptionHtml": "<h3>Requirements</h3><ul><li>Knows Python</li></ul>"}
    job = normalize_job(raw, "ashby", _company(ats="ashby"))
    assert job["source"] == "ats_ashby"
    assert "Python" in job["job_requirements"]


def test_normalize_job_stamps_category():
    # normalize_job now emits metadata['category'] for the upload-page filter.
    raw = {"title": "Software Engineer Intern", "content": "<p>build stuff</p>",
           "departments": [{"name": "Engineering"}]}
    job = normalize_job(raw, "greenhouse", _company())
    assert job["metadata"]["category"] == "software"

    biz = normalize_job({"title": "Finance Intern", "content": "",
                         "departments": [{"name": "Finance"}]}, "greenhouse", _company())
    assert biz["metadata"]["category"] == "business"


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


def test_skill_extraction_does_not_substring_match_single_letters():
    # Regression: the single-letter skill "r" used to match every description
    # containing the letter r (a raw `"r" in text` test), so non-technical
    # jobs were tagged with "r". Skills must match as whole tokens.
    text = (
        "Support manufacturing operations and improve production throughput. "
        "Strong communication and a great work ethic are required."
    )
    assert _extract_skills_from_text(text) == []


def test_skill_extraction_matches_genuine_token_mentions():
    # Real mentions still match, including short ones, regardless of
    # surrounding punctuation.
    assert "python" in _extract_skills_from_text("Proficiency in R or Python.")
    assert set(_extract_skills_from_text("Experience with SQL and Go.")) == {
        "sql", "go",
    }


def test_bare_r_is_never_extracted():
    # Bare "r" is intentionally not in COMMON_SKILLS: even token-bounded it
    # matches "R&D"/"R&B"/bullet "R." far more than the R language, so it is
    # dropped entirely (aligned with matcher.KNOWN_SKILLS_VOCAB). It must never
    # appear, even for genuine R-language mentions or "R&D".
    assert "r" not in _extract_skills_from_text("Proficiency in R or Python.")
    assert "r" not in _extract_skills_from_text("5+ years of empirical R&D.")
    assert "r" not in _extract_skills_from_text("Skills: Python, R, and SQL.")


def test_skill_extraction_ignores_substrings_inside_other_words():
    # "go" must not fire on "good"/"category"; "php" must not fire on "graph";
    # "c"/"node" must not bleed from "c++"/"node.js".
    assert _extract_skills_from_text("A good candidate for this category.") == []
    assert _extract_skills_from_text("Knowledge of graphing tools.") == []
    assert _extract_skills_from_text("Build UIs with React.") == ["react"]
    assert _extract_skills_from_text("Systems work in C++ and Node.js.") == [
        "node.js", "c++",
    ]
