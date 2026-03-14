"""
Tests for job_database.py

Uses SQLite :memory: (set in conftest.py) so no real database is needed.
Tables are created fresh for each test class via a module-level setup.
"""
import os
import pytest
from datetime import datetime, timedelta

# DATABASE_URL is overridden to sqlite:///:memory: by conftest.py
# Import after env is set
from job_database import (
    Base,
    Job,
    ResumeCache,
    SessionLocal,
    bulk_insert_jobs,
    engine,
    get_active_jobs,
    get_database_stats,
    get_resume_cache,
    mark_old_jobs_inactive,
    set_resume_cache,
)


@pytest.fixture(autouse=True)
def fresh_db():
    """Drop and recreate all tables before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _job(company="Acme", title="SWE Intern", location="Remote", n=0) -> dict:
    return {
        "company": company,
        "title": f"{title} {n}",
        "location": location,
        "apply_link": f"https://example.com/job/{n}",
        "description": "Great role",
        "required_skills": ["Python", "React"],
        "job_requirements": "2 years exp",
        "source": "github_internships",
        "days_since_posted": 1,
        "date_posted": "2025-03-01",
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# bulk_insert_jobs
# ---------------------------------------------------------------------------

class TestBulkInsertJobs:
    def test_inserts_new_jobs(self):
        jobs = [_job(n=i) for i in range(3)]
        stats = bulk_insert_jobs(jobs)
        assert stats["new_jobs"] == 3

    def test_deduplicates_same_job(self):
        job = _job(n=1)
        stats1 = bulk_insert_jobs([job])
        stats2 = bulk_insert_jobs([job])
        assert stats1["new_jobs"] == 1
        # Second insert is an update, not a new job
        assert stats2["new_jobs"] == 0

    def test_handles_empty_list(self):
        stats = bulk_insert_jobs([])
        assert stats["new_jobs"] == 0

    def test_stores_required_fields(self):
        bulk_insert_jobs([_job(company="Google", n=99)])
        db = SessionLocal()
        try:
            job = db.query(Job).filter_by(company="Google").first()
            assert job is not None
            assert "SWE Intern" in job.title
        finally:
            db.close()


# ---------------------------------------------------------------------------
# get_active_jobs
# ---------------------------------------------------------------------------

class TestGetActiveJobs:
    def test_returns_all_active(self):
        bulk_insert_jobs([_job(n=i) for i in range(5)])
        jobs = get_active_jobs()
        assert len(jobs) == 5

    def test_respects_limit(self):
        bulk_insert_jobs([_job(n=i) for i in range(10)])
        jobs = get_active_jobs(limit=3)
        assert len(jobs) == 3

    def test_excludes_inactive(self):
        bulk_insert_jobs([_job(n=i) for i in range(3)])
        # Manually deactivate one (fetch first to avoid SQLAlchemy evaluate error)
        db = SessionLocal()
        try:
            job = db.query(Job).first()
            job.is_active = False
            db.commit()
        finally:
            db.close()

        jobs = get_active_jobs()
        assert len(jobs) == 2


# ---------------------------------------------------------------------------
# mark_old_jobs_inactive
# ---------------------------------------------------------------------------

class TestMarkOldJobsInactive:
    def test_marks_stale_jobs_inactive(self):
        # Insert fresh jobs (days_since_posted=1 so bulk_insert won't deactivate them)
        bulk_insert_jobs([_job(n=i) for i in range(3)])

        # Manually backdate the metadata so jobs look 40 days old
        db = SessionLocal()
        try:
            import json as _json
            for job in db.query(Job).all():
                meta = _json.loads(job.job_metadata or "{}")
                meta["days_since_posted"] = 40
                job.job_metadata = _json.dumps(meta)
            db.commit()
        finally:
            db.close()

        count = mark_old_jobs_inactive(max_days_old=30)
        assert count == 3

    def test_leaves_fresh_jobs_active(self):
        bulk_insert_jobs([_job(n=i) for i in range(2)])
        count = mark_old_jobs_inactive(max_days_old=30)
        assert count == 0


# ---------------------------------------------------------------------------
# get_database_stats
# ---------------------------------------------------------------------------

class TestGetDatabaseStats:
    def test_returns_expected_keys(self):
        bulk_insert_jobs([_job(n=0)])
        stats = get_database_stats()
        assert "total_jobs" in stats
        assert "active_jobs" in stats

    def test_counts_active_jobs(self):
        bulk_insert_jobs([_job(n=i) for i in range(4)])
        stats = get_database_stats()
        assert stats["active_jobs"] == 4


# ---------------------------------------------------------------------------
# ResumeCache (get / set)
# ---------------------------------------------------------------------------

class TestResumeCache:
    def test_set_and_get(self):
        set_resume_cache("user1", "hash123", {"jobs": []}, ["Python"])
        result = get_resume_cache("user1", "hash123")
        assert result is not None
        assert result["skills"] == ["Python"]

    def test_miss_returns_none(self):
        result = get_resume_cache("user1", "nonexistent")
        assert result is None

    def test_different_users_isolated(self):
        set_resume_cache("user1", "h1", {"jobs": [1]}, ["Go"])
        set_resume_cache("user2", "h1", {"jobs": [2]}, ["Rust"])
        r1 = get_resume_cache("user1", "h1")
        r2 = get_resume_cache("user2", "h1")
        assert r1["skills"] == ["Go"]
        assert r2["skills"] == ["Rust"]
