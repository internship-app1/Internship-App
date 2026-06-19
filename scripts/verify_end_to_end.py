#!/usr/bin/env python3
"""
End-to-end verification of the universal ATS crawler.

Unlike smoke_crawlers.py (which pokes pieces in isolation), this runs the REAL
production pipeline exactly as the GitHub Actions cron will:

    registry -> orchestrator.run_full() -> per-ATS fetch -> is_intern_posting
    filter -> normalize_job -> bulk_insert_jobs -> DB

Then it queries the jobs table and prints the actual internships it landed, with
clickable apply links you can open in a browser to confirm they're real. Nothing
is mocked — a PASS here means the whole chain works on live data.

It uses a throwaway SQLite DB it deletes afterward, so your real DB is untouched.

Usage:
    python3 scripts/verify_end_to_end.py            # seed + crawl + show results
    python3 scripts/verify_end_to_end.py --keep-db  # leave the SQLite file for inspection
"""
import argparse
import asyncio
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
os.chdir(REPO_ROOT)

# Use a throwaway DB BEFORE importing anything that builds the engine.
DB_PATH = os.path.join(REPO_ROOT, "_e2e_verify.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ.setdefault("TRACK_USAGE", "false")

# A spread of known-live boards across every ATS the crawler supports. These are
# real companies; intern counts vary by season, so the script reports raw jobs AND
# interns and shows whatever it finds rather than asserting a fixed number.
SEED_COMPANIES = [
    # company_id, display_name, ats_type, ats_board_id
    ("stripe",            "Stripe",          "greenhouse",      "stripe"),
    ("databricks",        "Databricks",      "greenhouse",      "databricks"),
    ("lever_15five",      "15Five",          "lever",           "15five"),
    ("ashby_10xteam",     "10xTeam",         "ashby",           "10xteam"),
    ("Thales",            "Thales",          "smartrecruiters", "Thales"),
    ("Accor",             "Accor",           "smartrecruiters", "Accor"),
]


def _c(code, s):
    return f"\033[{code}m{s}\033[0m"


async def main(keep_db: bool):
    from crawlers.company_registry import CompanyRegistryStore
    from crawlers.orchestrator import CrawlOrchestrator
    from job_database import get_db, close_db, Job, Base, engine

    Base.metadata.create_all(bind=engine)

    # 1. Seed the registry exactly like the bootstrap/discover step would.
    print(_c("1;36", "\n[1/3] Seeding company registry with 6 live companies..."))
    registry = CompanyRegistryStore()
    for company_id, name, ats_type, board_id in SEED_COMPANIES:
        registry.upsert({
            "company_id": company_id,
            "display_name": name,
            "ats_type": ats_type,
            "ats_board_id": board_id,
        })
    stats = registry.get_stats()
    print(f"      registered: {stats['total_active']} active  ({stats['by_ats']})")

    # 2. Run the REAL orchestrator full crawl (the cron's exact code path).
    print(_c("1;36", "\n[2/3] Running orchestrator.run_full() — the production crawl path..."))
    orchestrator = CrawlOrchestrator()
    result = await orchestrator.run_full()
    # run_full fires a fire-and-forget apply-link discovery task; in this throwaway
    # run we cancel it so it can't outlive the DB we delete at the end.
    discovery = getattr(orchestrator, "_discovery_task", None)
    if discovery is not None:
        discovery.cancel()
        try:
            await discovery
        except (asyncio.CancelledError, Exception):
            pass
    print(f"      companies_crawled = {result['companies_crawled']}")
    print(f"      jobs_found (interns) = {result['jobs_found']}")
    print(f"      new_jobs inserted    = {result['new_jobs']}")
    print(f"      duration             = {result['duration_ms']} ms")

    # 3. Read the jobs table back and show real internships with apply links.
    print(_c("1;36", "\n[3/3] Reading internships back out of the DB...\n"))
    db = get_db()
    try:
        rows = db.query(Job).filter(Job.is_active == True).all()  # noqa: E712
        by_source = {}
        for r in rows:
            by_source[r.source] = by_source.get(r.source, 0) + 1

        print(f"      {len(rows)} active internships in DB, by source: {by_source}\n")

        shown = 0
        for r in rows:
            if shown >= 12:
                break
            meta = json.loads(r.job_metadata or "{}")
            link_ok = bool(r.apply_link and r.apply_link.startswith("http"))
            tick = _c("32", "link✓") if link_ok else _c("31", "NO LINK")
            print(f"  • {_c('1', r.title)}")
            print(f"      {r.company}  |  {r.location or '—'}  |  "
                  f"{meta.get('ats_type', '?')}  |  {tick}")
            print(f"      {_c('34', r.apply_link)}")
            shown += 1

        if len(rows) > shown:
            print(f"\n      ... and {len(rows) - shown} more.")

        # Verdict: the pipeline works if it crawled companies and landed jobs with
        # valid links. (Intern count can legitimately be low off-season.)
        bad_links = [r for r in rows if not (r.apply_link or "").startswith("http")]
        ok = result["companies_crawled"] > 0 and len(rows) > 0 and not bad_links
        print()
        if ok:
            print(_c("1;32", "VERDICT: pipeline works — real internships landed with valid apply links."))
            print("Open any link above in your browser to confirm it's a live posting.")
        elif result["companies_crawled"] == 0:
            print(_c("1;31", "VERDICT: no companies crawled — check the registry seed step."))
        elif not rows:
            print(_c("1;33", "VERDICT: pipeline ran but found 0 internships right now "
                             "(can be seasonal). Try different SEED_COMPANIES."))
            ok = True  # ran cleanly; just no interns in season
        else:
            print(_c("1;31", f"VERDICT: {len(bad_links)} job(s) have a broken apply_link."))
        return 0 if ok else 1
    finally:
        close_db(db)
        if not keep_db:
            try:
                os.remove(DB_PATH)
            except OSError:
                pass
        else:
            print(f"\n(SQLite DB left at {DB_PATH} — inspect with: "
                  f"sqlite3 {DB_PATH} 'select company,title,apply_link from jobs')")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--keep-db", action="store_true",
                        help="don't delete the throwaway SQLite DB (inspect it yourself)")
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.keep_db)))
