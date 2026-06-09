# Internship Matcher — Claude Context

## What This Project Does
A full-stack web app that matches students to software internships using AI. Users upload a resume (PDF), and the app extracts their skills, scrapes current internship listings, and uses Claude to rank and explain the best matches. Users can also tailor their resume to a specific job with AI.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI 0.109.2, Uvicorn |
| AI | Anthropic Claude (Haiku 4.5 for fast ops, Sonnet 4.5 for deep ops) |
| Frontend | React 19 + TypeScript (Create React App), React Router v7 |
| Auth | Clerk (`@clerk/react` v6) — frontend only, no server-side auth guards |
| Database | SQLAlchemy 1.4 + SQLite (dev) / Supabase PostgreSQL (prod) |
| Cache | Redis (4h TTL) + DB fallback + in-memory dict (3-tier) |
| File Storage | AWS S3 (resume files via boto3) |
| Resume Parsing | pdfplumber (PDF), pytesseract + Pillow (images/OCR) |
| Resume Tailoring | Claude Sonnet + LaTeX (pdflatex compiles to PDF) |
| Scraping | BeautifulSoup4 + requests (GitHub SimplifyJobs repo) |
| Styling | Tailwind CSS v3 + shadcn/ui patterns (HSL CSS variables, CVA) |
| Streaming | SSE via sse-starlette (`/api/match-stream`) |
| Deployment | Railway (primary), Docker Compose, AWS EC2 (alternatives) |

---

## Project Structure

```
/
├── app.py                    # FastAPI app — all routes, startup/shutdown lifecycle
├── job_database.py           # SQLAlchemy ORM models (jobs, cache_metadata, resume_cache)
├── job_cache.py              # Hybrid Redis + DB caching layer
├── s3_service.py             # AWS S3 resume upload/download
├── main.py                   # CLI entry point for local testing
├── requirements.txt
├── Dockerfile                # Single-container build (backend + React build)
├── docker-compose.yml        # Full stack: Redis + Backend + Nginx
├── railway.toml              # Railway PaaS config
├── nginx.conf                # Reverse proxy config
├── start.sh                  # Dev startup script
│
├── job_scrapers/
│   ├── dispatcher.py         # Scraping orchestrator
│   └── scrape_github_internships.py  # PRIMARY active scraper (SimplifyJobs GitHub repo)
│   # scrape_google/meta/microsoft/salesforce.py — DISABLED (Selenium issues)
│
├── matching/
│   ├── matcher.py            # Core matching engine — orchestrates full pipeline
│   ├── llm_skill_extractor.py # Claude skill extraction + deep ranking + candidate profiling
│   ├── metadata_matcher.py   # Weighted metadata scoring (location, experience level, etc.)
│   └── llm_processing_node.py
│
├── resume_parser/
│   └── parse_resume.py       # PDF/image parsing + Claude skill extraction
│
├── resume_tailor/
│   ├── tailor_resume.py      # Claude-powered resume rewrite + LaTeX PDF generation
│   └── template.tex          # LaTeX template
│
├── email_sender/
│   └── generate_email.py
│
├── tests/                    # pytest test suite
│
└── frontend/                 # React CRA app
    ├── src/
    │   ├── App.tsx            # Root: routes + ClerkProvider
    │   ├── pages/
    │   │   ├── LandingPage.tsx   # /  — marketing page
    │   │   ├── FindPage.tsx      # /find — main app (upload + results)
    │   │   ├── HistoryPage.tsx   # /history — past analyses
    │   │   ├── LoginPage.tsx     # /login
    │   │   └── HomePage.tsx
    │   ├── components/
    │   │   ├── JobCard.tsx       # Rich match result card with score + reasoning
    │   │   ├── Header.tsx
    │   │   ├── ResumeUploadForm.tsx
    │   │   └── ui/               # shadcn-style primitives
    │   └── lib/
    │       └── supabaseClient.ts # Supabase client (supports Clerk JWT)
    ├── package.json
    └── tailwind.config.js
```

---

## Development Commands

```bash
# Backend
uvicorn app:app --host 0.0.0.0 --port 8000 --reload

# Frontend (proxies /api → localhost:8000 via setupProxy.js)
cd frontend && npm start

# Both together
./start.sh --all

# Tests
pytest tests/

# Production build (Railway runs this)
pip install -r requirements.txt
cd frontend && npm install && npm run build
uvicorn app:app --host 0.0.0.0 --port $PORT
```

---

## API Routes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/match` | Upload resume → get matched jobs (JSON) |
| POST | `/api/match-stream` | Same but SSE streaming with real-time progress |
| GET | `/api/resume-cache/{hash}` | Check if resume results are cached |
| GET | `/api/user-history` | User's past resume analyses |
| POST | `/api/tailor-resume` | Generate tailored PDF resume for a job |
| GET | `/api/cache-status` | Redis + DB cache health |
| POST | `/api/refresh-cache` | Manually trigger full job scrape |
| POST | `/api/refresh-cache-incremental` | Incremental scrape |
| GET | `/api/database-stats` | DB statistics |
| GET | `/{full_path}` | Catch-all → serves React SPA `index.html` |

---

## AI / Matching Pipeline

The main flow for `/api/match-stream`:

1. **Parse resume** — pdfplumber or pytesseract OCR
2. **Extract skills** — Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)
3. **Fetch jobs** — Redis cache → DB → scrape fallback
4. **Extract job skills** — Claude Haiku 4.5 (cached per job hash, 3-tier)
5. **Metadata scoring** — weighted: 40% experience, 25% location, 20% industry, 15% citizenship
6. **Skill matching** — exact match + synonym normalization + difflib fuzzy fallback
7. **Deep ranking** — Claude Sonnet 4.5 (`claude-sonnet-4-5-20250929`) re-ranks top 30 → top 10
8. **Stream results** — SSE events with `step`, `message`, `progress` fields

**"Think Deeper" mode** — extended analysis with Claude extended thinking, triggered by `think_deeper=true`.

**Resume tailoring** — Claude Sonnet 4.5 rewrites resume JSON for a target job, then pdflatex compiles LaTeX → PDF (tries font sizes 11→8 to fit one page).

---

## Database Models (`job_database.py`)

**`jobs`** — internship listings
- `job_hash` (SHA-256 of company+title+location+domain) — deduplication key
- `required_skills`, `job_metadata` stored as JSON strings
- `is_active` — soft delete; jobs inactive if `last_seen` > 3 days or `days_since_posted` > 30

**`cache_metadata`** — tracks scrape operations and job skill cache entries
- `cache_type` can be `'daily'`, `'full'`, or `'job_skills_{hash}'`

**`resume_cache`** — caches matching results per user
- Keyed by `(user_id, resume_hash)` — suffix `_deep` for think-deeper mode
- 30-day TTL via `expires_at`

Schema auto-created via `Base.metadata.create_all()` — no Alembic migration files exist.

---

## Caching

| Tier | Store | TTL | Key |
|------|-------|-----|-----|
| 1 | Redis | 4 hours | `internship_jobs_cache` |
| 2 | SQLite/PostgreSQL | persistent | `jobs` table |
| 3 | In-memory dict | process lifetime | content hash |

Resume results cached in `resume_cache` table (30 days). Background `asyncio` task refreshes jobs every 24h.

---

## Authentication

- **Frontend:** Clerk (`useAuth()` hook) — `getToken()` fetches a short-lived JWT sent as `Authorization: Bearer <token>` on all user-specific API calls
- **Backend:** `auth.py` — `require_user` FastAPI dependency verifies the Clerk JWT via JWKS (RS256), returns the verified `user_id` from the `sub` claim. Raises 401 if missing/invalid/expired.
- Protected endpoints: `/api/resume-cache/{hash}`, `/api/user-history`, `/api/match-stream`, `/api/tailor-resume`
- **Supabase:** Frontend Supabase client optionally uses Clerk JWT for RLS, but it's not enforced
- `CLERK_PUBLISHABLE_KEY` backend env var (same value as `REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY`) is required for JWKS URL derivation
- Auth was migrated: Google OAuth → Stack Auth → Clerk (some legacy code remains)

---

## Environment Variables

**Backend (Python):**
```
CLAUDE_API_KEY          # Anthropic API key
DATABASE_URL            # PostgreSQL URL (Supabase) — defaults to sqlite:///./jobs.db
REDIS_URL               # Redis URL — defaults to redis://localhost:6379
AWS_ACCESS_KEY_ID       # S3 credentials
AWS_SECRET_ACCESS_KEY
AWS_REGION              # default: us-east-1
AWS_BUCKET_NAME         # S3 bucket for resumes
SECRET_KEY              # Session middleware secret
ENVIRONMENT             # "development" or "production"
PORT                    # Injected by Railway/Render
CLERK_PUBLISHABLE_KEY   # Same as REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY — used to derive JWKS URL
```

**Frontend (React, baked in at build time):**
```
REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY
REACT_APP_SUPABASE_URL
REACT_APP_SUPABASE_ANON_KEY
REACT_APP_API_URL       # Backend URL (dev only; prod uses relative URLs)
```

---

## Deployment

**Railway (primary):**
- Dockerfile-based, single container (Python backend serves React build)
- `railway.toml` configures build and start commands
- `frontend/build/` is committed and served by FastAPI static mount

**Docker Compose:**
- 3 services: Redis, FastAPI backend, Nginx+frontend
- `docker-compose.yml` + `nginx.conf`

**AWS EC2:**
- `setup-ec2.sh` and `deploy.sh` available

**Production URL:** `https://internship-app-production.up.railway.app`

---

## Key Patterns

- **SPA serving:** FastAPI serves `frontend/build/index.html` via catch-all route `/{full_path:path}` in production
- **Dev proxy:** `frontend/src/setupProxy.js` proxies `/api` → `localhost:8000`
- **SSE streaming:** `EventSourceResponse` from sse-starlette; frontend uses native `EventSource` API
- **Job deduplication:** SHA-256 of `(company + title + location + domain)` → `job_hash`
- **Background tasks:** `asyncio.create_task()` for scraping/refresh; cleaned up on app shutdown
- **API URL detection:** `FindPage.tsx` checks `NODE_ENV === 'development'` to pick base URL
- **shadcn patterns:** Components use CVA + `cn()` util, HSL CSS variables for theming
- **LaTeX PDF:** `pdflatex` must be installed in the container for resume tailoring to work

---

## Supabase Project
- Project ID: `gninorapexsxsfbtyajl`
- Used for: `resume_cache` and user history (via frontend Supabase client)

## Job Data Source
- GitHub: `SimplifyJobs/Summer2026-Internships` README.md (parsed via BeautifulSoup)
- Other scrapers (Google, Meta, Microsoft, Salesforce) exist but are **disabled**
