#!/usr/bin/env python3
"""
Cache Health Check Script
Run this to diagnose cache/job issues in production
"""
import os
from datetime import datetime, timedelta
from job_database import get_db, Job, get_database_stats
from sqlalchemy import func
import json

def check_cache_health():
    """Check the health of the job cache and database"""
    print("=" * 60)
    print("JOB CACHE HEALTH CHECK")
    print("=" * 60)

    db = get_db()
    try:
        # Get overall stats
        stats = get_database_stats()
        print(f"\n📊 DATABASE STATS:")
        print(f"   Total jobs: {stats.get('total_jobs', 0)}")
        print(f"   Active jobs: {stats.get('active_jobs', 0)}")
        print(f"   Inactive jobs: {stats.get('inactive_jobs', 0)}")
        print(f"   New jobs (24h): {stats.get('new_jobs_24h', 0)}")

        # Check job age distribution
        print(f"\n📅 JOB AGE DISTRIBUTION:")
        active_jobs = db.query(Job).filter(Job.is_active == True).all()

        age_buckets = {
            '0-7 days': 0,
            '8-14 days': 0,
            '15-30 days': 0,
            '31-60 days': 0,
            '60+ days': 0,
            'no date info': 0
        }

        for job in active_jobs:
            try:
                metadata = json.loads(job.job_metadata) if job.job_metadata else {}
                days_since = metadata.get('days_since_posted')

                if days_since is None:
                    age_buckets['no date info'] += 1
                elif days_since <= 7:
                    age_buckets['0-7 days'] += 1
                elif days_since <= 14:
                    age_buckets['8-14 days'] += 1
                elif days_since <= 30:
                    age_buckets['15-30 days'] += 1
                elif days_since <= 60:
                    age_buckets['31-60 days'] += 1
                else:
                    age_buckets['60+ days'] += 1
            except:
                age_buckets['no date info'] += 1

        for bucket, count in age_buckets.items():
            percentage = (count / len(active_jobs) * 100) if active_jobs else 0
            print(f"   {bucket}: {count} jobs ({percentage:.1f}%)")

        # Check last_seen timestamps
        print(f"\n🕒 LAST SEEN DISTRIBUTION:")
        now = datetime.utcnow()

        seen_buckets = {
            '< 1 hour': 0,
            '1-6 hours': 0,
            '6-24 hours': 0,
            '1-3 days': 0,
            '3-7 days': 0,
            '7+ days': 0
        }

        for job in active_jobs:
            time_diff = now - job.last_seen
            hours = time_diff.total_seconds() / 3600

            if hours < 1:
                seen_buckets['< 1 hour'] += 1
            elif hours < 6:
                seen_buckets['1-6 hours'] += 1
            elif hours < 24:
                seen_buckets['6-24 hours'] += 1
            elif hours < 72:
                seen_buckets['1-3 days'] += 1
            elif hours < 168:
                seen_buckets['3-7 days'] += 1
            else:
                seen_buckets['7+ days'] += 1

        for bucket, count in seen_buckets.items():
            percentage = (count / len(active_jobs) * 100) if active_jobs else 0
            print(f"   {bucket}: {count} jobs ({percentage:.1f}%)")

        # Show sample of most recent jobs
        print(f"\n📋 MOST RECENT JOBS (by last_seen):")
        recent = db.query(Job).filter(Job.is_active == True).order_by(Job.last_seen.desc()).limit(5).all()
        for i, job in enumerate(recent):
            metadata = json.loads(job.job_metadata) if job.job_metadata else {}
            days_since = metadata.get('days_since_posted', 'unknown')
            print(f"   {i+1}. {job.company} - {job.title}")
            print(f"      Last seen: {job.last_seen}")
            print(f"      Days since posted: {days_since}")

        # Show sample of oldest jobs
        print(f"\n📋 OLDEST JOBS (by posting date in metadata):")
        oldest_jobs = []
        for job in active_jobs:
            try:
                metadata = json.loads(job.job_metadata) if job.job_metadata else {}
                days_since = metadata.get('days_since_posted')
                if days_since is not None:
                    oldest_jobs.append((job, days_since))
            except:
                pass

        oldest_jobs.sort(key=lambda x: x[1], reverse=True)
        for i, (job, days_since) in enumerate(oldest_jobs[:5]):
            print(f"   {i+1}. {job.company} - {job.title}")
            print(f"      Last seen: {job.last_seen}")
            print(f"      Days since posted: {days_since}")

        # Check for jobs that should be inactive
        print(f"\n⚠️  JOBS THAT SHOULD BE MARKED INACTIVE (>30 days old):")
        should_be_inactive = []
        for job in active_jobs:
            try:
                metadata = json.loads(job.job_metadata) if job.job_metadata else {}
                days_since = metadata.get('days_since_posted')
                if days_since is not None and days_since > 30:
                    should_be_inactive.append((job, days_since))
            except:
                pass

        if should_be_inactive:
            print(f"   Found {len(should_be_inactive)} jobs that should be inactive!")
            for i, (job, days_since) in enumerate(should_be_inactive[:10]):
                print(f"   {i+1}. {job.company} - {job.title} ({days_since} days old)")
        else:
            print(f"   ✅ All active jobs are within 30-day threshold")

        # Check cache metadata
        print(f"\n🔄 RECENT CACHE OPERATIONS:")
        from job_database import CacheMetadata
        recent_ops = db.query(CacheMetadata).order_by(CacheMetadata.last_updated.desc()).limit(5).all()

        if recent_ops:
            for i, op in enumerate(recent_ops):
                time_ago = datetime.utcnow() - op.last_updated
                hours_ago = time_ago.total_seconds() / 3600
                print(f"   {i+1}. {op.cache_type} - {op.status}")
                print(f"      Time: {op.last_updated} ({hours_ago:.1f}h ago)")
                print(f"      Jobs: {op.job_count} total, {op.new_jobs_added} new")
        else:
            print(f"   ⚠️  No cache operations recorded")

        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")

        if should_be_inactive:
            print(f"   ⚠️  {len(should_be_inactive)} jobs are >30 days old but still active")
            print(f"      → Run manual cache refresh to clean up old jobs")

        if age_buckets['60+ days'] > 0:
            print(f"   ⚠️  {age_buckets['60+ days']} jobs are >60 days old")
            print(f"      → These should definitely be marked inactive")

        if not recent_ops or (recent_ops and (datetime.utcnow() - recent_ops[0].last_updated).days > 2):
            print(f"   ⚠️  No recent cache operations in last 2 days")
            print(f"      → Daily refresh task may not be running")
            print(f"      → Check server logs for refresh task messages")

        if age_buckets['0-7 days'] < stats.get('active_jobs', 0) * 0.2:
            print(f"   ⚠️  Less than 20% of jobs are from last 7 days")
            print(f"      → Cache may not be refreshing regularly")

        print(f"\n✅ HEALTH CHECK COMPLETE")

    except Exception as e:
        print(f"❌ Error during health check: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_cache_health()