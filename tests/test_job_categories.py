"""
Tests for job_categories.categorize_job and matcher._passes_category_filter —
the department/category filter that powers the upload-page selector.

Fast tests monkeypatch _classify_with_embeddings to None so no model loads.
Slow tests (marked pytest.mark.slow) exercise the real embedding model.
"""
import pytest
import job_categories

from job_categories import categorize_job, CATEGORY_IDS
from matching.matcher import _passes_category_filter, _filter_by_categories

# Capture the real embedding function before any monkeypatching so the slow
# tests can restore it even after the autouse fixture disables it.
_real_classify_with_embeddings = job_categories._classify_with_embeddings


@pytest.fixture(autouse=True)
def _disable_embeddings(monkeypatch):
    """Disable embedding calls in unit tests — keyword path only, no model load."""
    monkeypatch.setattr(job_categories, "_classify_with_embeddings", lambda text: None)


@pytest.mark.parametrize("department,title,source,expected", [
    # title drives the bucket (new title-first behaviour)
    ("Engineering", "Software Engineer Intern", "ats_greenhouse", "software"),
    ("Sales", "Sales Development Intern", "ats_lever", "business"),
    ("Marketing", "Product Marketing Intern", "ats_greenhouse", "business"),
    ("Data Science", "Data Scientist Intern", "ats_ashby", "data_ml"),
    ("Hardware", "Firmware Intern", "ats_greenhouse", "hardware"),
    ("Security", "Security Engineer Intern", "ats_greenhouse", "security"),
    ("Design", "Product Design Intern", "ats_lever", "design"),
    ("Product", "Associate Product Manager Intern", "ats_greenhouse", "product"),
    # no department -> fall back to title
    ("", "Machine Learning Intern", "ats_greenhouse", "data_ml"),
    ("", "Finance Intern", "ats_greenhouse", "business"),
    # curated GitHub source: unclassified title defaults to software
    ("", "Some Quirky Intern Title", "github_internships", "software"),
    ("", "Finance Intern", "github_internships", "business"),  # explicit wins over default
    # truly unknown ATS role -> other
    ("", "Llama groomer", "ats_workday", "other"),
    # Bug regression: clinical title should win over admin department (was tagged "business")
    ("Administration", "Master's Level Clinical Intern", "ats_greenhouse", "healthcare"),
    # Bug regression: dept-only keyword should still work when title is generic
    ("Data Science", "Summer Intern", "ats_greenhouse", "data_ml"),
])
def test_categorize_job(department, title, source, expected):
    assert categorize_job(department, title, source) == expected


def test_categorize_job_always_returns_valid_id():
    for src in ("ats_greenhouse", "github_internships", "ats_workday"):
        assert categorize_job("", "", src) in CATEGORY_IDS


def _job(category):
    return {"title": "X", "metadata": {"category": category}}


def test_passes_category_filter_empty_selection_passes_all():
    assert _passes_category_filter(_job("business"), set()) is True
    assert _passes_category_filter(_job("software"), None) is True


def test_passes_category_filter_membership():
    sel = {"software", "data_ml"}
    assert _passes_category_filter(_job("software"), sel) is True
    assert _passes_category_filter(_job("data_ml"), sel) is True
    assert _passes_category_filter(_job("business"), sel) is False


def test_passes_category_filter_missing_metadata_passes_through():
    # Jobs with no category stamp (pre-backfill rows) pass through any filter
    # so they remain visible until the next scrape re-stamps them.
    assert _passes_category_filter({"title": "X"}, {"software"}) is True
    assert _passes_category_filter({"title": "X", "metadata": {}}, {"software"}) is True
    assert _passes_category_filter({"title": "X", "metadata": {}}, {"other"}) is True


def test_filter_by_categories_noop_when_empty():
    jobs = [_job("software"), _job("business")]
    assert _filter_by_categories(jobs, []) == jobs
    assert _filter_by_categories(jobs, None) == jobs


def test_filter_by_categories_filters_and_reports_empty():
    jobs = [_job("software"), _job("business"), _job("data_ml")]
    assert _filter_by_categories(jobs, ["software", "data_ml"]) == [jobs[0], jobs[2]]
    msgs = []
    out = _filter_by_categories(jobs, ["security"], progress_callback=msgs.append)
    assert out == []
    assert msgs and "department" in msgs[0].lower()


# ── Embedding regression tests (slow — load real model) ───────────────────────
# These exercise the specific staging failures. Marked slow so CI can skip:
#   pytest -m "not slow"   → fast suite only
#   pytest -m slow         → embedding tests only


@pytest.mark.slow
class TestEmbeddingClassifier:
    """Real-model tests — no monkeypatch, _classify_with_embeddings runs for real."""

    @pytest.fixture(autouse=True)
    def _reenable_embeddings(self, monkeypatch):
        # Restore the real embedding function (captured before any patching above).
        monkeypatch.setattr(job_categories, "_classify_with_embeddings",
                            _real_classify_with_embeddings)

    def test_oncology_dept_pm_title_not_healthcare(self):
        # "oncology" in dept used to override the PM title → healthcare. Title wins now.
        result = categorize_job("Product Management, Oncology", "Product Management Intern", "ats_greenhouse")
        assert result != "healthcare", (
            f"PM role at oncology dept should not be healthcare, got {result!r}"
        )

    def test_editorial_therapy_title_not_healthcare(self):
        # "therapy" keyword in title used to fire on an editorial/media internship.
        # Embedding should recognise the editorial context and reject healthcare.
        result = categorize_job("Editorial Special Projects", "Dorm Therapy Editorial Intern", "ats_greenhouse")
        assert result != "healthcare", (
            f"Editorial role should not be healthcare even with 'therapy' in title, got {result!r}"
        )

    def test_health_economics_is_healthcare(self):
        # "health" alone was not a keyword — Health Economics fell to other.
        # Embedding should bridge the vocabulary gap.
        result = categorize_job("HEOR", "Health Economics and Outcomes Research Intern", "ats_greenhouse")
        assert result == "healthcare", (
            f"Health Economics research should be healthcare, got {result!r}"
        )

    def test_clinical_ai_not_business_or_other(self):
        # data_ml fired before healthcare via " ai " keyword. Both healthcare and
        # data_ml are acceptable (it's genuinely at the intersection); only
        # business/other/software are clearly wrong.
        result = categorize_job("Frontier", "Clinical AI Intern", "ats_ashby")
        assert result in {"healthcare", "data_ml"}, (
            f"Clinical AI role should be healthcare or data_ml, got {result!r}"
        )

    def test_business_analytics_mars_not_healthcare(self):
        # The exact job that appeared in a Healthcare-only search due to NULL category.
        # After the scraper fix it will get a category; verify it's not healthcare.
        result = categorize_job("", "Business Analytics Analyst Co-op", "github_internships")
        assert result != "healthcare", (
            f"Business Analytics role should not be healthcare, got {result!r}"
        )
