"""
Regression tests for title-based skill inference in the GitHub/SimplifyJobs
scraper (job_scrapers.scrape_github_internships.infer_skills_from_title_aggressive).

The tech_map lookup used a raw substring test (`keyword in title_lower`), which
mis-tagged titles: "go" fired on "Google"/"Category", and "java" fired inside
"JavaScript" (so JavaScript-only roles were tagged with Java). Matching is now
token-bounded.
"""
from job_scrapers.scrape_github_internships import infer_skills_from_title_aggressive as infer


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
