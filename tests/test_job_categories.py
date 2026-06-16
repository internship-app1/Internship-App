"""
Tests for job_categories.categorize_job and matcher._passes_category_filter —
the department/category filter that powers the upload-page selector.
"""
import pytest

from job_categories import categorize_job, CATEGORY_IDS
from matching.matcher import _passes_category_filter, _filter_by_categories


@pytest.mark.parametrize("department,title,source,expected", [
    # department drives the bucket when present
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


def test_passes_category_filter_missing_metadata_is_other():
    # not-yet-backfilled rows have no category -> treated as 'other'
    assert _passes_category_filter({"title": "X"}, {"other"}) is True
    assert _passes_category_filter({"title": "X", "metadata": {}}, {"software"}) is False


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
