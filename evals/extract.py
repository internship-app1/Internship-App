"""
Thin wrappers around production extraction functions that inject an arbitrary
system prompt and force temperature=0 for deterministic eval runs.
"""
import os
import sys

# Ensure the repo root is on the path so we can import production modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from resume_parser.parse_resume import extract_skills_with_llm_full  # noqa: E402
from matching.matcher import (  # noqa: E402
    _extract_resume_profile_haiku,
    _score_jobs_with_prompt,
)
from resume_tailor.tailor_resume import tailor_resume_to_json  # noqa: E402


def extract_with_prompt(resume_text: str, system_prompt: str) -> dict:
    """
    Run resume parsing extraction with a specific system prompt at temperature=0.

    Returns the raw dict from extract_skills_with_llm_full.
    Propagates exceptions — the caller (run.py) handles failures as gate errors.
    """
    return extract_skills_with_llm_full(
        resume_text,
        system_prompt=system_prompt,
        temperature=0,
    )


def extract_resume_profile_with_prompt(resume_text: str, system_prompt: str) -> dict:
    """
    Run Haiku resume-profile extraction with a specific system prompt at temperature=0.
    """
    return _extract_resume_profile_haiku(
        resume_text,
        system_prompt=system_prompt,
        temperature=0,
    )


def extract_job_matches_with_prompt(resume_text: str, jobs_xml: str, system_prompt: str) -> dict:
    """
    Run Sonnet-only job scoring with a specific system prompt at temperature=0.

    Bypasses the Haiku pre-filter step so only the scoring system prompt is tested.
    Returns the raw parsed JSON dict (with a 'job_scores' key).
    """
    return _score_jobs_with_prompt(
        resume_text,
        jobs_xml,
        system_prompt=system_prompt,
        temperature=0,
    )


def extract_tailoring_with_prompt(
    resume_text: str,
    job_title: str,
    company: str,
    job_description: str,
    system_prompt: str,
) -> dict:
    """
    Run resume tailoring with a specific system prompt at temperature=0.
    """
    return tailor_resume_to_json(
        resume_text,
        job_title,
        company,
        job_description,
        system_prompt=system_prompt,
        temperature=0,
    )


def extract_with_context(context: str, case_assets: dict, system_prompt: str):
    """
    Dispatch to the right production extraction function based on eval context.

    Args:
        context: one of resume_parsing | resume_profile | job_matching | tailoring
        case_assets: dict of pre-loaded inputs for this case (keys depend on context)
        system_prompt: the prompt variant to inject (baseline or candidate)

    Returns:
        Raw extraction dict from the appropriate production function.
    """
    if context == "resume_parsing":
        return extract_with_prompt(case_assets["resume_text"], system_prompt)
    elif context == "resume_profile":
        return extract_resume_profile_with_prompt(case_assets["resume_text"], system_prompt)
    elif context == "job_matching":
        return extract_job_matches_with_prompt(
            case_assets["resume_text"],
            case_assets["jobs_xml"],
            system_prompt,
        )
    elif context == "tailoring":
        return extract_tailoring_with_prompt(
            case_assets["resume_text"],
            case_assets["job_title"],
            case_assets["company"],
            case_assets["job_description"],
            system_prompt,
        )
    else:
        raise ValueError(f"Unknown eval context: {context!r}")
