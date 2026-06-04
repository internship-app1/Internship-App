#!/usr/bin/env python3
"""
Eval runner: A/B baseline diff + pairwise LLM judge for prompt changes.

Usage:
    python -m evals.run                                      # resume_parsing, all cases
    python -m evals.run --context resume_profile             # profile extraction context
    python -m evals.run --context job_matching               # job scoring context
    python -m evals.run --context tailoring                  # resume tailoring context
    python -m evals.run --cases cs_student_cv negative_context  # run subset of cases
    python -m evals.run --no-cache                           # force re-extraction
    python -m evals.run --no-judge-cache                     # force re-judge too

Requires:
    CLAUDE_API_KEY environment variable set to a real Anthropic key.

Output:
    evals/results/report-<timestamp>.md   (Markdown report, human-readable)
    evals/results/cache/                  (raw JSON per extraction, keyed by prompt hash)

Exit codes:
    0 — candidate won or tied every case
    1 — one or more regressions (candidate lost at least one case)
"""
import argparse
import hashlib
import json
import os
import random
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Ensure repo root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.extract import extract_with_context  # noqa: E402
from evals.judge import pairwise_judge  # noqa: E402

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EVALS_DIR = Path(__file__).parent
DATASETS_DIR = EVALS_DIR / "datasets"
RESULTS_DIR = EVALS_DIR / "results"
CACHE_DIR = RESULTS_DIR / "cache"

RESULTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Structural gates (per context)
# ---------------------------------------------------------------------------

VALID_EXPERIENCE_LEVELS = {"student", "recent_graduate", "entry_level", "experienced"}


def structural_gate_resume_parsing(extraction, label):
    """Gate for resume_parsing context — same as original."""
    issues = []
    if not isinstance(extraction, dict):
        return False, [f"{label}: extraction is not a dict"]

    if "skills" not in extraction:
        issues.append(f"{label}: missing 'skills' key")
    elif not isinstance(extraction["skills"], list):
        issues.append(f"{label}: 'skills' is not a list")

    if "experience_level" not in extraction:
        issues.append(f"{label}: missing 'experience_level' key")
    elif extraction["experience_level"] not in VALID_EXPERIENCE_LEVELS:
        issues.append(
            f"{label}: invalid experience_level={extraction['experience_level']!r}"
            f" (expected one of {sorted(VALID_EXPERIENCE_LEVELS)})"
        )

    if "years_of_experience" not in extraction:
        issues.append(f"{label}: missing 'years_of_experience' key")
    elif not isinstance(extraction["years_of_experience"], (int, float)):
        issues.append(f"{label}: 'years_of_experience' is not a number")

    return len(issues) == 0, issues


def structural_gate_resume_profile(extraction, label):
    """Gate for resume_profile context."""
    issues = []
    if not isinstance(extraction, dict):
        return False, [f"{label}: extraction is not a dict"]

    if "skills" not in extraction:
        issues.append(f"{label}: missing 'skills' key")
    elif not isinstance(extraction["skills"], list):
        issues.append(f"{label}: 'skills' is not a list")

    valid_levels = {"student", "entry_level", "experienced", "recent_graduate"}
    if "experience_level" not in extraction:
        issues.append(f"{label}: missing 'experience_level' key")
    elif extraction["experience_level"] not in valid_levels:
        issues.append(
            f"{label}: invalid experience_level={extraction['experience_level']!r}"
            f" (expected one of {sorted(valid_levels)})"
        )

    if "years_of_experience" not in extraction:
        issues.append(f"{label}: missing 'years_of_experience' key")
    elif not isinstance(extraction["years_of_experience"], (int, float)):
        issues.append(f"{label}: 'years_of_experience' is not a number")

    return len(issues) == 0, issues


def structural_gate_job_matching(extraction, label):
    """Gate for job_matching context."""
    issues = []
    if not isinstance(extraction, dict):
        return False, [f"{label}: extraction is not a dict"]

    if "job_scores" not in extraction:
        issues.append(f"{label}: missing 'job_scores' key")
        return False, issues

    if not isinstance(extraction["job_scores"], list):
        issues.append(f"{label}: 'job_scores' is not a list")
        return False, issues

    for i, entry in enumerate(extraction["job_scores"]):
        if not isinstance(entry, dict):
            issues.append(f"{label}: job_scores[{i}] is not a dict")
            continue
        if "job_id" not in entry or not isinstance(entry["job_id"], (int, float)):
            issues.append(f"{label}: job_scores[{i}] missing or invalid 'job_id' (must be number)")
        if "match_score" not in entry or not isinstance(entry["match_score"], (int, float)):
            issues.append(f"{label}: job_scores[{i}] missing or invalid 'match_score' (must be 0-100 number)")
        elif not (0 <= entry["match_score"] <= 100):
            issues.append(f"{label}: job_scores[{i}] match_score={entry['match_score']} out of range [0,100]")
        if "reasoning" not in entry or not isinstance(entry["reasoning"], str):
            issues.append(f"{label}: job_scores[{i}] missing or invalid 'reasoning' (must be string)")
        if "skill_matches" not in entry or not isinstance(entry["skill_matches"], list):
            issues.append(f"{label}: job_scores[{i}] missing or invalid 'skill_matches' (must be list)")
        if "skill_gaps" not in entry or not isinstance(entry["skill_gaps"], list):
            issues.append(f"{label}: job_scores[{i}] missing or invalid 'skill_gaps' (must be list)")

    return len(issues) == 0, issues


def structural_gate_tailoring(extraction, label):
    """Gate for tailoring context."""
    issues = []
    if not isinstance(extraction, dict):
        return False, [f"{label}: extraction is not a dict"]

    if "name" not in extraction or not isinstance(extraction["name"], str):
        issues.append(f"{label}: missing or invalid 'name' (must be string)")
    if "experience" not in extraction or not isinstance(extraction["experience"], list):
        issues.append(f"{label}: missing or invalid 'experience' (must be list)")
    if "education" not in extraction or not isinstance(extraction["education"], list):
        issues.append(f"{label}: missing or invalid 'education' (must be list)")
    if "skills" not in extraction or not isinstance(extraction["skills"], (dict, list)):
        issues.append(f"{label}: missing or invalid 'skills' (must be dict or list)")
    if "projects" not in extraction or not isinstance(extraction["projects"], list):
        issues.append(f"{label}: missing or invalid 'projects' (must be list)")

    return len(issues) == 0, issues


# ---------------------------------------------------------------------------
# Asset loaders (per context)
# ---------------------------------------------------------------------------

def _load_resume_text(case, datasets_dir):
    path = datasets_dir / "resumes" / case["resume_file"]
    with open(path) as f:
        return f.read()


def asset_loader_resume_parsing(case, datasets_dir):
    return {"resume_text": _load_resume_text(case, datasets_dir)}


def asset_loader_resume_profile(case, datasets_dir):
    return {"resume_text": _load_resume_text(case, datasets_dir)}


def asset_loader_job_matching(case, datasets_dir):
    resume_text = case.get("resume_text", "")
    if not resume_text and "resume_file" in case:
        resume_text = _load_resume_text(case, datasets_dir)
    slate_path = datasets_dir / "job_matching" / "slates" / case["slate_file"]
    with open(slate_path) as f:
        jobs_xml = f.read()
    return {"resume_text": resume_text, "jobs_xml": jobs_xml}


def asset_loader_tailoring(case, datasets_dir):
    resume_text = _load_resume_text(case, datasets_dir)
    return {
        "resume_text": resume_text,
        "job_title": case["job_title"],
        "company": case["company"],
        "job_description": case["job_description"],
    }


# ---------------------------------------------------------------------------
# Context registry
# ---------------------------------------------------------------------------

def _build_registry():
    return {
        "resume_parsing": {
            "baseline_loader": lambda: _import("evals.prompts.baseline", "BASELINE_PROMPT"),
            "candidate_loader": lambda: _import("resume_parser.parse_resume", "RESUME_ANALYSIS_SYSTEM_PROMPT"),
            "cases_path": DATASETS_DIR / "cases.json",
            "structural_gate": structural_gate_resume_parsing,
            "dimensions": ["skill_accuracy", "conservatism", "project_classification", "impact_quality"],
            "asset_loader": asset_loader_resume_parsing,
        },
        "resume_profile": {
            "baseline_loader": lambda: _import("evals.prompts.resume_profile_baseline", "RESUME_PROFILE_BASELINE_PROMPT"),
            "candidate_loader": lambda: _import("matching.matcher", "RESUME_PROFILE_SYSTEM_PROMPT"),
            "cases_path": DATASETS_DIR / "resume_profile" / "cases.json",
            "structural_gate": structural_gate_resume_profile,
            "dimensions": ["skill_accuracy", "conservatism", "experience_level_accuracy"],
            "asset_loader": asset_loader_resume_profile,
        },
        "job_matching": {
            "baseline_loader": lambda: _import("evals.prompts.job_matching_baseline", "JOB_MATCH_BASELINE_PROMPT"),
            "candidate_loader": lambda: _import("matching.matcher", "JOB_MATCH_SYSTEM_PROMPT"),
            "cases_path": DATASETS_DIR / "job_matching" / "cases.json",
            "structural_gate": structural_gate_job_matching,
            "dimensions": ["ranking_accuracy", "reasoning_quality", "skill_gap_accuracy"],
            "asset_loader": asset_loader_job_matching,
        },
        "tailoring": {
            "baseline_loader": lambda: _import("evals.prompts.tailoring_baseline", "TAILOR_BASELINE_PROMPT"),
            "candidate_loader": lambda: _import("resume_tailor.tailor_resume", "TAILOR_SYSTEM_PROMPT"),
            "cases_path": DATASETS_DIR / "tailoring" / "cases.json",
            "structural_gate": structural_gate_tailoring,
            "dimensions": ["keyword_alignment", "truthfulness", "specificity", "concision"],
            "asset_loader": asset_loader_tailoring,
        },
    }


def _import(module_path, attr):
    """Dynamically import a named attribute from a dotted module path."""
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, attr)


# ---------------------------------------------------------------------------
# Dataset helpers
# ---------------------------------------------------------------------------

def load_cases(cases_path, case_ids=None):
    with open(cases_path) as f:
        cases = json.load(f)
    if case_ids:
        cases = [c for c in cases if c["id"] in case_ids]
        missing = set(case_ids) - {c["id"] for c in cases}
        if missing:
            print(f"[warn] Unknown case IDs: {sorted(missing)}", flush=True)
    return cases


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def prompt_hash(prompt_str):
    return hashlib.md5(prompt_str.encode()).hexdigest()[:12]


def extraction_cache_key(context, case_id, p_hash):
    return f"extract__{context}__{case_id}__{p_hash}"


def judge_cache_key(case_id, hash_a, hash_b):
    return f"judge__{case_id}__{hash_a}__{hash_b}"


def cache_load(key):
    path = CACHE_DIR / f"{key}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def cache_save(key, data):
    path = CACHE_DIR / f"{key}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# JSON diff helper
# ---------------------------------------------------------------------------

def json_diff_lines(label_a, obj_a, label_b, obj_b, indent=2):
    lines = []
    lines.append(f"**{label_a}:**")
    lines.append("```json")
    lines.append(json.dumps(obj_a, indent=indent))
    lines.append("```")
    lines.append(f"**{label_b}:**")
    lines.append("```json")
    lines.append(json.dumps(obj_b, indent=indent))
    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Score aggregation
# ---------------------------------------------------------------------------

def mean_delta(results, dimensions):
    """Per-dimension mean (candidate - baseline) across cases that were judged."""
    judged = [r for r in results if r.get("judged") and not r.get("gate_failed")]
    if not judged:
        return {d: 0.0 for d in dimensions}
    deltas = {d: [] for d in dimensions}
    for r in judged:
        for d in dimensions:
            cand_score = r["judge"]["scores_candidate"].get(d, 3)
            base_score = r["judge"]["scores_baseline"].get(d, 3)
            deltas[d].append(cand_score - base_score)
    return {d: round(sum(v) / len(v), 2) for d, v in deltas.items()}


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(run_id, context, results, b_hash, c_hash, dimensions):
    judged = [r for r in results if r.get("judged") and not r.get("gate_failed")]
    gate_failures = [r for r in results if r.get("gate_failed")]

    wins = sum(1 for r in judged if r["judge"]["winner"] == "candidate")
    losses = sum(1 for r in judged if r["judge"]["winner"] == "baseline")
    ties = sum(1 for r in judged if r["judge"]["winner"] == "tie")
    regressions = [r for r in judged if r["judge"]["winner"] == "baseline"]
    deltas = mean_delta(results, dimensions)

    lines = []
    lines.append(f"# Eval Report — {run_id}  (context: {context})")
    lines.append("")
    lines.append(f"**Baseline prompt hash:** `{b_hash}`  ")
    lines.append(f"**Candidate prompt hash:** `{c_hash}`  ")
    lines.append(f"**Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  ")
    lines.append(f"**Cases:** {len(results)} total, {len(judged)} judged")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    verdict_emoji = "✅" if losses == 0 else "🚩"
    lines.append(
        f"{verdict_emoji} Candidate **wins {wins}**, ties {ties}, loses {losses}"
        + (f" — **{losses} REGRESSION(S)**" if losses else "")
    )
    lines.append("")
    lines.append("### Per-dimension mean delta (candidate − baseline)")
    lines.append("")
    lines.append("| Dimension | Δ mean |")
    lines.append("|-----------|--------|")
    for d, delta in deltas.items():
        arrow = "⬆" if delta > 0.1 else ("⬇" if delta < -0.1 else "↔")
        lines.append(f"| {d} | {arrow} {delta:+.2f} |")
    lines.append("")

    if gate_failures:
        lines.append("## ⛔ Gate Failures (structural check failed)")
        lines.append("")
        for r in gate_failures:
            lines.append(f"### {r['id']}")
            lines.append("")
            for issue in r["gate_issues"]:
                lines.append(f"- {issue}")
            lines.append("")

    if regressions:
        lines.append("## 🚩 Regressions (candidate lost)")
        lines.append("")
        for r in regressions:
            j = r["judge"]
            lines.append(f"### {r['id']}")
            lines.append("")
            lines.append(f"> {r['description']}")
            lines.append("")
            lines.append(f"**Judge justification:** {j['justification']}")
            lines.append("")
            lines.append("| Dimension | Baseline | Candidate |")
            lines.append("|-----------|----------|-----------|")
            for d in dimensions:
                bs = j["scores_baseline"].get(d, "?")
                cs = j["scores_candidate"].get(d, "?")
                flag = " ⬇" if isinstance(bs, int) and isinstance(cs, int) and cs < bs else ""
                lines.append(f"| {d} | {bs} | {cs}{flag} |")
            lines.append("")

    lines.append("## Per-case Results")
    lines.append("")
    for r in results:
        case_id = r["id"]
        lines.append(f"### {case_id}")
        lines.append("")
        lines.append(f"> {r['description']}")
        lines.append("")

        if r.get("gate_failed"):
            lines.append("**Status: ⛔ GATE FAILURE**")
            lines.append("")
            for issue in r.get("gate_issues", []):
                lines.append(f"- {issue}")
            lines.append("")
            continue

        if not r.get("judged"):
            lines.append("**Status: ⚠ Not judged (error)**")
            lines.append(f"```\n{r.get('error', 'unknown error')}\n```")
            lines.append("")
            continue

        j = r["judge"]
        winner_label = {
            "candidate": "✅ Candidate wins",
            "baseline": "🚩 Baseline wins (REGRESSION)",
            "tie": "↔ Tie",
        }.get(j["winner"], j["winner"])
        lines.append(f"**Verdict: {winner_label}**")
        lines.append("")
        lines.append(f"*{j['justification']}*")
        lines.append("")
        lines.append("| Dimension | Baseline | Candidate |")
        lines.append("|-----------|----------|-----------|")
        for d in dimensions:
            bs = j["scores_baseline"].get(d, "?")
            cs = j["scores_candidate"].get(d, "?")
            flag = " ⬆" if isinstance(bs, int) and isinstance(cs, int) and cs > bs else (
                " ⬇" if isinstance(bs, int) and isinstance(cs, int) and cs < bs else ""
            )
            lines.append(f"| {d} | {bs} | {cs}{flag} |")
        lines.append("")

        lines.append("<details><summary>Extractions (click to expand)</summary>")
        lines.append("")
        lines.append(
            json_diff_lines("Baseline", r["baseline_output"], "Candidate", r["candidate_output"])
        )
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_evals(context="resume_parsing", case_ids=None, no_extract_cache=False, no_judge_cache=False):
    if not os.getenv("CLAUDE_API_KEY"):
        print("ERROR: CLAUDE_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    registry = _build_registry()
    if context not in registry:
        print(f"ERROR: unknown context {context!r}. Choices: {list(registry)}", file=sys.stderr)
        sys.exit(1)

    ctx = registry[context]
    dimensions = ctx["dimensions"]

    baseline_prompt = ctx["baseline_loader"]()
    candidate_prompt = ctx["candidate_loader"]()
    b_hash = prompt_hash(baseline_prompt)
    c_hash = prompt_hash(candidate_prompt)

    print(f"Context:        {context}", flush=True)
    print(f"Baseline hash:  {b_hash}", flush=True)
    print(f"Candidate hash: {c_hash}", flush=True)
    if b_hash == c_hash:
        print(
            "[warn] Baseline and candidate prompts are identical — "
            "expect all ties (sanity-check mode).",
            flush=True,
        )

    cases = load_cases(ctx["cases_path"], case_ids)
    print(f"Running {len(cases)} cases...\n", flush=True)

    results = []

    for case in cases:
        case_id = case["id"]
        print(f"[{case_id}] Starting...", end=" ", flush=True)
        result = {
            "id": case_id,
            "description": case.get("description", ""),
            "judged": False,
            "gate_failed": False,
        }

        # Load assets for this case
        try:
            case_assets = ctx["asset_loader"](case, DATASETS_DIR)
        except FileNotFoundError as e:
            result["gate_failed"] = True
            result["gate_issues"] = [f"asset file not found: {e}"]
            results.append(result)
            print("ERROR (missing asset file)", flush=True)
            continue

        # --- Extraction (with per-prompt, per-context cache) ---
        b_extract_key = extraction_cache_key(context, case_id, b_hash)
        c_extract_key = extraction_cache_key(context, case_id, c_hash)

        baseline_output = None if no_extract_cache else cache_load(b_extract_key)
        candidate_output = None if no_extract_cache else cache_load(c_extract_key)

        try:
            if baseline_output is None:
                baseline_output = extract_with_context(context, case_assets, baseline_prompt)
                cache_save(b_extract_key, baseline_output)

            if candidate_output is None:
                candidate_output = extract_with_context(context, case_assets, candidate_prompt)
                cache_save(c_extract_key, candidate_output)
        except Exception as e:
            result["gate_failed"] = True
            result["gate_issues"] = [f"extraction error: {e}"]
            result["error"] = traceback.format_exc()
            results.append(result)
            print(f"ERROR (extraction failed): {e}", flush=True)
            continue

        result["baseline_output"] = baseline_output
        result["candidate_output"] = candidate_output

        # --- Structural gate ---
        gate_fn = ctx["structural_gate"]
        b_ok, b_issues = gate_fn(baseline_output, "baseline")
        c_ok, c_issues = gate_fn(candidate_output, "candidate")
        gate_issues = b_issues + c_issues
        if gate_issues:
            result["gate_failed"] = True
            result["gate_issues"] = gate_issues
            results.append(result)
            print(f"GATE FAIL: {gate_issues}", flush=True)
            continue

        # --- Pairwise judge (randomize A/B order) ---
        j_key = judge_cache_key(case_id, b_hash, c_hash)
        judge_result = None if no_judge_cache else cache_load(j_key)

        if judge_result is None:
            flip = random.random() < 0.5
            output_a = candidate_output if flip else baseline_output
            output_b = baseline_output if flip else candidate_output
            label_a = "candidate" if flip else "baseline"
            label_b = "baseline" if flip else "candidate"

            try:
                raw_verdict = pairwise_judge(
                    resume_text=case_assets.get("resume_text", ""),
                    expectations=case.get("expectations", ""),
                    output_a=output_a,
                    output_b=output_b,
                    context=context,
                )
            except Exception as e:
                result["judged"] = False
                result["error"] = f"judge failed: {e}\n{traceback.format_exc()}"
                results.append(result)
                print(f"JUDGE ERROR: {e}", flush=True)
                continue

            if label_a == "candidate":
                scores_candidate = raw_verdict["scores_A"]
                scores_baseline = raw_verdict["scores_B"]
                raw_winner = raw_verdict["winner"]
                winner = "candidate" if raw_winner == "A" else (
                    "baseline" if raw_winner == "B" else "tie"
                )
            else:
                scores_baseline = raw_verdict["scores_A"]
                scores_candidate = raw_verdict["scores_B"]
                raw_winner = raw_verdict["winner"]
                winner = "baseline" if raw_winner == "A" else (
                    "candidate" if raw_winner == "B" else "tie"
                )

            judge_result = {
                "scores_baseline": scores_baseline,
                "scores_candidate": scores_candidate,
                "winner": winner,
                "justification": raw_verdict.get("justification", ""),
            }
            cache_save(j_key, judge_result)

        result["judge"] = judge_result
        result["judged"] = True

        winner_str = {
            "candidate": "✅ candidate",
            "baseline": "🚩 BASELINE (regression)",
            "tie": "↔ tie",
        }.get(judge_result["winner"], judge_result["winner"])
        print(f"{winner_str}", flush=True)

        results.append(result)

    # --- Report ---
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report = build_report(run_id, context, results, b_hash, c_hash, dimensions)
    report_path = RESULTS_DIR / f"report-{run_id}.md"
    report_path.write_text(report)

    raw_path = RESULTS_DIR / f"raw-{run_id}.json"
    raw_path.write_text(json.dumps(results, indent=2, default=str))

    print(f"\n{'=' * 60}", flush=True)
    judged = [r for r in results if r.get("judged")]
    wins = sum(1 for r in judged if r["judge"]["winner"] == "candidate")
    losses = sum(1 for r in judged if r["judge"]["winner"] == "baseline")
    ties = sum(1 for r in judged if r["judge"]["winner"] == "tie")
    gate_failures = sum(1 for r in results if r.get("gate_failed"))

    print(f"Results: {wins} wins / {ties} ties / {losses} regressions / {gate_failures} gate failures")
    print(f"Report:  {report_path}")

    if losses > 0 or gate_failures > 0:
        print(f"\n🚩 {losses} regression(s) detected. Check the report for details.")
        return 1
    else:
        print("\n✅ No regressions. Candidate is at least as good as baseline.")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Run prompt evals (baseline vs candidate A/B + LLM judge)."
    )
    parser.add_argument(
        "--context",
        default="resume_parsing",
        choices=["resume_parsing", "resume_profile", "job_matching", "tailoring"],
        help=(
            "Which prompt context to evaluate. "
            "Default: resume_parsing (backward-compatible with original behavior)."
        ),
    )
    parser.add_argument(
        "--cases",
        nargs="*",
        metavar="CASE_ID",
        help="Run only these case IDs (default: all). E.g. --cases cs_student_cv negative_context",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Re-run all extractions even if cached (judge results still cached unless --no-judge-cache).",
    )
    parser.add_argument(
        "--no-judge-cache",
        action="store_true",
        help="Re-run all judge calls even if cached.",
    )
    args = parser.parse_args()

    exit_code = run_evals(
        context=args.context,
        case_ids=args.cases,
        no_extract_cache=args.no_cache,
        no_judge_cache=args.no_judge_cache,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
