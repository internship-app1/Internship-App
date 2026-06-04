"""
Pairwise LLM judge for resume extraction evals.

Grades two extraction outputs (A vs B) head-to-head using Claude Sonnet.
The caller randomizes which is baseline and which is candidate to avoid
position bias; this module just grades what it receives.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import anthropic  # noqa: E402

JUDGE_MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Per-context judge system prompts and token budgets
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of resume-parsing AI outputs.

You will be given a resume text, expected behavior for this type of resume, and two
extraction outputs labeled A and B. Your job is to grade each output on four dimensions
and declare a winner.

SCORING DIMENSIONS (1–5 for each output):
- skill_accuracy (1–5): Skills listed are real and demonstrated in the resume.
    Penalize: skills from negative contexts ("I've never used X"), skills from job
    descriptions the candidate applied to, skills from future learning goals.
    Reward: correct standardized names (JavaScript not JS, Machine Learning not ML).
    1=many hallucinated/incorrect skills, 5=only accurate well-demonstrated skills.

- conservatism (1–5): The number of skills extracted is appropriate for the evidence.
    Penalize: bloating with 20+ self-reported skills when projects show only 3 real ones.
    Penalize: extracting too few when the candidate has rich demonstrated experience.
    Reward: 5–12 solid skills for a typical candidate.
    1=wildly over/under extracted, 5=well-calibrated to evidence.

- project_classification (1–5): Project types are correctly categorized.
    Use the taxonomy: AI/ML (Computer Vision), AI/ML (NLP/GenAI), AI/ML (Traditional/Analytics),
    Data Engineering / ETL, Full-Stack Web App, Frontend Only, Mobile App,
    System/Infrastructure, Cybersecurity / Blockchain, Game Development,
    Embedded Systems / IoT / Robotics, Developer Tool / Automation.
    If no projects are extracted at all by a given output, score that output 3 (neutral)
    — absence of classification is not wrong unless projects clearly exist in the resume.
    1=wrong categories, 5=all correctly classified.

- impact_quality (1–5): Impact highlights are concrete with real numeric metrics or
    deployment evidence. Penalize vague claims ("made it faster", "users liked it").
    Reward: specific numbers, deployment URLs, award amounts, latency reductions, user counts.
    If neither output extracts impact highlights (because the resume has none), both get 3.
    If the resume has real metrics and an output fails to capture them, penalize.
    1=full of vague claims or missing real metrics, 5=precise concrete highlights.

WINNER RULES:
- Declare "A" if A is clearly better overall (wins majority of dimensions or wins the most
  important ones for this resume type).
- Declare "B" if B is clearly better overall.
- Declare "tie" ONLY if the outputs are genuinely equivalent across all four dimensions
  (within 0-1 points on each). Do not default to tie — be decisive.

Return ONLY valid JSON. No markdown fences, no commentary outside the JSON:
{
  "scores_A": {
    "skill_accuracy": 3,
    "conservatism": 4,
    "project_classification": 3,
    "impact_quality": 3
  },
  "scores_B": {
    "skill_accuracy": 4,
    "conservatism": 3,
    "project_classification": 5,
    "impact_quality": 4
  },
  "winner": "B",
  "justification": "B correctly classifies the YOLO project as AI/ML (Computer Vision) and captures deployment metrics. Both handle skill standardization equally."
}"""

JOB_MATCHING_JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of AI-powered job-matching outputs.

You will be given a resume, the expected ranking behavior for that resume, and two job-scoring outputs labeled A and B.
Each output is a JSON object with a "job_scores" array. Each entry has job_id, match_score (0-100), reasoning, skill_matches, skill_gaps.

Your job is to grade each output on three dimensions and declare a winner.

SCORING DIMENSIONS (1–5 for each output):

- ranking_accuracy (1–5): Do the scores correctly separate good-fit jobs from bad-fit jobs?
    Good-fit jobs (labeled in expectations) should score substantially higher than bad-fit jobs.
    The spread between good and bad should be at least 20-30 points.
    Penalize: clustering all jobs in the 60-75 range regardless of fit.
    Penalize: a mobile-only iOS role scoring >50 for a full-stack Python/React candidate.
    Reward: clear discrimination — good jobs >70, bad jobs <45, with spread.
    1=no meaningful discrimination, 5=scores perfectly reflect the labeled fit.

- reasoning_quality (1–5): Is the `reasoning` field specific and useful to the candidate?
    Reward: references the candidate's actual projects/companies (e.g. "Burnt (YC)", "Internship Matcher") AND the job's specific requirements.
    Reward: includes at least one concrete detail (technology name, metric, deployment).
    Penalize: generic phrases like "Good match", "Candidate has relevant skills", "Strong technical background".
    Penalize: identical or near-identical reasoning across multiple jobs.
    1=all generic filler, 5=all specific and actionable.

- skill_gap_accuracy (1–5): Are skill_gaps accurate and honest?
    Penalize: listing skills as gaps when the candidate clearly has them (fabricated gaps).
    Penalize: listing 5+ gaps for a good-fit role (over-penalizing).
    Reward: empty gaps [] for strong matches, accurate gaps for genuine mismatches.
    1=fabricated or wildly inaccurate gaps, 5=gaps are precisely correct.

WINNER RULES:
- Declare "A" if A is clearly better overall across the three dimensions.
- Declare "B" if B is clearly better overall.
- Declare "tie" ONLY if the outputs are genuinely equivalent (within 0-1 points on each). Be decisive.

Return ONLY valid JSON. No markdown fences, no commentary outside the JSON:
{
  "scores_A": {"ranking_accuracy": 3, "reasoning_quality": 2, "skill_gap_accuracy": 4},
  "scores_B": {"ranking_accuracy": 5, "reasoning_quality": 4, "skill_gap_accuracy": 5},
  "winner": "B",
  "justification": "B correctly gives Nash Full Stack 84 and Reply iOS 28 (56-point spread) vs A's 72/55 (17-point spread). B's reasoning references 'Burnt (YC) production React work' specifically; A uses generic 'relevant skills'."
}"""

TAILORING_JUDGE_SYSTEM_PROMPT = """You are an expert evaluator of AI-powered resume tailoring outputs.

You will be given a resume, a target job description, expected tailoring behavior, and two tailored resume outputs labeled A and B.
Each output is a JSON object with experience bullets and other resume fields.

Grade each output on four dimensions and declare a winner.

SCORING DIMENSIONS (1–5 for each output):

- keyword_alignment (1–5): Do the rewritten bullets incorporate key terminology from the job description?
    Reward: bullets that front-load job-description keywords while remaining truthful.
    Penalize: bullets that ignore the job description and just restate the original.
    1=no alignment with job keywords, 5=bullets read as if written for this specific role.

- truthfulness (1–5): Does the output avoid fabricating skills, tools, or experiences?
    Penalize: any bullet that claims a technology or responsibility not in the original resume.
    Penalize: inflating scope (e.g., "led a team of 10" when original says nothing about team size).
    Reward: elaborating real work authentically (adding context to stated metrics).
    1=fabrications present, 5=strictly truthful throughout.

- specificity (1–5): Are bullets concrete with real metrics and details?
    Penalize: dropping numeric metrics that were in the original ("1000+ orders", "83% code reduction").
    Penalize: vague phrases like "improved performance significantly" replacing specific claims.
    Reward: bullets that preserve or add specific numbers, technologies, deployment contexts.
    1=vague throughout, 5=all bullets are specific with evidence.

- concision (1–5): Are bullets tight and impactful without padding?
    Penalize: filler phrases ("Collaborated with cross-functional teams", "Leveraged best practices").
    Reward: action-verb-first bullets under ~120 chars each with clear outcomes.
    1=padded with filler, 5=every word earns its place.

WINNER RULES: Same as standard — declare A, B, or tie. Be decisive.

Return ONLY valid JSON:
{
  "scores_A": {"keyword_alignment": 3, "truthfulness": 5, "specificity": 4, "concision": 3},
  "scores_B": {"keyword_alignment": 5, "truthfulness": 4, "specificity": 5, "concision": 4},
  "winner": "B",
  "justification": "B front-loads React/Node.js keywords from the job description while preserving '1000+ orders' and '52% latency' metrics. A uses generic bullets that ignore the job."
}"""

# Map context → (judge_system_prompt, max_tokens)
JUDGE_CONFIG = {
    "resume_parsing": (JUDGE_SYSTEM_PROMPT, 700),
    "resume_profile": (JUDGE_SYSTEM_PROMPT, 700),
    "job_matching":   (JOB_MATCHING_JUDGE_SYSTEM_PROMPT, 1800),
    "tailoring":      (TAILORING_JUDGE_SYSTEM_PROMPT, 1200),
}


def pairwise_judge(
    resume_text: str,
    expectations: str,
    output_a: dict,
    output_b: dict,
    context: str = "resume_parsing",
) -> dict:
    """
    Grade two extractions head-to-head.

    Returns a dict with keys: scores_A, scores_B, winner ("A"|"B"|"tie"), justification.
    Raises on API error or JSON parse failure.
    """
    system_prompt, max_tokens = JUDGE_CONFIG.get(context, (JUDGE_SYSTEM_PROMPT, 700))
    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    user_prompt = f"""RESUME TEXT:
{resume_text}

EXPECTED BEHAVIOR FOR THIS RESUME:
{expectations}

EXTRACTION A:
{json.dumps(output_a, indent=2)}

EXTRACTION B:
{json.dumps(output_b, indent=2)}

Grade both extractions on all dimensions and declare a winner."""

    response = client.messages.create(
        model=JUDGE_MODEL,
        max_tokens=max_tokens,
        temperature=0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown fences if the model wraps its output anyway
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Drop opening fence line
        lines = lines[1:]
        # Drop closing fence if present
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines).strip()

    return json.loads(raw)
