"""
Regression test: the resume-results cache key must include the selected
department categories, so changing the department filter is a cache MISS
(a fresh search) instead of serving the previous selection's cached results.
"""
from app import _resume_cache_key


def test_categories_change_the_key():
    base = _resume_cache_key("h", True, [])
    sw = _resume_cache_key("h", True, ["software"])
    swdata = _resume_cache_key("h", True, ["software", "data_ml"])
    biz = _resume_cache_key("h", True, ["business"])
    # every distinct selection -> distinct key (forces a new search)
    assert len({base, sw, swdata, biz}) == 4


def test_selection_order_does_not_matter():
    assert _resume_cache_key("h", True, ["software", "data_ml"]) == \
           _resume_cache_key("h", True, ["data_ml", "software"])


def test_no_filter_is_all():
    assert _resume_cache_key("h", True, []).endswith("_all_v2")
    assert _resume_cache_key("h", True, None).endswith("_all_v2")


def test_think_deeper_still_distinguishes():
    assert _resume_cache_key("h", True, ["software"]) != \
           _resume_cache_key("h", False, ["software"])
