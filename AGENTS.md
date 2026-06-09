# Internship Matcher — Agent Guide

This file is for AI coding agents (Codex, Gemini, Cursor, Copilot, etc.). It covers architecture, onboarding, and code review standards. Claude Code users get this via `.claude/skills/` — this file is the equivalent for everyone else.

---

## Architecture Overview

Internship Matcher is a full-stack web app for CS students looking for software internships. Users upload a resume PDF, the app extracts their skills, fetches current internship listings, and uses Claude to rank and explain the best matches. Users can also tailor their resume to a specific job.

### Tech Stack at a Glance

| Layer | What |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| AI | Anthropic Claude — Haiku 4.5 (fast/cheap ops), Sonnet 4.5 (deep ranking, resume tailoring) |
| Frontend | React 19 + TypeScript, React Router v7 |
| Auth | Clerk (frontend only — `useAuth()` + JWT sent to backend) |
| Database | SQLAlchemy 1.4 — SQLite in dev, Supabase PostgreSQL in prod |
| Cache | 3-tier: Redis (4h TTL) → SQLite/Postgres → in-memory dict |
| File Storage | AWS S3 (resume PDFs) |
| Resume Parsing | pdfplumber (PDF), pytesseract (images/OCR) |
| Resume Tailoring | Claude Sonnet rewrites resume JSON → pdflatex compiles LaTeX → PDF |
| Job Scraping | BeautifulSoup4 scraping SimplifyJobs GitHub README |
| Styling | Tailwind CSS v3 + shadcn/ui patterns (HSL CSS variables, CVA) |
| Streaming | SSE via sse-starlette (`/api/match-stream`) |
| Deployment | Railway (primary), Docker Compose available |

### End-to-End Matching Pipeline

When a user uploads a resume at `/api/match-stream`:

1. **Parse resume** — pdfplumber or pytesseract OCR extracts raw text
2. **Extract skills** — Claude Haiku pulls structured skills from resume text
3. **Fetch jobs** — Redis → DB → live scrape fallback (3-tier cache)
4. **Extract job skills** — Claude Haiku (cached per job hash so we don't re-call for the same job)
5. **Metadata scoring** — weighted: 40% experience level, 25% location, 20% industry, 15% citizenship
6. **Skill matching** — exact match + synonym normalization + difflib fuzzy fallback
7. **Deep ranking** — Claude Sonnet re-ranks top 30 → top 10 with explanations
8. **Stream results** — SSE events sent to the frontend with `step`, `message`, `progress` fields

**Think Deeper mode** — `think_deeper=true` triggers Claude extended thinking for deeper analysis.

### Key Files

```
app.py                          # All FastAPI routes + startup/shutdown lifecycle
job_database.py                 # SQLAlchemy ORM models (jobs, cache_metadata, resume_cache)
job_cache.py                    # 3-tier Redis + DB caching logic
matching/matcher.py             # Core orchestrator for the matching pipeline
matching/llm_skill_extractor.py # Claude skill extraction + deep ranking
resume_parser/parse_resume.py   # PDF/OCR parsing + skill extraction
resume_tailor/tailor_resume.py  # Claude rewrite + LaTeX PDF generation
job_scrapers/scrape_github_internships.py  # Primary job data source
frontend/src/pages/FindPage.tsx # Main app page (upload + streaming results)
frontend/src/components/JobCard.tsx        # Match result card
```

### Database Models

**`jobs`** — internship listings, deduplicated by SHA-256 of `(company + title + location + domain)`

**`resume_cache`** — matching results per user, keyed by `(user_id, resume_hash)`, 30-day TTL. Suffix `_deep` for think-deeper mode.

**`cache_metadata`** — tracks scrape operations and per-job skill cache entries.

No Alembic — schema is auto-created via `Base.metadata.create_all()`.

### Cost Sensitivity

Every user upload triggers multiple Claude API calls. Keep this in mind:
- Don't add new LLM calls without considering caching or batching
- Haiku for anything fast/cheap, Sonnet only for deep ranking and resume tailoring
- `TRACK_USAGE=true` enforces a per-upload cooldown in both frontend and backend — do not disable in production

---

## Getting Started (New Contributors)

### 1. Get Your Keys

You need two `.env` files. Start by copying the examples:

```bash
# From repo root
cp .env.example .env

# Frontend
cp frontend/.env.example frontend/.env
```

**Backend `.env` keys you need:**
- `CLAUDE_API_KEY` — get your own Anthropic API key at console.anthropic.com
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_BUCKET_NAME` — contact nandikolsujan@gmail.com to be added as an IAM user, or use your own S3 bucket
- `DATABASE_URL` — leave blank to use local SQLite, or get Supabase credentials from nandikolsujan@gmail.com
- `CLERK_PUBLISHABLE_KEY` — contact nandikolsujan@gmail.com
- `ENVIRONMENT=development`
- `SKIP_STARTUP_SCRAPE=1` (set this — don't hammer the scraping source on every dev restart)
- `TRACK_USAGE=true`

**Frontend `frontend/.env` keys you need:**
- `REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY` — same Clerk key, contact nandikolsujan@gmail.com
- `REACT_APP_API_URL=http://localhost:8000`
- `REACT_APP_ENVIRONMENT=development`
- `REACT_APP_TRACK_USAGE=true`

### 2. Install Dependencies

```bash
# Backend — use Python 3.11 (matches Docker/prod)
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# If you need Python 3.11 via pyenv:
brew install pyenv
pyenv install 3.11
pyenv local 3.11
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install
```

### 3. Run the Servers

```bash
# Backend (from repo root, venv activated)
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (separate terminal)
cd frontend && npm start
```

Frontend proxies `/api` → `localhost:8000` automatically via `setupProxy.js`.

Common issues:
- Port already in use: `kill -9 $(lsof -t -i:8000)` or `kill -9 $(lsof -t -i:3000)`
- Keys missing: check both `.env` (root) and `frontend/.env`
- Auth not working: you're missing the Clerk key — contact nandikolsujan@gmail.com

### 4. Run Tests

```bash
pytest tests/
```

Tests must pass before any PR is merged. CI runs them automatically on PRs.

---

## Code Review Standards

When reviewing or writing code in this repo, apply these standards:

### Correctness First

- **LLM calls must have error handling** — Claude API calls can fail or time out; always handle exceptions around `anthropic` client calls
- **Cache invalidation** — if you touch job data, make sure you're not serving stale results; understand the 3-tier cache before modifying `job_cache.py`
- **SSE streaming** — the frontend uses native `EventSource`; backend must send well-formed `data: ...\n\n` events or the stream silently breaks
- **Auth on protected routes** — `/api/match-stream`, `/api/tailor-resume`, `/api/user-history`, `/api/resume-cache/{hash}` all require a valid Clerk JWT. Any new user-specific endpoint must use the `require_user` dependency
- **Job deduplication** — jobs are deduplicated by SHA-256 of `(company + title + location + domain)`. Never insert without computing `job_hash` first

### Cost & Performance

- Default to Haiku (`claude-haiku-4-5-20251001`) for any new LLM call unless deep reasoning is required
- Sonnet (`claude-sonnet-4-5-20250929`) only for deep ranking and resume tailoring
- New LLM calls on the hot path (per-user-upload) must either be cached or justified
- Job skill extraction is cached per `job_hash` — don't break this cache

### Code Style

- No comments that describe what the code does — name things clearly instead
- No defensive error handling for scenarios that can't happen — trust FastAPI and SQLAlchemy guarantees
- No half-finished features — if it's not complete, don't merge it
- Prefer editing existing files over creating new ones
- shadcn/ui patterns for new frontend components: CVA + `cn()` util, HSL CSS variables

### Database

- No Alembic — schema changes go in `job_database.py` models and are applied via `create_all()`
- `is_active` is a soft delete — never hard-delete jobs, set `is_active = False`
- Always use `job_hash` for job lookups, not `id`

### Environment & Secrets

- Never hardcode API keys or secrets
- `TRACK_USAGE` and `SKIP_STARTUP_SCRAPE` are dev toggles — confirm they're set correctly before reviewing any env-related change
- Both `.env` files are gitignored — never commit them; update `.env.example` instead if you add a new variable

### Before Marking a PR Ready

- `pytest tests/` passes
- Frontend builds without errors: `cd frontend && npm run build`
- No new LLM calls on the hot path without caching consideration
- Auth dependencies present on any new user-specific endpoint
- `.env.example` updated if new env vars were added
