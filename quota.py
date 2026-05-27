"""Weekly per-user quota for the resume-tailoring feature, backed by Postgres."""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from job_database import TailorRequestLog

WEEKLY_TAILOR_LIMIT = 5
WEEKLY_WINDOW = timedelta(days=7)


def get_tailor_quota_status(db: Session, user_id: str) -> dict:
    """
    Return the current quota state for a user.

    Returns a dict with:
      limit      — the cap (5)
      used       — requests in the last 7 days
      remaining  — slots left
      reset_at   — ISO datetime string when the oldest slot frees up (None if nothing used)
    """
    window_start = datetime.utcnow() - WEEKLY_WINDOW
    rows = (
        db.query(TailorRequestLog)
        .filter(
            TailorRequestLog.user_id == user_id,
            TailorRequestLog.requested_at > window_start,
        )
        .order_by(TailorRequestLog.requested_at.asc())
        .all()
    )
    used = len(rows)
    remaining = max(0, WEEKLY_TAILOR_LIMIT - used)
    # Reset time = the moment the oldest in-window row falls out of the window
    oldest_in_window: Optional[datetime] = rows[0].requested_at if rows else None
    reset_at: Optional[datetime] = (oldest_in_window + WEEKLY_WINDOW) if oldest_in_window else None

    return {
        "limit": WEEKLY_TAILOR_LIMIT,
        "used": used,
        "remaining": remaining,
        "reset_at": reset_at,
    }


def record_tailor_request(db: Session, user_id: str, job_title: str, company: str) -> None:
    """Insert a new log row. Caller is responsible for db.commit()."""
    entry = TailorRequestLog(
        user_id=user_id,
        job_title=job_title[:500] if job_title else None,
        company=company[:500] if company else None,
    )
    db.add(entry)
