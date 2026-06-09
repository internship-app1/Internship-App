"""
Closed-loop widow elimination eval harness.

This is an EVAL, not a mock unit test: it really compiles LaTeX (pdflatex) and
really measures the rendered PDF (pdftotext). The two API-touching seams of the
pipeline — producing the tailored JSON and rewriting a widowed bullet — are
dependency-injected, so the harness runs with ZERO Anthropic spend:

  * tailored JSON  → supplied inline per fixture (hand-authored, the "model output")
  * rewrite_fn     → a hand-authored fix map + a deterministic trim-to-one-line
                     fallback (stands in for the Sonnet rewrite)

The machinery under test (inject → compile → max_full_line_len → measure_bullets
→ rewrite_widowed_bullets → recompile, with font locking) is exercised for real.

Acceptance (the deterministic GUARANTEE): after refinement, no wrapped bullet's
last line is below BACKSTOP_FLOOR * C (i.e. every bullet is either a single full
line or two near-full lines), and the PDF is a single page. The higher
WIDOW_THRESHOLD is the LLM's aspirational extend target; the floor is what the
free deterministic backstop guarantees even when the model does nothing. Every
bullet's ratio is printed so the run is auditable.

To run the REAL Haiku-backed path instead, pass rewrite_fn=_batch_widow_rewrite
and feed real tailor_resume_to_json output — the seams are unchanged.
"""
import shutil

import pytest

from resume_tailor.tailor_resume import (
    WIDOW_THRESHOLD,
    BACKSTOP_FLOOR,
    FONT_SIZES,
    inject_into_template,
    _compile_at_font,
    _count_pdf_pages,
    max_full_line_len,
    measure_bullets,
    _flatten_bullet_locations,
    refine_to_no_widows,
)

pytestmark = pytest.mark.skipif(
    not (shutil.which("pdflatex") and shutil.which("pdftotext")),
    reason="requires pdflatex and pdftotext on PATH",
)


# ---------------------------------------------------------------------------
# Injectable no-API rewrite seam
# ---------------------------------------------------------------------------

def _make_rewrite_fn(fix_map):
    """Return a BATCH rewrite_fn(items, cap, resume_text) -> {index: new_text}.

    Mirrors the production seam: one call fixes every widow. Uses a hand-authored
    fix when available, else deterministically trims the bullet to a single line
    (which can never be a widow) — the no-API stand-in for the model's "tighten to
    one line" branch.
    """
    def _trim_one_line(bullet, cap):
        target = max(20, cap - 4)
        if len(bullet) <= target:
            return bullet
        out = ""
        for w in bullet.split():
            if len(out) + len(w) + 1 > target:
                break
            out = (out + " " + w).strip()
        return out or bullet[:target]

    def fn(items, cap, resume_text):
        return {
            idx: (fix_map[bullet] if bullet in fix_map else _trim_one_line(bullet, cap))
            for idx, bullet, _fill in items
        }
    return fn


def _ratios(pdf, cap):
    """(ratio, below_floor) per bullet, ratio = last_line/cap (0 for single-line).

    `below_floor` marks the GUARANTEE violation: a wrapped last line under the
    deterministic BACKSTOP_FLOOR. (Ratios between the floor and WIDOW_THRESHOLD are
    acceptable "mostly full" two-liners.)
    """
    out = []
    for (l1, l2) in measure_bullets(pdf):
        r = (l2 / cap) if (l2 and cap) else 0.0
        out.append((r, bool(l2) and r < BACKSTOP_FLOOR))
    return out


# ---------------------------------------------------------------------------
# Fixtures: (name, resume_text, job_title, company, job_description,
#            tailored_data, fix_map)
# ---------------------------------------------------------------------------

_CONTACT = {
    "email": "alex.rivera@example.com", "phone": "555-201-3344",
    "website": "https://alexrivera.dev", "github": "https://github.com/arivera",
    "linkedin": "https://linkedin.com/in/arivera",
}

# Fixture A — fits at 11pt; two deliberate dead-zone widows.
# Resume text is the grounding source for the hand-authored extend/shrink fixes.
A_RESUME = """Alex Rivera — alex.rivera@example.com — github.com/arivera
EXPERIENCE
Northwind Labs, Remote — Backend Intern (May 2024 - Aug 2024)
- Built a FastAPI service exposing 12 REST endpoints; added Redis caching that cut p95 latency 38% (210ms to 130ms) and shipped it to 3 staging environments.
- Wrote a Python abstraction wrapper around Grafanalib on a 3-person team, achieving 83% code reduction (30+ lines to 5 per dashboard), validated across 3 Grafana production environments.
- Added pytest coverage from 41% to 88% across the orders module.
PROJECTS
ReviewHub (TypeScript, React, Node.js, PostgreSQL) — Jan 2024
- Building a full-stack professor review platform for 30,000+ SJSU students using TypeScript, React, Node.js, Drizzle ORM, and PostgreSQL; shipped the review submission flow and a Python GraphQL webscraper for automated course-data ingestion.
- Designed the PostgreSQL schema with 9 tables.
"""

A_DATA = {
    "name": "Alex Rivera", **_CONTACT,
    "experience": [
        {"company": "Northwind Labs", "location": "Remote",
         "title": "Backend Intern", "dates": "May 2024 - Aug 2024",
         "bullets": [
             # WIDOW (dead zone ~154 chars): wraps to a short orphan line.
             "Built Python abstraction wrapper around Grafanalib on 3-person engineering team, achieving 83% code reduction (30+ lines to 5) for dashboard configuration",
             "Raised pytest coverage from 41% to 88% across the orders module.",
             # WIDOW (dead zone ~145 chars): another orphan.
             "Built a FastAPI service exposing 12 REST endpoints with Redis caching that cut p95 latency by 38 percent from 210ms down to about 130ms in staging",
         ]},
    ],
    "education": [
        {"school": "San Jose State University", "location": "San Jose, CA",
         "degree": "B.S. Computer Science", "dates": "2022 - 2026"},
    ],
    "skills": {
        "Languages": "Python, TypeScript, SQL",
        "Frameworks": "FastAPI, React, Node.js",
        "Tools": "Redis, PostgreSQL, Docker, Git",
    },
    "projects": [
        {"name": "ReviewHub (TypeScript, React, Node.js, PostgreSQL)", "dates": "Jan 2024",
         "bullets": [
             "Designed the PostgreSQL schema with 9 normalized tables.",
         ]},
    ],
}

# Hand-authored fixes (grounded in A_RESUME): one EXTEND to a full two lines,
# one TIGHTEN to a single line.
A_FIX = {
    # EXTEND to two near-full lines (~191 chars → second line ~79% full) using
    # real resume facts (validated across 3 Grafana production environments).
    "Built Python abstraction wrapper around Grafanalib on 3-person engineering team, achieving 83% code reduction (30+ lines to 5) for dashboard configuration":
        "Built a Python abstraction wrapper around Grafanalib on a 3-person team, achieving 83% code reduction (30+ lines to 5 per dashboard) and validating it across 3 Grafana production environments",
    # TIGHTEN to a single tight line (<= C) by cutting the trailing clause.
    "Built a FastAPI service exposing 12 REST endpoints with Redis caching that cut p95 latency by 38 percent from 210ms down to about 130ms in staging":
        "Built FastAPI service (12 REST endpoints) with Redis caching, cutting p95 latency 38% (210ms to 130ms)",
}

# Fixture B — dense resume that overflows 11pt and forces a smaller font; the
# trim-to-one-line fallback resolves every widow at whatever font is locked.
def _dense_data():
    long_widow = (
        "Implemented a distributed job queue in Python with retry and backoff that processed "
        "over 5,000 tasks per day across 4 worker nodes for the platform"
    )  # dead-zone length -> widow
    exp = []
    for n in range(4):
        exp.append({
            "company": f"Company {n}", "location": "Remote",
            "title": "Software Engineer Intern", "dates": "2023 - 2024",
            "bullets": [
                long_widow,
                "Shipped a React dashboard with 18 components and 95% Lighthouse score.",
                "Cut CI time 46% (22m to 12m) by parallelizing the pytest suite and caching deps.",
                "Migrated 7 services from REST to gRPC, reducing payload size 60% on average.",
                "Authored 30+ runbooks and onboarded 5 new engineers to the on-call rotation.",
            ],
        })
    return {
        "name": "Dana Cruz", **_CONTACT,
        "experience": exp,
        "education": [
            {"school": "State University", "location": "Austin, TX",
             "degree": "B.S. Computer Science", "dates": "2021 - 2025"},
        ],
        "skills": {
            "Languages": "Python, Go, TypeScript, SQL",
            "Frameworks": "FastAPI, React, gRPC",
            "Tools": "Docker, Kubernetes, Redis, PostgreSQL, Git",
        },
        "projects": [
            {"name": "PipelineKit (Python, Kubernetes)", "dates": "2024",
             "bullets": [
                 "Built a Kubernetes operator in Go that auto-scales workers based on queue depth.",
                 "Designed a Postgres-backed metadata store with tag-based cache invalidation.",
             ]},
        ],
    }

B_RESUME = "Dana Cruz — dense backend resume; see bullets. Grounding source for trims."

FIXTURES = [
    ("A_fits_11pt", A_RESUME, "Backend Engineer Intern", "Acme", "Python, FastAPI, Redis, PostgreSQL backend role.", A_DATA, A_FIX),
    ("B_dense_subfont", B_RESUME, "Platform Engineer Intern", "Globex", "Distributed systems, Kubernetes, Go, Python.", _dense_data(), {}),
]


@pytest.mark.parametrize("name,resume,title,company,jd,data,fix_map", FIXTURES)
def test_no_widows_after_refine(name, resume, title, company, jd, data, fix_map, capsys):
    # ----- BEFORE: compile the raw tailored data at its first fitting font -----
    latex = inject_into_template(data)
    before_pdf, before_font = None, FONT_SIZES[-1]
    for size in FONT_SIZES:
        cand = _compile_at_font(latex, size)
        if _count_pdf_pages(cand) <= 1:
            before_pdf, before_font = cand, size
            break
    if before_pdf is None:
        before_pdf = cand
    before_cap = max_full_line_len(before_pdf)
    before = _ratios(before_pdf, before_cap)

    # ----- REFINE (closed loop, no API) -----
    rewrite_fn = _make_rewrite_fn(fix_map)
    final_pdf = refine_to_no_widows(data, resume, rewrite_fn=rewrite_fn, max_rounds=3)

    final_cap = max_full_line_len(final_pdf)
    final_pairs = measure_bullets(final_pdf)
    after = _ratios(final_pdf, final_cap)
    pages = _count_pdf_pages(final_pdf)

    # ----- AUDIT OUTPUT -----
    print(f"\n=== Fixture {name} ===")
    def _label(r, below):
        if below:
            return "BELOW-FLOOR"
        if not r:
            return "1line"
        return "2line-full" if r >= WIDOW_THRESHOLD else "2line-ok"

    print(f"BEFORE: font={before_font} C={before_cap} below_floor={sum(1 for _,b in before if b)}/{len(before)}")
    for i, (r, b) in enumerate(before):
        print(f"  before[{i}] ratio={r:.2f} {_label(r, b)}")
    print(f"AFTER:  C={final_cap} pages={pages} bullets={len(final_pairs)} (floor={BACKSTOP_FLOOR}, target={WIDOW_THRESHOLD})")
    for i, (r, b) in enumerate(after):
        print(f"  after [{i}] ratio={r:.2f} {_label(r, b)}")

    # ----- ASSERTIONS (the deterministic guarantee) -----
    assert pages == 1, f"{name}: expected 1 page, got {pages}"
    below = [i for i, (_, b) in enumerate(after) if b]
    assert not below, f"{name}: orphans below floor remain at bullets {below}: {after}"


@pytest.mark.parametrize("name,resume,title,company,jd,data,fix_map", FIXTURES)
def test_backstop_guarantees_when_llm_gives_up(name, resume, title, company, jd, data, fix_map):
    """Even if the model returns NO rewrites, the free deterministic backstop must
    still guarantee every bullet is at/above the floor and the PDF stays one page."""
    llm_gives_up = lambda items, cap, resume_text: {}  # noqa: E731 — model contributes nothing

    final_pdf = refine_to_no_widows(data, resume, rewrite_fn=llm_gives_up, max_rounds=3)

    cap = max_full_line_len(final_pdf)
    pages = _count_pdf_pages(final_pdf)
    after = _ratios(final_pdf, cap)
    below = [i for i, (_, b) in enumerate(after) if b]
    print(f"\n[{name}] LLM-gives-up: pages={pages} below_floor={len(below)}/{len(after)} "
          f"ratios={[round(r, 2) for r, _ in after]}")
    assert pages == 1, f"{name}: expected 1 page, got {pages}"
    assert not below, f"{name}: backstop failed — orphans below floor at {below}"
