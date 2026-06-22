#!/usr/bin/env python3
"""
Manual smoke test for the universal ATS crawler.

Runs three checks, no server required:
  1. Live fetch from each ATS (Greenhouse, Lever, Ashby, SmartRecruiters, Workday)
  2. Full normalize -> bulk_insert -> read-back, asserting ATS metadata persists
  3. Greenhouse apply_link token extraction (query-string strip + embed denylist)

Usage:
    python3 scripts/smoke_crawlers.py              # all checks
    python3 scripts/smoke_crawlers.py --live       # only the live ATS fetches
    python3 scripts/smoke_crawlers.py --db         # only the DB persistence check
    python3 scripts/smoke_crawlers.py --list       # print the slugs used and exit

Note: ATS slugs go stale constantly. If a count is 0, the slug probably died —
swap a fresh one into LIVE_TARGETS below (or check with:
  curl https://boards-api.greenhouse.io/v1/boards/<slug>/jobs?limit=1 ).
"""
import argparse
import asyncio
import json
import os
import sys

# Run from the repo root regardless of where the script is invoked from.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

# Known-live slugs as of the last update. ats_board_id, ats_type, min expected.
# For Greenhouse/Lever/Ashby the crawler returns ALL jobs (intern filter is applied
# later by the orchestrator); SmartRecruiters filters to internships in-crawler.
LIVE_TARGETS = [
    ("stripe", "greenhouse", 1),
    ("15five", "lever", 1),
    ("10xteam", "ashby", 1),
    ("Thales", "smartrecruiters", 1),
    ("apple", "workday", 0),  # 0 is acceptable — Apple is usually Cloudflare-protected
]


class _Company:
    """Stand-in for the CompanyRegistry row the crawlers expect."""

    def __init__(self, slug, ats):
        self.ats_board_id = slug
        self.display_name = slug
        self.ats_type = ats
        self.is_eu = False


def _green(s):
    return f"\033[32m{s}\033[0m"


def _red(s):
    return f"\033[31m{s}\033[0m"


async def check_live():
    """Fetch from each live ATS and report job counts."""
    from crawlers import greenhouse, lever, ashby, smartrecruiters, workday

    fetchers = {
        "greenhouse": greenhouse.fetch_jobs,
        "lever": lever.fetch_jobs,
        "ashby": ashby.fetch_jobs,
        "smartrecruiters": smartrecruiters.fetch_jobs,
        "workday": workday.fetch_jobs,
    }

    print("\n=== 1. Live ATS fetches ===")
    ok = True
    for slug, ats, minimum in LIVE_TARGETS:
        try:
            jobs = await fetchers[ats](_Company(slug, ats), since_hours=None)
            n = len(jobs)
            title = jobs[0].get("_title") if jobs else None
            passed = n >= minimum
            mark = _green("PASS") if passed else _red("FAIL")
            print(f"  [{mark}] {ats:16s} {slug:12s} -> {n:4d} jobs"
                  + (f"  (e.g. {title!r})" if title else ""))
            ok = ok and passed
        except Exception as exc:
            print(f"  [{_red('FAIL')}] {ats:16s} {slug:12s} -> {type(exc).__name__}: {exc}")
            ok = False
    return ok


def check_db_persistence():
    """Normalize a SmartRecruiters job, insert it, and confirm ATS metadata survives."""
    os.environ.setdefault("DATABASE_URL", "sqlite:///./_smoke_test.db")
    from job_database import bulk_insert_jobs, get_db, close_db, Job, Base, engine
    from crawlers.normalizer import normalize_job

    print("\n=== 2. normalize -> insert -> read-back (issue #1) ===")
    Base.metadata.create_all(bind=engine)

    company = _Company("Thales", "smartrecruiters")
    raw = {
        "id": "999",
        "name": "Data Science Intern",
        "experienceLevel": {"id": "internship", "label": "Internship"},
        "location": {"fullLocation": "Madrid"},
    }
    bulk_insert_jobs([normalize_job(raw, "smartrecruiters", company)])

    db = get_db()
    try:
        row = db.query(Job).filter(Job.title == "Data Science Intern").first()
        assert row is not None, "row was not inserted"
        meta = json.loads(row.job_metadata)
        required = ["ats_type", "ats_job_id", "department", "employment_type", "remote_type"]
        missing = [k for k in required if k not in meta]
        assert not missing, f"metadata missing keys: {missing}"
        assert meta["ats_type"] == "smartrecruiters" and meta["ats_job_id"] == "999"
        print(f"  [{_green('PASS')}] persisted ATS metadata: {sorted(meta.keys())}")
        return True
    except AssertionError as exc:
        print(f"  [{_red('FAIL')}] {exc}")
        return False
    finally:
        close_db(db)
        try:
            os.remove(os.path.join(REPO_ROOT, "_smoke_test.db"))
        except OSError:
            pass


def check_token_extraction():
    """Confirm apply_link token extraction strips query strings and denylists embed/js."""
    os.environ.setdefault("DATABASE_URL", "sqlite:///./_smoke_test.db")
    from job_database import get_db, close_db, Base, engine
    from sqlalchemy import text
    from crawlers.company_registry import CompanyRegistryStore

    print("\n=== 3. Greenhouse apply_link token extraction (issue #4) ===")
    Base.metadata.create_all(bind=engine)
    db = get_db()
    try:
        db.execute(text("DELETE FROM jobs"))
        for h, link in [
            ("h1", "https://boards.greenhouse.io/cleanco/jobs/123"),
            ("h2", "https://boards.greenhouse.io/queryco?gh_jid=456"),
            ("h3", "https://boards.greenhouse.io/embed/job_board/js?for=acme"),
        ]:
            db.execute(text(
                "INSERT INTO jobs (job_hash, company, title, location, apply_link, source, "
                "is_active, first_seen, last_seen, created_at, updated_at) VALUES "
                "(:h,'C','T','L',:l,'s',1,datetime('now'),datetime('now'),"
                "datetime('now'),datetime('now'))"
            ), {"h": h, "l": link})
        db.commit()
    finally:
        close_db(db)

    tokens = set(CompanyRegistryStore().get_unregistered_apply_link_tokens("greenhouse"))
    try:
        assert "cleanco" in tokens, "clean token missing"
        assert "queryco" in tokens, "query string not stripped"
        assert "embed" not in tokens, "embed leaked into tokens"
        assert not any("?" in t for t in tokens), "query string in token"
        print(f"  [{_green('PASS')}] tokens = {sorted(tokens)}")
        return True
    except AssertionError as exc:
        print(f"  [{_red('FAIL')}] {exc}  (got {sorted(tokens)})")
        return False
    finally:
        try:
            os.remove(os.path.join(REPO_ROOT, "_smoke_test.db"))
        except OSError:
            pass


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="only run live ATS fetches")
    parser.add_argument("--db", action="store_true", help="only run the DB persistence + token checks")
    parser.add_argument("--list", action="store_true", help="print the slugs used and exit")
    args = parser.parse_args()

    if args.list:
        print("Live targets (slug, ats, min_expected):")
        for t in LIVE_TARGETS:
            print(f"  {t}")
        return 0

    run_live = args.live or not args.db
    run_db = args.db or not args.live

    results = []
    if run_live:
        results.append(asyncio.run(check_live()))
    if run_db:
        results.append(check_db_persistence())
        results.append(check_token_extraction())

    ok = all(results)
    print("\n" + (_green("ALL CHECKS PASSED") if ok else _red("SOME CHECKS FAILED")))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
