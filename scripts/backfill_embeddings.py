"""
One-time backfill: generate sentence embeddings for all active jobs that don't have one.

Usage:
    python scripts/backfill_embeddings.py           # live run
    python scripts/backfill_embeddings.py --dry-run # just print counts, no DB writes
"""
import sys
import os
import argparse

# Allow running from repo root or from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from job_database import init_database, get_jobs_without_embeddings, save_job_embeddings, get_db, close_db
from matching.embedder import embed_batch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print counts only, no DB writes")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    args = parser.parse_args()

    init_database()

    db = get_db()
    try:
        jobs = get_jobs_without_embeddings(db)
    finally:
        close_db(db)

    print(f"Jobs without embeddings: {len(jobs)}")
    if args.dry_run:
        print("Dry run — exiting without writing.")
        return

    if not jobs:
        print("Nothing to backfill.")
        return

    batch_size = args.batch_size
    total = 0
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i : i + batch_size]
        hashes = [j.job_hash for j in batch]
        descs = [j.description or "" for j in batch]

        print(f"  Embedding batch {i // batch_size + 1} ({len(batch)} jobs)...", end=" ", flush=True)
        vectors = embed_batch(descs)

        db = get_db()
        try:
            save_job_embeddings(hashes, vectors, db)
            db.commit()
        finally:
            close_db(db)

        total += len(batch)
        print(f"done. ({total}/{len(jobs)})")

    print(f"\nBackfill complete. Embedded {total} jobs.")


if __name__ == "__main__":
    main()
