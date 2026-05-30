"""
SimplifyJobs → Supabase sync pipeline.
Runs hourly via GitHub Actions. No dependency on the main app's modules.

Three phases:
  1. Fetch + parse SimplifyJobs README
  2. Upsert to Supabase (preserving first_seen on existing rows)
  3. Inactive sweep (jobs absent > 3 days → is_active = False)
"""

import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from supabase import create_client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not required in CI — env vars are injected directly

README_URL = "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/README.md"
HASH_CHUNK = 500   # max hashes per Supabase IN query
INSERT_CHUNK = 200 # max rows per insert batch


# ---------------------------------------------------------------------------
# Phase 1: Extract & Transform
# ---------------------------------------------------------------------------

def fetch_readme() -> str:
    resp = requests.get(README_URL, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_date_to_days(date_string) -> int | None:
    """Convert various date formats to days-since-posted integer.
    Copied from job_scrapers/scrape_github_internships.py:parse_date_to_days."""
    if not date_string or date_string == "Unknown":
        return None

    date_string = date_string.strip().lower()

    try:
        if "today" in date_string or "just now" in date_string:
            return 0
        elif "yesterday" in date_string:
            return 1
        elif "day" in date_string or (date_string and date_string[-1] == "d"):
            match = re.search(r'(\d+)\s*d', date_string)
            if match:
                return int(match.group(1))
        elif "week" in date_string or (date_string and date_string[-1] == "w"):
            match = re.search(r'(\d+)\s*w', date_string)
            if match:
                return int(match.group(1)) * 7
        elif "month" in date_string or "mo" in date_string:
            match = re.search(r'(\d+)\s*mo', date_string)
            if match:
                return int(match.group(1)) * 30
        elif "year" in date_string or (date_string and date_string[-1] == "y"):
            match = re.search(r'(\d+)\s*y', date_string)
            if match:
                return int(match.group(1)) * 365

        current_year = datetime.now().year

        for fmt in ('%Y-%m-%d', '%b %d, %Y'):
            try:
                posted = datetime.strptime(date_string, fmt)
                return max(0, (datetime.now() - posted).days)
            except ValueError:
                pass

        try:
            posted = datetime.strptime(f"{date_string} {current_year}", '%b %d %Y')
            days = (datetime.now() - posted).days
            if days < 0:
                posted = datetime.strptime(f"{date_string} {current_year - 1}", '%b %d %Y')
                days = (datetime.now() - posted).days
            return max(0, days)
        except ValueError:
            pass

        for fmt in ('%m/%d/%Y', '%d/%m/%Y'):
            try:
                posted = datetime.strptime(date_string, fmt)
                return max(0, (datetime.now() - posted).days)
            except ValueError:
                pass

        return None

    except Exception:
        return None


def make_job_hash(company: str, title: str, location: str, apply_link: str) -> str:
    """SHA-256 hash matching job_database.py:generate_job_hash exactly."""
    try:
        parsed = urlparse(apply_link)
        domain_path = (parsed.netloc + parsed.path).rstrip("/")
    except Exception:
        domain_path = apply_link[:100]

    hash_string = (
        f"{company.lower().strip()}|"
        f"{title.lower().strip()}|"
        f"{location.lower().strip()}|"
        f"{domain_path.lower()}"
    )
    return hashlib.sha256(hash_string.encode("utf-8")).hexdigest()


def parse_table(markdown: str) -> list[dict]:
    """Parse the SimplifyJobs markdown table into job dicts."""
    soup = BeautifulSoup(markdown, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        print("ERROR: No tables found in README", file=sys.stderr)
        return []

    table = tables[0]
    rows = table.find_all("tr")
    if len(rows) < 2:
        return []

    # Detect date column index from header
    header_cells = rows[0].find_all(["th", "td"])
    date_col = None
    for i, cell in enumerate(header_cells):
        text = cell.get_text(strip=True).lower()
        if any(k in text for k in ("date posted", "posted", "date added", "added", "date", "age")):
            date_col = i
            break

    jobs = []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        # Company (cell 0)
        company_cell = cells[0]
        anchor = company_cell.find("a")
        company = anchor.get_text(strip=True) if anchor else company_cell.get_text(strip=True)

        # Role (cell 1)
        title = cells[1].get_text(strip=True)

        # Location (cell 2)
        location = cells[2].get_text(separator=", ", strip=True)

        # Apply link (cell 3) — prefer non-Simplify link
        link_cell = cells[3]
        apply_link = ""
        for a in link_cell.find_all("a", href=True):
            href = a["href"]
            if "simplify.jobs" not in href:
                apply_link = href
                break
        if not apply_link:
            a = link_cell.find("a", href=True)
            apply_link = a["href"] if a else ""

        # Date (optional)
        date_raw = None
        if date_col is not None and date_col < len(cells):
            date_raw = cells[date_col].get_text(strip=True)

        if not company or not title or not apply_link:
            continue

        jobs.append({
            "company": company,
            "title": title,
            "location": location,
            "apply_link": apply_link,
            "date_posted_raw": date_raw,
            "days_since_posted": parse_date_to_days(date_raw),
        })

    return jobs


def build_records(jobs: list[dict], now_iso: str) -> list[dict]:
    records = []
    for job in jobs:
        records.append({
            "job_hash": make_job_hash(
                job["company"], job["title"], job["location"], job["apply_link"]
            ),
            "company": job["company"],
            "title": job["title"],
            "location": job["location"],
            "apply_link": job["apply_link"],
            "description": "",
            "required_skills": "[]",
            "job_requirements": "",
            "source": "github_internships",
            "job_metadata": json.dumps({"days_since_posted": job["days_since_posted"]}),
            "first_seen": now_iso,
            "last_seen": now_iso,
            "created_at": now_iso,
            "updated_at": now_iso,
            "is_active": True,
        })
    return records


# ---------------------------------------------------------------------------
# Phase 2: Upsert
# ---------------------------------------------------------------------------

def _chunks(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def fetch_existing_hashes(supabase, all_hashes: list[str]) -> set[str]:
    existing = set()
    for chunk in _chunks(all_hashes, HASH_CHUNK):
        resp = supabase.table("jobs").select("job_hash").in_("job_hash", chunk).execute()
        for row in resp.data:
            existing.add(row["job_hash"])
    return existing


def insert_new_jobs(supabase, new_records: list[dict]) -> int:
    for chunk in _chunks(new_records, INSERT_CHUNK):
        supabase.table("jobs").insert(chunk).execute()
    return len(new_records)


def update_existing_jobs(supabase, existing_records: list[dict], now_iso: str) -> int:
    # Group by days_since_posted so we can batch update per distinct metadata value.
    # This keeps the number of API calls low (one per distinct days value).
    by_days: dict[int | None, list[str]] = defaultdict(list)
    for rec in existing_records:
        meta = json.loads(rec["job_metadata"])
        by_days[meta.get("days_since_posted")].append(rec["job_hash"])

    for days_val, hashes in by_days.items():
        update_payload = {
            "last_seen": now_iso,
            "updated_at": now_iso,
            "is_active": True,
            "job_metadata": json.dumps({"days_since_posted": days_val}),
        }
        for chunk in _chunks(hashes, HASH_CHUNK):
            supabase.table("jobs").update(update_payload).in_("job_hash", chunk).execute()

    return len(existing_records)


# ---------------------------------------------------------------------------
# Phase 3: Inactive sweep
# ---------------------------------------------------------------------------

def inactive_sweep(supabase) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    resp = (
        supabase.table("jobs")
        .update({"is_active": False})
        .lt("last_seen", cutoff)
        .eq("is_active", True)
        .execute()
    )
    return len(resp.data) if resp.data else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    supabase_url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not service_key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set", file=sys.stderr)
        sys.exit(1)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Phase 1
    print("Fetching SimplifyJobs README...")
    markdown = fetch_readme()
    jobs = parse_table(markdown)
    print(f"Parsed {len(jobs)} jobs from README")
    if not jobs:
        print("No jobs parsed — aborting", file=sys.stderr)
        sys.exit(1)

    records = build_records(jobs, now_iso)
    all_hashes = [r["job_hash"] for r in records]

    # Phase 2
    print("Connecting to Supabase...")
    supabase = create_client(supabase_url, service_key)

    print("Checking existing hashes...")
    existing_hashes = fetch_existing_hashes(supabase, all_hashes)

    new_records = [r for r in records if r["job_hash"] not in existing_hashes]
    existing_records = [r for r in records if r["job_hash"] in existing_hashes]

    print(f"Inserting {len(new_records)} new jobs...")
    inserted = insert_new_jobs(supabase, new_records)

    print(f"Updating {len(existing_records)} existing jobs...")
    updated = update_existing_jobs(supabase, existing_records, now_iso)

    # Phase 3
    print("Running inactive sweep...")
    swept = inactive_sweep(supabase)

    print(f"Done: {inserted} new | {updated} updated | {swept} marked inactive")


if __name__ == "__main__":
    main()
