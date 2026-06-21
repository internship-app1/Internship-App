"""
Regression tests for title-based skill inference in the GitHub/SimplifyJobs
scraper (job_scrapers.scrape_github_internships.infer_skills_from_title_aggressive).

The tech_map lookup used a raw substring test (`keyword in title_lower`), which
mis-tagged titles: "go" fired on "Google"/"Category", and "java" fired inside
"JavaScript" (so JavaScript-only roles were tagged with Java). Matching is now
token-bounded.
"""
from job_scrapers.scrape_github_internships import infer_skills_from_title_aggressive as infer
from job_categories import CATEGORY_IDS


def test_go_not_inferred_from_substring_words():
    # "Go" must not be inferred from "Google" or "Category".
    assert "Go" not in infer("Software Engineer, Google Ads")
    assert "Go" not in infer("Category Manager Intern")


def test_java_not_inferred_from_javascript():
    # Use a title that hits the "frontend" role branch so the generic
    # else-branch baseline (which legitimately adds Java) does not fire — this
    # isolates the tech_map lookup. Pre-fix, "java" matched inside "javascript"
    # and Java was tagged on top of JavaScript.
    skills = infer("Frontend JavaScript Engineer Intern")
    assert "JavaScript" in skills
    assert "Java" not in skills


def test_genuine_language_tokens_still_inferred():
    assert "Go" in infer("Go Backend Intern")
    assert "Java" in infer("Java Backend Intern")
    assert ".NET" in infer("ASP.NET Developer Intern")
    assert "C++" in infer("C++ Systems Intern")
    assert "C#" in infer("C# Engineer Intern")
    assert "Node.js" in infer("Node.js Developer Intern")


def test_github_scraper_jobs_have_metadata_category(monkeypatch):
    """Regression: GitHub scraper used to omit metadata entirely → category NULL in DB."""
    # Stub network calls — we only care about the job dict shape, not real data.
    import job_scrapers.scrape_github_internships as mod

    fake_html = """<table>
<tr><th>Company</th><th>Role</th><th>Location</th><th>Application/Link</th><th>Date Posted</th></tr>
<tr><td>Acme Corp</td><td>Software Engineer Intern</td><td>Remote</td>
<td><a href="https://example.com/apply">Apply</a></td><td>2 days ago</td></tr>
</table>"""

    monkeypatch.setattr(mod.requests, "get", lambda *a, **kw: type("R", (), {
        "status_code": 200, "text": fake_html, "raise_for_status": lambda self: None,
    })())

    jobs = mod.scrape_github_internships()
    assert jobs, "Expected at least one job from the fake HTML"
    for job in jobs:
        assert "metadata" in job, f"Job missing metadata key: {job.get('title')}"
        assert "category" in job["metadata"], f"Job metadata missing category: {job.get('title')}"
        assert job["metadata"]["category"] in CATEGORY_IDS, (
            f"Job category {job['metadata']['category']!r} not a valid CATEGORY_ID"
        )
