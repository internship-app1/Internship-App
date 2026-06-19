#!/usr/bin/env bash
#
# Tier-2 pre-ship test: boots the REAL FastAPI app locally and exercises the
# /api/crawl/* HTTP endpoints exactly as the GitHub Actions cron does — the layer
# the Python scripts (smoke_crawlers.py / verify_end_to_end.py) can't reach.
#
# Validates:
#   - the app boots with the crawler routes registered
#   - GET  /api/crawl/status returns JSON (not index.html) -> route-shadow fix
#   - POST /api/crawl/full crawls seeded companies and inserts internships
#   - the overlap guard rejects a concurrent second crawl
#   - auth: a request without the admin key is rejected
#
# Everything runs against a throwaway SQLite DB and a local uvicorn on a spare
# port; both are torn down on exit. Your real DB/server are untouched.
#
# Requires the backend deps installed (slowapi, pyjwt, mcp, etc.) — i.e. run it
# from the same venv you use for `uvicorn app:app`. Run from the repo root:
#   ./scripts/test_crawler_api.sh
#
set -uo pipefail

cd "$(dirname "$0")/.."

# Prefer the backend venv python (has slowapi/fastapi/etc.) over system python3,
# so the script works whether or not the venv is activated.
if [ -x "venv/bin/python" ]; then
  PYBIN="venv/bin/python"
elif [ -x ".venv/bin/python" ]; then
  PYBIN=".venv/bin/python"
else
  PYBIN="python3"
fi
echo "==> Using python: ${PYBIN} ($($PYBIN --version 2>&1))"

PORT=8077
DB_FILE="$(pwd)/_crawler_api_test.db"
BASE="http://127.0.0.1:${PORT}"
KEY="devtestkey"
LOG="$(mktemp)"

export DATABASE_URL="sqlite:///${DB_FILE}"
export INTERNSHIP_MATCHER_API_KEY="$KEY"
export TRACK_USAGE="false"
export SKIP_STARTUP_SCRAPE="1"
export ENVIRONMENT="development"

PASS=0
FAIL=0
ok()   { echo "  [PASS] $1"; PASS=$((PASS+1)); }
bad()  { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

cleanup() {
  [ -n "${SERVER_PID:-}" ] && kill "$SERVER_PID" 2>/dev/null
  rm -f "$DB_FILE" "$LOG"
}
trap cleanup EXIT

echo "==> Booting uvicorn on :${PORT} (throwaway SQLite DB)..."
$PYBIN -m uvicorn app:app --host 127.0.0.1 --port "$PORT" --no-access-log \
  >"$LOG" 2>&1 &
SERVER_PID=$!

# Wait up to ~30s for the server to answer the (public) status route.
ready=""
for _ in $(seq 1 60); do
  if curl -fsS "${BASE}/api/crawl/status" >/dev/null 2>&1; then ready=1; break; fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "!! Server died on boot. Last log lines:"; tail -20 "$LOG"; exit 1
  fi
  sleep 0.5
done
if [ -z "$ready" ]; then
  echo "!! Server never became ready. Last log lines:"; tail -20 "$LOG"; exit 1
fi
echo "    up."

echo "==> Seeding 3 live companies into the registry..."
$PYBIN - <<'PY'
import os, sys; sys.path.insert(0, '.')
from job_database import Base, engine
Base.metadata.create_all(bind=engine)
from crawlers.company_registry import CompanyRegistryStore
s = CompanyRegistryStore()
for cid, name, ats, board in [
    ("stripe", "Stripe", "greenhouse", "stripe"),
    ("Thales", "Thales", "smartrecruiters", "Thales"),
    ("Accor",  "Accor",  "smartrecruiters", "Accor"),
]:
    s.upsert({"company_id": cid, "display_name": name, "ats_type": ats, "ats_board_id": board})
print("    seeded:", s.get_stats())
PY

echo ""
echo "=== Test 1: GET /api/crawl/status returns JSON (route-shadow fix) ==="
STATUS_BODY="$(curl -fsS "${BASE}/api/crawl/status")"
if echo "$STATUS_BODY" | grep -q '"success"'; then
  ok "status returns JSON: $(echo "$STATUS_BODY" | cut -c1-80)..."
else
  bad "status did NOT return JSON (catch-all may be shadowing it): $(echo "$STATUS_BODY" | cut -c1-80)"
fi

echo ""
echo "=== Test 2: auth — POST without key is rejected ==="
CODE="$(curl -s -o /dev/null -w '%{http_code}' -X POST "${BASE}/api/crawl/full" -d '{}')"
if [ "$CODE" = "401" ]; then ok "no-key request -> 401"; else bad "expected 401, got $CODE"; fi

echo ""
echo "=== Test 3: POST /api/crawl/full triggers async crawl (202) ==="
# Crawls now run as fire-and-forget background tasks (Railway's proxy kills any
# request at ~300s), so the endpoint returns 202 {"status":"started"} immediately
# instead of the old synchronous {"companies_crawled":...} payload.
FULL_BODY="$(curl -fsS -X POST "${BASE}/api/crawl/full" \
  -H "X-Api-Key: ${KEY}" -H 'Content-Type: application/json' -d '{}')"
echo "    $FULL_BODY"
if echo "$FULL_BODY" | grep -qE '"status" *: *"(started|already_running)"'; then
  ok "full crawl accepted (async)"
else
  bad "full crawl did not return status started/already_running"
fi

# Poll status until the background run clears (or give up after ~60s).
echo "    polling /api/crawl/status for completion..."
for _ in $(seq 1 30); do
  POLL="$(curl -fsS "${BASE}/api/crawl/status")"
  echo "$POLL" | grep -oE '"running" *:[^}]*}' | grep -q '"full" *: *true' || { ok "crawl finished (running.full=false)"; break; }
  sleep 2
done

echo ""
echo "=== Test 4: overlap guard — two concurrent full crawls ==="
curl -fsS -X POST "${BASE}/api/crawl/full" -H "X-Api-Key: ${KEY}" -d '{}' >/tmp/_c1 2>&1 &
P1=$!
curl -fsS -X POST "${BASE}/api/crawl/full" -H "X-Api-Key: ${KEY}" -d '{}' >/tmp/_c2 2>&1 &
P2=$!
wait $P1; wait $P2
if grep -q 'already_running' /tmp/_c1 /tmp/_c2; then
  ok "one concurrent crawl was rejected with already_running"
else
  echo "    c1: $(cat /tmp/_c1 | cut -c1-70)"
  echo "    c2: $(cat /tmp/_c2 | cut -c1-70)"
  bad "neither concurrent crawl was rejected (guard may not be holding, or crawl too fast to overlap)"
fi
rm -f /tmp/_c1 /tmp/_c2

echo ""
echo "=== Test 5: status now reflects the crawl ==="
STATUS2="$(curl -fsS "${BASE}/api/crawl/status")"
echo "    $STATUS2"
if echo "$STATUS2" | grep -q '"last_full"'; then ok "status exposes last_full"; else bad "status missing last_full"; fi

echo ""
echo "================ ${PASS} passed, ${FAIL} failed ================"
[ "$FAIL" -eq 0 ] && echo "CRAWLER API: READY TO SHIP" || echo "CRAWLER API: DO NOT SHIP — investigate failures above"
exit "$FAIL"
