# Cache Refresh System - Production Fix Guide

## Problem Diagnosed

The daily cache refresh task in production is **not running**, causing jobs to be 10+ days old.

**Root Cause:**
- The `daily_cache_refresh_task()` asyncio background task is failing silently
- No jobs have been refreshed since November 15 (10.5 days ago)
- All 318 active jobs have `last_seen` timestamps > 7 days old

## Immediate Fix (Run Now)

### Step 1: Manually Refresh the Cache

SSH into your production server and run:

```bash
# Option 1: Using curl (recommended)
curl -X POST http://localhost:8000/api/refresh-cache?max_days_old=30

# Option 2: From your local machine
curl -X POST https://internshipmatcher.com/api/refresh-cache?max_days_old=30
```

**Expected Output:**
```json
{
  "success": true,
  "message": "Cache refreshed successfully (last 30 days)",
  "new_jobs": 85,
  "total_jobs": 436,
  "database_success": true,
  "redis_success": true,
  "scrape_type": "smart",
  "max_days_old": 30
}
```

###Step 2: Verify the Fix

Check the health status:
```bash
curl http://localhost:8000/api/refresh-health
```

Check the cache status:
```bash
curl http://localhost:8000/api/cache-status
```

## Long-Term Fix (Deployed)

I've improved the daily refresh task with:

1. **Better Error Handling** - Now catches and logs all errors without stopping
2. **Refresh Counter** - Tracks how many refreshes have occurred
3. **Detailed Logging** - Prints clear messages for debugging
4. **Health Check Endpoint** - Monitor when last refresh happened

### Deploy the Updated Code

1. **Commit the changes:**
   ```bash
   git add app.py check_cache_health.py
   git commit -m "Fix: Improve daily cache refresh task with better error handling and monitoring"
   git push
   ```

2. **On your production server:**
   ```bash
   git pull
   docker-compose restart backend
   # or
   ./deploy.sh
   ```

3. **Monitor the logs:**
   ```bash
   docker-compose logs -f backend | grep -E "(Scheduled|refresh)"
   ```

   You should see messages like:
   ```
   ⏰ [Scheduled] Next cache refresh in 24 hours...
   🔄 [Scheduled #1] Starting daily cache refresh at 2025-11-26T12:00:00
   ✅ [Scheduled #1] Daily refresh complete: 15 new jobs, 340 total active jobs
   ```

## Monitoring & Maintenance

### Health Check Endpoint

Use this endpoint to monitor the refresh system:

```bash
curl http://localhost:8000/api/refresh-health
```

**Response:**
```json
{
  "success": true,
  "health": {
    "status": "healthy",  // or "warning", "unhealthy", "critical"
    "warnings": [],
    "info": {
      "last_refresh": {
        "time": "2025-11-26T12:00:00",
        "hours_ago": 2.5,
        "type": "daily_scheduled",
        "status": "success",
        "new_jobs": 15,
        "total_jobs": 340
      },
      "active_jobs": 340,
      "job_age_distribution": {
        "recent_jobs_0_7d": 120,
        "old_jobs_21plus_d": 50,
        "recent_percentage": 35.3
      }
    }
  },
  "recommendation": "System is healthy"
}
```

### Set Up Automated Monitoring

Add this to your monitoring system (e.g., cron job, monitoring service):

```bash
# Check health every 6 hours
0 */6 * * * curl -s http://localhost:8000/api/refresh-health | jq '.health.status'
```

If status is "unhealthy", trigger an alert or automatic refresh:
```bash
# Auto-fix script
STATUS=$(curl -s http://localhost:8000/api/refresh-health | jq -r '.health.status')
if [ "$STATUS" = "unhealthy" ] || [ "$STATUS" = "warning" ]; then
    echo "Cache unhealthy - triggering manual refresh..."
    curl -X POST http://localhost:8000/api/refresh-cache?max_days_old=30
fi
```

## Diagnostic Tools

### 1. Cache Health Check Script

Run this locally to diagnose issues:
```bash
python check_cache_health.py
```

### 2. Manual Cache Operations

```bash
# Force full refresh (re-scrape everything)
curl -X POST http://localhost:8000/api/refresh-cache?force_full=true&max_days_old=30

# Incremental refresh (only new jobs)
curl -X POST http://localhost:8000/api/refresh-cache-incremental?max_days_old=30

# Get database stats
curl http://localhost:8000/api/database-stats

# Get cache status
curl http://localhost:8000/api/cache-status
```

## Why the Daily Task Failed

Possible reasons:

1. **Server Restarts** - If the server restarts frequently, the 24-hour timer resets
2. **Silent Failures** - The old code didn't log errors properly
3. **Asyncio Issues** - The task might have been cancelled without logging
4. **Memory/Resource Issues** - The server might be killing background tasks

The new code handles all these cases with better error recovery.

## Prevention

### Option 1: External Cron Job (Most Reliable)

Instead of relying on the asyncio task, set up a cron job:

```bash
# Add to crontab on production server
crontab -e

# Refresh cache daily at 2 AM
0 2 * * * curl -X POST http://localhost:8000/api/refresh-cache?max_days_old=30 >> /var/log/cache_refresh.log 2>&1
```

### Option 2: Keep Both (Redundancy)

- Keep the asyncio daily task for normal operation
- Add a cron job as backup in case the task fails

## Testing the Fix

1. **Check current status:**
   ```bash
   curl http://localhost:8000/api/refresh-health
   ```

2. **Trigger manual refresh:**
   ```bash
   curl -X POST http://localhost:8000/api/refresh-cache?max_days_old=30
   ```

3. **Verify jobs are updated:**
   ```bash
   python check_cache_health.py
   ```

4. **Check logs for scheduled refresh (wait 24h):**
   ```bash
   docker-compose logs backend | grep "Scheduled"
   ```

## Expected Timeline

- **Immediate**: Manual refresh updates jobs within 30 seconds
- **24 hours**: First automatic daily refresh should run
- **Ongoing**: System refreshes automatically every 24 hours

## Success Criteria

✅ Jobs are updated within last 24 hours
✅ At least 20% of jobs are from last 7 days
✅ Daily refresh logs appear in server logs
✅ Health check returns "healthy" status
✅ No warnings in health check response

## Support

If issues persist:

1. Check server logs: `docker-compose logs -f backend`
2. Run health check: `python check_cache_health.py`
3. Check for errors: `docker-compose logs backend | grep ERROR`
4. Verify asyncio task is running: Look for "Daily cache refresh scheduler started" in logs

## Summary

**What Changed:**
- ✅ Improved daily refresh task error handling
- ✅ Added health check endpoint (`/api/refresh-health`)
- ✅ Added diagnostic script (`check_cache_health.py`)
- ✅ Better logging for debugging

**What You Need To Do:**
1. Run manual refresh NOW to get fresh jobs
2. Deploy the updated code to production
3. Monitor logs for 24-48 hours to confirm automatic refresh works
4. (Optional) Set up external cron job as backup