# Internship Matcher

An AI-powered web app that matches students to software internships. Upload your resume, and the app extracts your skills, scrapes current internship listings, and uses Claude to rank and explain the best matches. You can also tailor your resume to a specific job with one click.

**Live:** [internshipmatcher.com](https://internship-app-production.up.railway.app)

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [API Routes](#api-routes)
- [AI & Matching Pipeline](#ai--matching-pipeline)
- [Authentication](#authentication)
- [Database](#database)
- [Caching](#caching)
- [Deployment](#deployment)

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI 0.109.2, Uvicorn |
| AI | Anthropic Claude — Haiku 4.5 (fast ops), Sonnet 4.5 (deep ops) |
| Frontend | React 19 + TypeScript, React Router v7 |
| Auth | Clerk (`@clerk/react` v6) |
| Database | SQLAlchemy 1.4 + SQLite (dev) / Supabase PostgreSQL (prod) |
| Cache | Redis (4h TTL) + DB fallback + in-memory dict (3-tier) |
| File Storage | AWS S3 (resume files via boto3) |
| Resume Parsing | pdfplumber (PDF), pytesseract + Pillow (OCR for images) |
| Resume Tailoring | Claude Sonnet + LaTeX (pdflatex compiles to PDF) |
| Scraping | BeautifulSoup4 + requests (SimplifyJobs GitHub repo) |
| Styling | Tailwind CSS v3 + shadcn/ui patterns (HSL CSS variables, CVA) |
| Streaming | SSE via sse-starlette |
| Deployment | Railway (primary), Docker Compose |

---

## Project Structure

```
/
├── app.py                    # FastAPI app — all routes, startup/shutdown lifecycle
├── job_database.py           # SQLAlchemy ORM models (jobs, cache_metadata, resume_cache)
├── job_cache.py              # Hybrid Redis + DB caching layer
├── s3_service.py             # AWS S3 resume upload/download
├── auth.py                   # Clerk JWT verification (RS256 via JWKS)
├── requirements.txt
├── Dockerfile                # Single-container build (backend + React build)
├── docker-compose.yml        # Full stack: Redis + Backend + Nginx
├── railway.toml              # Railway PaaS config
├── nginx.conf                # Reverse proxy config
├── start.sh                  # Dev startup script (./start.sh --all for both services)
│
├── job_scrapers/
│   ├── dispatcher.py         # Scraping orchestrator
│   └── scrape_github_internships.py  # Active scraper (SimplifyJobs/Summer2026-Internships)
│
├── matching/
│   ├── matcher.py            # Core matching engine
│   ├── llm_skill_extractor.py # Claude skill extraction + deep ranking
│   ├── metadata_matcher.py   # Weighted metadata scoring
│   └── llm_processing_node.py
│
├── resume_parser/
│   └── parse_resume.py       # PDF/image parsing + Claude skill extraction
│
├── resume_tailor/
│   ├── tailor_resume.py      # Claude-powered resume rewrite + LaTeX PDF generation
│   └── template.tex          # LaTeX template
│
├── tests/                    # pytest test suite
│
└── frontend/
    └── src/
        ├── App.tsx            # Root: routes + ClerkProvider
        ├── pages/
        │   ├── LandingPage.tsx   # /  — marketing page
        │   ├── FindPage.tsx      # /find — main app (upload + results)
        │   ├── HistoryPage.tsx   # /history — past analyses
        │   ├── UsagePage.tsx     # /usage — weekly quota dashboard
        │   └── LoginPage.tsx     # /login
        ├── components/
        │   ├── JobCard.tsx       # Match result card with score + reasoning
        │   ├── Header.tsx
        │   └── ResumeUploadForm.tsx
        └── lib/
            └── supabaseClient.ts
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Redis (optional — app falls back to DB cache without it)
- `pdflatex` installed (required for resume tailoring)
- Supabase project (prod) or SQLite (dev, automatic)

### Installation

1. **Clone and install dependencies**
   ```bash
   git clone <repository-url>
   cd Internship-App
   pip install -r requirements.txt
   cd frontend && npm install && cd ..
   ```

2. **Set up environment variables**

   Create a `.env` file:
   ```bash
   # Anthropic
   CLAUDE_API_KEY=sk-ant-...

   # AWS S3 (resume storage)
   AWS_ACCESS_KEY_ID=...
   AWS_SECRET_ACCESS_KEY=...
   AWS_REGION=us-east-1
   AWS_BUCKET_NAME=...

   # Database (omit for SQLite dev default)
   DATABASE_URL=postgresql://...

   # Redis (optional)
   REDIS_URL=redis://localhost:6379

   # Auth
   SECRET_KEY=...
   CLERK_PUBLISHABLE_KEY=pk_...

   # Frontend (React, baked in at build time)
   REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY=pk_...
   REACT_APP_SUPABASE_URL=...
   REACT_APP_SUPABASE_ANON_KEY=...
   ```

3. **Start development servers**
   ```bash
   # Both backend + frontend together
   ./start.sh --all

   # Or separately
   uvicorn app:app --host 0.0.0.0 --port 8000 --reload
   cd frontend && npm start
   ```

   Backend: `http://localhost:8000` | Frontend: `http://localhost:3001`

4. **Run tests**
   ```bash
   pytest tests/
   ```

---

## API Routes

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/match` | Required | Upload resume → matched jobs (JSON) |
| POST | `/api/match-stream` | Required | Same but SSE streaming with real-time progress |
| GET | `/api/resume-cache/{hash}` | Required | Check if resume results are cached |
| GET | `/api/user-history` | Required | User's past resume analyses |
| POST | `/api/tailor-resume` | Required | Generate tailored PDF resume for a job |
| GET | `/api/usage` | Required | Weekly quota status for all AI features |
| GET | `/api/cache-status` | None | Redis + DB cache health |
| POST | `/api/refresh-cache` | None | Trigger full job scrape |
| POST | `/api/refresh-cache-incremental` | None | Incremental scrape |
| GET | `/api/database-stats` | None | DB statistics |

---

## AI & Matching Pipeline

### Main flow (`/api/match-stream`)

1. **Parse resume** — pdfplumber or pytesseract OCR
2. **Extract skills** — Claude Haiku 4.5
3. **Fetch jobs** — Redis cache → DB → scrape fallback
4. **Extract job skills** — Claude Haiku 4.5 (cached per job hash, 3-tier)
5. **Metadata scoring** — weighted: 40% experience, 25% location, 20% industry, 15% citizenship
6. **Skill matching** — exact match + synonym normalization + difflib fuzzy fallback
7. **Deep ranking** — Claude Sonnet 4.5 re-ranks top 30 → top 10
8. **Stream results** — SSE events with `step`, `message`, `progress` fields

### Think Deeper mode

Enables Claude extended thinking for deeper resume-to-job reasoning. Rate-limited to **20 uses per user per week**.

### Resume tailoring

Claude Sonnet 4.5 rewrites your resume JSON for a target job, then `pdflatex` compiles LaTeX → PDF (auto-adjusts font sizes 11→8 to fit one page). Rate-limited to **5 tailors per user per week**.

### Job data source

GitHub: [`SimplifyJobs/Summer2026-Internships`](https://github.com/SimplifyJobs/Summer2026-Internships) — parsed via BeautifulSoup. Scrapes run on startup and refresh every 24h in the background.

---

## Authentication

- **Frontend:** Clerk (`useAuth()`) — `getToken()` fetches a short-lived JWT sent as `Authorization: Bearer <token>`
- **Backend:** `auth.py` — `require_user` FastAPI dependency verifies Clerk JWT via JWKS (RS256), returns `user_id` from `sub` claim
- Protected endpoints: `/api/match-stream`, `/api/tailor-resume`, `/api/user-history`, `/api/resume-cache/{hash}`, `/api/usage`

---

## Database

Models defined in `job_database.py`, auto-created via `Base.metadata.create_all()` (no Alembic).

| Table | Purpose |
|-------|---------|
| `jobs` | Internship listings, deduplicated by SHA-256 of `(company+title+location+domain)` |
| `cache_metadata` | Scrape operation logs and per-job skill cache entries |
| `resume_cache` | Matching results per user, keyed by `(user_id, resume_hash)`, 30-day TTL |
| `tailor_request_log` | Resume tailor usage tracking for weekly quota enforcement |
| `think_deeper_request_log` | Think Deeper usage tracking for weekly quota enforcement |

**Supabase project:** `gninorapexsxsfbtyajl` — quota tables have Row Level Security enabled.

---

## Caching

| Tier | Store | TTL | Key |
|------|-------|-----|-----|
| 1 | Redis | 4 hours | `internship_jobs_cache` |
| 2 | SQLite / PostgreSQL | persistent | `jobs` table |
| 3 | In-memory dict | process lifetime | content hash |

---

## Deployment

**Railway (primary):**
- Dockerfile-based, single container — Python backend serves React build
- `railway.toml` configures build and start commands
- `frontend/build/` committed and served by FastAPI static mount

```bash
# Production build
pip install -r requirements.txt
cd frontend && npm install && npm run build
uvicorn app:app --host 0.0.0.0 --port $PORT
```

**Docker Compose:**
```bash
docker-compose up
```
Runs: Redis + FastAPI backend + Nginx frontend (3 services).
