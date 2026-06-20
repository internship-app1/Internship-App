"""
One-time backfill: stamp metadata['category'] on existing Job rows.

New crawls/scrapes set the category at insert time (crawlers/normalizer.py and
the GitHub scraper), but rows that predate the `departments` feature have no
category. This recomputes it from the stored department + title + source using
the same job_categories.categorize_job used everywhere else.

Run against staging FIRST, then prod:
    railway run -s internship-app python scripts/backfill_categories.py

Safe to re-run (idempotent). Pass --dry-run to only print the distribution.
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from job_categories import categorize_job  # noqa: E402
from job_database import get_db, close_db, Job  # noqa: E402

DRY_RUN = "--dry-run" in sys.argv


def main():
    db_url = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")
    print(f"DATABASE_URL host: {db_url.split('@')[-1][:50] if '@' in db_url else db_url}")
    print(f"mode: {'DRY RUN' if DRY_RUN else 'WRITE'}")

    db = get_db()
    try:
        jobs = db.query(Job).all()
        print(f"scanning {len(jobs)} rows...")
        dist, changed = Counter(), 0
        for job in jobs:
            try:
                meta = json.loads(job.job_metadata) if job.job_metadata else {}
            except (json.JSONDecodeError, TypeError):
                meta = {}
            department = (meta.get("department") or "")
            category = categorize_job(department, job.title or "", job.source or "")
            dist[category] += 1
            if meta.get("category") != category or job.category != category:
                changed += 1
                if not DRY_RUN:
                    meta["category"] = category
                    job.job_metadata = json.dumps(meta)
                    job.category = category
        if not DRY_RUN:
            db.commit()
        print(f"category distribution: {dict(dist)}")
        print(f"rows {'would change' if DRY_RUN else 'updated'}: {changed}")
    finally:
        close_db(db)


if __name__ == "__main__":
    main()
