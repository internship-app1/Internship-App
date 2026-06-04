"""
FROZEN baseline — DO NOT EDIT while running an eval round.

Snapshot of matching.matcher.RESUME_PROFILE_SYSTEM_PROMPT as of the eval harness
initial commit. Candidate prompts are loaded live from the production module;
this file exists only to give the judge a stable reference point.
"""

RESUME_PROFILE_BASELINE_PROMPT = (
    "Extract the candidate's skills and experience level from the resume. "
    "Return ONLY valid JSON: "
    '{"skills": ["skill1", "skill2"], "experience_level": "student|entry_level|experienced", "years_of_experience": 0}'
)
