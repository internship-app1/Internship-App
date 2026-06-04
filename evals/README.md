# Resume-Parsing Prompt Eval Harness

Measures whether a prompt edit to `RESUME_ANALYSIS_SYSTEM_PROMPT` (in
`resume_parser/parse_resume.py`) improves or regresses extraction quality,
using a **frozen baseline + pairwise LLM judge**.

## Quick Start

```bash
# Make sure you're in the repo root and your venv is active
export CLAUDE_API_KEY=sk-ant-...

# Run all 10 cases
python -m evals.run

# Run a single case (fast sanity check)
python -m evals.run --cases negative_context

# Run a subset
python -m evals.run --cases negative_context nonstandard_names cs_student_cv

# Force re-extraction (ignore cache)
python -m evals.run --no-cache

# Force re-judge too
python -m evals.run --no-cache --no-judge-cache
```

Reports are written to `evals/results/report-<timestamp>.md`.

---

## How It Works

```
For each case:
  1. Structural gate (free)   — extract JSON, check schema, fail fast if malformed
  2. A/B extraction           — run real Haiku calls with baseline + candidate prompts
                                (temperature=0, results cached by prompt hash)
  3. Pairwise judge (Sonnet)  — grades both extractions, randomized A/B order
                                returns: winner + per-dimension scores 1–5
  4. Un-shuffle               — map A/B back to baseline/candidate
```

**Caching:** Extractions are cached in `evals/results/cache/` keyed by
`(case_id, prompt_hash)`. Unchanged prompts cost $0 to re-run. Use `--no-cache`
to force a fresh extraction after tweaking a prompt.

**Cost per full run:** ~30 API calls (10 cases × 2 extractions + 10 judge calls).
~$0.05–$0.15 depending on resume length.

---

## Cases

| Case | Tests |
|------|-------|
| `cs_student_cv` | Project classification (CV/ML), impact extraction, student level |
| `negative_context` | Skills in "I've never used X" / "want to learn X" must be excluded |
| `nonstandard_names` | JS→JavaScript, ML→Machine Learning, Py→Python standardization |
| `deployed_metrics` | Concrete metrics (users, latency, prize $) → impact_highlights |
| `vague_claims` | "Made it faster" with no number → empty impact_highlights |
| `experienced_backend` | experience_level=experienced, 10–14 conservative strong skills |
| `frontend_only` | Static sites → "Frontend Only" not "Full-Stack Web App" |
| `embedded_robotics` | ROS/Arduino projects → "Embedded Systems / IoT / Robotics" |
| `kitchen_sink_20_skills` | Self-reported 50 technologies, 0 projects → ≤5 skills |
| `sparse_resume` | Near-zero experience → short skills, no hallucination |

---

## Interpreting the Report

- **✅ Candidate wins** — the prompt edit improved this case
- **🚩 Baseline wins (REGRESSION)** — the edit made this case worse; investigate
- **↔ Tie** — no meaningful difference
- **⛔ Gate failure** — one of the extractions produced invalid/malformed JSON

The exit code is `0` if no regressions, `1` if any regressions. This makes
it CI-compatible for future gating.

---

## Promote a Winning Candidate

When the candidate prompt wins consistently across a full run, promote it:

```bash
# 1. Copy the candidate prompt text into baseline.py
python - <<'EOF'
import sys
sys.path.insert(0, '.')
from resume_parser.parse_resume import RESUME_ANALYSIS_SYSTEM_PROMPT
with open('evals/prompts/baseline.py', 'w') as f:
    f.write('BASELINE_PROMPT = """\n')
    f.write(RESUME_ANALYSIS_SYSTEM_PROMPT)
    f.write('"""\n')
print("baseline.py updated")
EOF

# 2. Commit baseline.py alongside parse_resume.py
git add evals/prompts/baseline.py resume_parser/parse_resume.py
git commit -m "chore: promote candidate prompt to baseline"
```

---

## Adding New Cases

1. Add a `resumes/<name>.txt` file with the resume text.
2. Add an entry to `datasets/cases.json`:

```json
{
  "id": "my_new_case",
  "resume_file": "my_new_case.txt",
  "description": "One-line description of what this case tests",
  "expectations": "Plain English: what correct extraction should produce for this resume.",
  "rules_under_test": ["rule1", "rule2"]
}
```

3. Run: `python -m evals.run --cases my_new_case`

---

## Files

```
evals/
├── README.md            — this file
├── __init__.py
├── extract.py           — calls extract_skills_with_llm_full with injected prompt
├── judge.py             — pairwise Sonnet judge
├── run.py               — orchestrator + report builder
├── prompts/
│   └── baseline.py      — FROZEN baseline prompt (update on promotion only)
├── datasets/
│   ├── cases.json       — eval case descriptors + expectations
│   └── resumes/         — 10 resume text files (one per case)
└── results/             — gitignored: cache/ + report-*.md files
```
