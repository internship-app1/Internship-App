import re
import os
import json
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

def extract_json_from_response(text: str) -> str:
    """
    Extract JSON from Claude response, handling markdown code blocks.
    Returns the cleaned JSON string ready for parsing.
    """
    # Remove markdown code blocks if present
    if "```json" in text:
        # Extract content between ```json and ```
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end == -1:
            # No closing ```, likely truncated
            return text[start:].strip()
        return text[start:end].strip()
    elif "```" in text:
        # Extract content between ``` and ```
        start = text.find("```") + 3
        end = text.find("```", start)
        if end == -1:
            # No closing ```, likely truncated
            return text[start:].strip()
        return text[start:end].strip()
    # Return as-is if no code blocks
    return text.strip()


def repair_truncated_json(json_str: str) -> str:
    """
    Attempt to repair truncated or malformed JSON.
    Handles common issues like unterminated strings, missing brackets, etc.
    """
    if not json_str:
        return "{}"

    # Remove any trailing incomplete text after last complete structure
    # Find the last valid closing brace
    last_brace = json_str.rfind('}')
    last_bracket = json_str.rfind(']')

    # Determine which one comes last
    last_valid = max(last_brace, last_bracket)

    if last_valid == -1:
        # No valid closing found, this is badly truncated
        return "{}"

    # Truncate to last valid closing
    truncated = json_str[:last_valid + 1]

    # Count opening and closing braces/brackets
    open_braces = truncated.count('{')
    close_braces = truncated.count('}')
    open_brackets = truncated.count('[')
    close_brackets = truncated.count(']')

    # Add missing closing characters
    if close_braces < open_braces:
        truncated += '}' * (open_braces - close_braces)
    if close_brackets < open_brackets:
        truncated += ']' * (open_brackets - close_brackets)

    return truncated


def validate_job_score_structure(score_obj: Dict) -> bool:
    """
    Validate that a job score object has all required fields.
    Returns True if valid, False otherwise.
    """
    required_fields = ['job_id', 'company', 'title', 'match_score', 'reasoning']

    for field in required_fields:
        if field not in score_obj:
            return False

    # Validate types
    if not isinstance(score_obj['job_id'], int):
        return False
    if not isinstance(score_obj['match_score'], int):
        return False
    if not isinstance(score_obj['reasoning'], str):
        return False

    # Validate score range
    if score_obj['match_score'] < 0 or score_obj['match_score'] > 100:
        return False

    return True


def clean_and_validate_llm_response(response_text: str, expected_job_count: int) -> Dict:
    """
    Comprehensive JSON cleaning, repair, and validation.

    Args:
        response_text: Raw JSON string from LLM
        expected_job_count: Number of jobs we expect to see scores for

    Returns:
        Parsed and validated JSON dict

    Raises:
        Exception: If JSON is irreparably malformed
    """
    # Step 1: Try to parse as-is
    try:
        result = json.loads(response_text)
        print("✅ JSON parsed successfully on first attempt")
    except json.JSONDecodeError as e:
        print(f"⚠️  Initial JSON parse failed: {e}")
        print(f"🔧 Attempting to repair JSON...")

        # Step 2: Try to repair truncated JSON
        repaired = repair_truncated_json(response_text)

        try:
            result = json.loads(repaired)
            print("✅ JSON repaired and parsed successfully")
        except json.JSONDecodeError as e2:
            print(f"❌ JSON repair failed: {e2}")
            print(f"📄 Original error at line {e.lineno}, col {e.colno}")
            print(f"📄 Repair error at line {e2.lineno}, col {e2.colno}")

            # Show diagnostic info
            lines = response_text.split('\n')
            start_line = max(0, e.lineno - 3)
            end_line = min(len(lines), e.lineno + 2)
            print("📄 Context around original error:")
            for i in range(start_line, end_line):
                marker = ">>> " if i == e.lineno - 1 else "    "
                print(f"{marker}{i+1}: {lines[i][:100]}")

            raise Exception(f"JSON is irreparably malformed: {e}")

    # Step 3: Validate structure
    if not isinstance(result, dict):
        raise Exception(f"Expected JSON object (dict), got {type(result)}")

    if "job_scores" not in result:
        raise Exception("Missing required field 'job_scores' in response")

    job_scores = result["job_scores"]

    if not isinstance(job_scores, list):
        raise Exception(f"'job_scores' should be a list, got {type(job_scores)}")

    # Step 4: Validate and clean individual job scores
    valid_scores = []
    invalid_count = 0

    for idx, score_obj in enumerate(job_scores):
        if not isinstance(score_obj, dict):
            print(f"⚠️  Job score #{idx+1} is not a dict, skipping")
            invalid_count += 1
            continue

        if not validate_job_score_structure(score_obj):
            print(f"⚠️  Job score #{idx+1} (job_id: {score_obj.get('job_id', '?')}) has invalid structure:")
            print(f"     Keys present: {list(score_obj.keys())}")
            invalid_count += 1
            continue

        # Ensure optional fields have defaults
        if 'red_flags' not in score_obj:
            score_obj['red_flags'] = []
        if 'skill_matches' not in score_obj:
            score_obj['skill_matches'] = []
        if 'skill_gaps' not in score_obj:
            score_obj['skill_gaps'] = []

        # Ensure arrays are actually arrays
        if not isinstance(score_obj['red_flags'], list):
            score_obj['red_flags'] = []
        if not isinstance(score_obj['skill_matches'], list):
            score_obj['skill_matches'] = []
        if not isinstance(score_obj['skill_gaps'], list):
            score_obj['skill_gaps'] = []

        valid_scores.append(score_obj)

    # Step 5: Report validation results
    print(f"📊 Validation results:")
    print(f"   Expected: {expected_job_count} jobs")
    print(f"   Received: {len(job_scores)} total job scores")
    print(f"   Valid: {len(valid_scores)} job scores")
    print(f"   Invalid: {invalid_count} job scores (skipped)")

    # Update result with cleaned scores
    result["job_scores"] = valid_scores

    # Step 6: Warn if we're missing jobs
    if len(valid_scores) < expected_job_count:
        missing = expected_job_count - len(valid_scores)
        print(f"⚠️  WARNING: Missing {missing} job scores (expected {expected_job_count}, got {len(valid_scores)} valid)")
        print(f"⚠️  This may indicate truncation or LLM error")

    # Step 7: Check for duplicate job_ids
    job_ids = [score['job_id'] for score in valid_scores]
    if len(job_ids) != len(set(job_ids)):
        print(f"⚠️  WARNING: Duplicate job_ids detected!")
        duplicates = [jid for jid in job_ids if job_ids.count(jid) > 1]
        print(f"   Duplicate IDs: {set(duplicates)}")

    return result


def extract_user_experience_level(resume_skills, resume_text=""):
    """
    Extract user's experience level from resume skills and text.
    Returns: 'student', 'recent_graduate', 'entry_level', 'experienced'
    """
    resume_text_lower = resume_text.lower()
    
    # Check for student indicators
    student_indicators = [
        "student", "university", "college", "bachelor", "master", "phd", "degree",
        "graduation", "academic", "campus", "freshman", "sophomore", "junior", "senior",
        "undergraduate", "graduate", "thesis", "research", "internship", "co-op"
    ]
    
    # Check for recent graduate indicators
    recent_graduate_indicators = [
        "recent graduate", "new graduate", "entry level", "junior", "0-2 years",
        "less than 2 years", "first job", "career starter"
    ]
    
    # Check for experienced indicators
    experienced_indicators = [
        "senior", "lead", "principal", "staff", "architect", "manager", "director",
        "5+ years", "10+ years", "extensive experience", "expert", "advanced",
        "seasoned", "veteran", "leadership", "mentor", "coach", "supervise"
    ]
    
    # Check resume text for experience indicators
    for indicator in experienced_indicators:
        if indicator in resume_text_lower:
            return "experienced"
    
    for indicator in recent_graduate_indicators:
        if indicator in resume_text_lower:
            return "recent_graduate"
    
    for indicator in student_indicators:
        if indicator in resume_text_lower:
            return "student"
    
    # Default to student if no clear indicators
    return "student"

def analyze_job_requirements(job_title, job_description, required_skills):
    """
    Analyze job requirements and return qualification level and key requirements.
    """
    text = f"{job_title} {job_description}".lower()
    
    # Check for senior/experienced requirements
    senior_indicators = [
        "senior", "lead", "principal", "staff", "architect", "manager", "director",
        "10+ years", "12+ years", "15+ years", "20+ years", "extensive experience",
        "expert", "advanced", "seasoned", "veteran", "senior level", "leadership",
        "mentor", "coach", "supervise", "manage", "oversee", "strategic"
    ]
    
    # Check for entry-level indicators
    entry_level_indicators = [
        "entry level", "junior", "intern", "student", "recent graduate", "new graduate",
        "0-2 years", "less than 2 years", "first job", "career starter", "training"
    ]
    
    # Determine qualification level
    qualification_level = "mid_level"  # default
    
    for indicator in senior_indicators:
        if indicator in text:
            qualification_level = "senior"
            break
    
    for indicator in entry_level_indicators:
        if indicator in text:
            qualification_level = "entry_level"
            break
    
    # Extract experience requirements
    experience_patterns = [
        r'(\d+)\+?\s*years?\s*experience',
        r'(\d+)\+?\s*years?\s*in\s*the\s*field',
        r'(\d+)\+?\s*years?\s*of\s*development',
        r'(\d+)\+?\s*years?\s*of\s*software',
        r'(\d+)\+?\s*years?\s*of\s*programming'
    ]
    
    required_years = 0
    for pattern in experience_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                years = int(match)
                required_years = max(required_years, years)
            except ValueError:
                continue
    
    return {
        "qualification_level": qualification_level,
        "required_years": required_years,
        "required_skills": required_skills
    }


def extract_skills_from_text(text):
    """Extract skills from text using LLM-based analysis instead of hardcoded keywords."""
    from matching.llm_skill_extractor import extract_job_skills_with_llm
    
    # Use LLM to extract skills from the text
    # Treat the text as a job description for skill extraction
    skills = extract_job_skills_with_llm("", text, "")
    
    return skills

def generate_llm_based_description(job, llm_analysis, resume_skills):
    """
    Generate rich career fit description based on LLM analysis data.
    This replaces the legacy match_job_to_resume description with LLM-based insights.
    """
    company_name = job.get('company', 'Unknown Company')
    full_title = job.get('title', 'Unknown Position')
    location = job.get('location', 'Location not specified')
    score = llm_analysis.get('score', 0)
    complexity = llm_analysis.get('resume_complexity', 'UNKNOWN')
    experience_match = llm_analysis.get('experience_match', 'unknown')
    skill_count = llm_analysis.get('skill_match_count', 0)
    reasoning = llm_analysis.get('reasoning', 'No analysis available')
    
    # Create opening line based on score and complexity
    if score >= 80:
        if complexity == 'ADVANCED':
            opening = f"🎯 **{company_name}** - Excellent match! This {full_title} position aligns perfectly with your advanced profile."
        else:
            opening = f"🎯 **{company_name}** - Great match! This {full_title} role is well-suited for your background."
    elif score >= 60:
        opening = f"✅ **{company_name}** - Good fit! This {full_title} position shows strong alignment with your skills."
    elif score >= 40:
        opening = f"⚠️ **{company_name}** - Moderate match. This {full_title} role has some promising elements."
    else:
        opening = f"📊 **{company_name}** - Limited match. This {full_title} position has minimal alignment."
    
    # Add LLM reasoning insights
    reasoning_section = f"\n\n**🤖 AI Analysis:** {reasoning}"
    
    # Add complexity and experience insights
    profile_section = f"\n\n**📊 Profile Match:**"
    profile_section += f"\n- Resume Complexity: **{complexity}** level"
    profile_section += f"\n- Experience Alignment: **{experience_match}**"
    
    if skill_count > 0:
        profile_section += f"\n- Skills Matched: **{skill_count}** relevant skills identified"
    
    # Add location info
    location_info = f"\n\n**📍 Location:** {location}"
    
    # Add final score with context
    score_context = f"\n\n**🎯 Match Score: {score}/100**"
    if score >= 70:
        score_context += " - **Highly Recommended**"
    elif score >= 40:
        score_context += " - **Worth Considering**"
    else :
        score_context += " - **May Not Be Ideal**"
    
    # Combine everything
    return opening + reasoning_section + profile_section + location_info + score_context

def intelligent_resume_based_scoring(job, resume_skills, resume_text=""):
    """
    LLM-based intelligent job scoring that analyzes resume complexity and candidate fit.
    This replaces rule-based scoring with AI-powered matching that considers:
    1. Resume complexity and sophistication
    2. Experience level appropriateness
    3. Skill matching quality
    4. Career trajectory alignment
    
    Returns: score (0-100)
    """
    if not resume_text or not resume_text.strip():
        print("❌ No resume text provided for intelligent scoring")
        raise Exception("Resume text is required for intelligent scoring")
    
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

        # Prepare job information
        job_title = job.get("title", "Unknown Position")
        job_company = job.get("company", "Unknown Company")
        job_description = job.get("description", "No description available")
        job_location = job.get("location", "Location not specified")
        job_skills = job.get("required_skills", [])

        # Create comprehensive prompt for intelligent matching
        prompt = f"""You are an expert **career advisor and technical resume analyst**. Your task is to evaluate how well a candidate's resume matches a specific job opportunity.

You must output a structured JSON assessment that is **precise, consistent, and parsable**.

---

## INPUT

**CANDIDATE RESUME**
- Skills: {resume_skills}
- Text (truncated to first 2000 chars): {resume_text[:2000]}

**JOB OPPORTUNITY**
- Company: {job_company}
- Title: {job_title}
- Location: {job_location}
- Description (truncated to first 1000 chars): {job_description[:1000]}
- Required Skills: {job_skills}

---

## EVALUATION FRAMEWORK

You will assign a **final score (0–100)** using the following weighted components:

### 1. RESUME COMPLEXITY (40% weight — MOST IMPORTANT)
Evaluate the candidate's technical and experiential sophistication.

**Advanced Resume (80–100 range):**
- Multiple technically complex projects (e.g., AI agents, distributed systems, production-grade apps)
- Work at reputable companies, startups, or internships
- Leadership, mentorship, or technical ownership experience
- Published research or open-source contributions
- Awards, hackathon wins, or recognized achievements
- Demonstrated depth (e.g., "Implemented Flask API with caching + CI/CD pipeline," not just "used Flask")

**Intermediate Resume (50–79 range):**
- Some real-world experience or strong personal projects
- Decent technical coverage but lacking in depth or complexity
- Limited leadership or research exposure

**Beginner Resume (0–49 range):**
- Only academic projects or class assignments
- Minimal or no professional experience
- Vague skill descriptions without technical detail
- Generic language: "Used JavaScript for websites" with no measurable output

---

### 2. EXPERIENCE LEVEL MATCHING (30% weight)
Determine if the job level matches the candidate's level.

**Rules:**
- If job includes "senior", "lead", "principal", "architect", "manager", "5+ years", or "10+ years"
  AND candidate is BEGINNER or INTERMEDIATE → **Immediate disqualification (score 0)**
- Entry-level candidates → good match for intern/entry roles
- Advanced candidates → poor match for entry-level roles
- Aim for "calibrated fit": the job should challenge but not exceed or undershoot the resume's demonstrated level.

---

### 3. SKILL ALIGNMENT (20% weight)
Compare required job skills with resume skills.

**Evaluation criteria:**
- Count how many required skills are present AND demonstrated (not just listed)
- 0–1 overlapping skills → score 0
- 2–3 overlapping skills → acceptable (50–70)
- 4+ well-demonstrated skills → strong alignment (80–100)
- Consider relevance (e.g., "React" matches "ReactJS" but not "Vue")

---

### 4. CAREER FIT (10% weight)
Assess whether the role aligns with the candidate's next logical step:
- Does this job advance their current trajectory?
- Is it in the same or a natural evolution of their domain?
- Would this role reasonably leverage and expand their current skills?

---

## SCORING RULES

| Situation | Action |
|------------|---------|
| Senior-level job + beginner resume | **Return 0 (disqualified)** |
| Job requires 5+ years, resume < 2 years | **Return 0 (disqualified)** |
| <2 required skills matched | **Return 0 (disqualified)** |
| Role clearly misaligned with candidate level | **Return ≤ 30 (red flag)** |
| Poor general fit | **Return 1–40 (not recommended)** |
| Adequate fit | **Return 41–70 (reasonable)** |
| Excellent alignment | **Return 71–100 (strong recommendation)** |

---

## OUTPUT FORMAT (STRICT JSON ONLY)

Return ONLY valid JSON (no markdown, no code blocks):

{{
  "score": <integer 0–100>,
  "resume_complexity": "<ADVANCED | INTERMEDIATE | BEGINNER>",
  "complexity_score": <integer 0–100>,
  "experience_match": "<excellent | good | acceptable | poor | disqualified>",
  "skill_match_count": <integer>,
  "reasoning": "<1–3 concise sentences summarizing reasoning>",
  "red_flags": ["<any disqualifying issues, or empty array if none>"]
}}

---

## EXAMPLES

**Example 1: Excellent Match**
- Resume: 2 internships, built AI SaaS project, led hackathon team
- Job: Junior AI Developer (Python, Flask, ML)
- Output:
{{
  "score": 92,
  "resume_complexity": "ADVANCED",
  "complexity_score": 88,
  "experience_match": "excellent",
  "skill_match_count": 5,
  "reasoning": "Strong technical depth, 2 relevant internships, direct Python/Flask/ML experience aligns perfectly.",
  "red_flags": []
}}

**Example 2: Poor Match — Overqualified**
- Resume: Senior backend engineer, 10+ years experience
- Job: Intern software developer
- Output:
{{
  "score": 25,
  "resume_complexity": "ADVANCED",
  "complexity_score": 95,
  "experience_match": "poor",
  "skill_match_count": 4,
  "reasoning": "Candidate far exceeds role requirements; this position is below their demonstrated level.",
  "red_flags": ["Overqualified for position"]
}}

**Example 3: Disqualified — Lacks Skill Alignment**
- Resume: Web designer with HTML/CSS
- Job: Backend Engineer (Java, SQL, Spring Boot)
- Output:
{{
  "score": 0,
  "resume_complexity": "INTERMEDIATE",
  "complexity_score": 60,
  "experience_match": "disqualified",
  "skill_match_count": 0,
  "reasoning": "No overlap in required backend technologies; lacks Java or SQL experience.",
  "red_flags": ["Missing required skills"]
}}

**Example 4: Acceptable — Beginner for Entry Role**
- Resume: 2 university projects (React, Node.js)
- Job: Frontend Intern (React, HTML, CSS)
- Output:
{{
  "score": 68,
  "resume_complexity": "BEGINNER",
  "complexity_score": 45,
  "experience_match": "good",
  "skill_match_count": 3,
  "reasoning": "Beginner-level candidate matches well for entry-level React internship.",
  "red_flags": []
}}

---

## NOTES
- Keep reasoning concise and factual (avoid opinions or restating data).
- Use conservative scoring — reward clear depth, penalize vagueness.
- Never include non-JSON text in output."""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=400,
            system="You are an expert career advisor who analyzes resume complexity and job fit. You heavily weight resume sophistication when determining if a job is appropriate for a candidate. You prevent mismatches by filtering out senior roles for beginners and entry roles for advanced candidates. Always return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)
        score = result.get("score", 0)
        complexity = result.get("resume_complexity", "UNKNOWN")
        reasoning = result.get("reasoning", "No reasoning provided")
        
        print(f"🤖 Intelligent Scoring: {job_company} - {job_title}")
        print(f"   Score: {score}/100 | Complexity: {complexity}")
        print(f"   Reasoning: {reasoning}")
        
        # Return full analysis object instead of just score
        return {
            "score": score,
            "resume_complexity": complexity,
            "complexity_score": result.get("complexity_score", score),
            "experience_match": result.get("experience_match", "unknown"),
            "skill_match_count": result.get("skill_match_count", 0),
            "reasoning": reasoning,
            "red_flags": result.get("red_flags", [])
        }
        
    except Exception as e:
        print(f"❌ Error in intelligent scoring for {job.get('title', 'Unknown')}: {e}")
        raise Exception(f"Intelligent scoring failed: {str(e)}")


def calculate_optimal_batch_size(jobs: List[Dict], resume_text: str, min_size: int = 5, max_size: int = 30) -> int:
    """
    Dynamically calculate optimal batch size based on content length.
    Prevents truncation while maximizing throughput.

    Args:
        jobs: List of job dictionaries
        resume_text: Candidate's resume text
        min_size: Minimum jobs per batch (default: 5)
        max_size: Maximum jobs per batch (default: 30)

    Returns:
        Optimal number of jobs to process in a single batch
    """
    if not jobs:
        return min_size

    # Calculate average job description length (we truncate to 500 chars in prompt)
    total_desc_length = sum(min(len(job.get('description', '')), 500) for job in jobs)
    avg_desc_length = total_desc_length / len(jobs) if jobs else 0

    # Resume context length (we truncate to 1500 chars in prompt)
    resume_context_length = min(len(resume_text), 1500)

    # Estimate tokens per job in the response (comprehensive analysis)
    # Each job analysis includes: reasoning, skill_matches, skill_gaps, red_flags
    estimated_response_tokens_per_job = 250

    # Estimate tokens per job in the prompt based on ACTUAL average description length
    # Includes: job_id, company, title, location, description
    # Convert chars to tokens (roughly 4 chars = 1 token)
    job_metadata_chars = 100  # company, title, location, job_id
    estimated_prompt_tokens_per_job = (avg_desc_length + job_metadata_chars) // 4

    # Fixed prompt overhead (instructions, examples, formatting)
    fixed_prompt_overhead = 2500  # Base prompt tokens

    # Resume overhead
    resume_overhead = resume_context_length // 4  # chars to tokens

    # Model's max output tokens (we can request up to 16000)
    max_output_tokens = 16000

    # Calculate how many jobs we can fit
    # We need to ensure: (fixed + resume + jobs*prompt_size) + (jobs*response_size) < total_budget
    total_budget = max_output_tokens
    available_for_jobs = total_budget - fixed_prompt_overhead - resume_overhead

    # Each job uses: prompt tokens + response tokens
    tokens_per_job = estimated_prompt_tokens_per_job + estimated_response_tokens_per_job

    # Ensure we don't divide by zero
    if tokens_per_job <= 0:
        tokens_per_job = 300  # Safe default

    optimal_size = int(available_for_jobs / tokens_per_job)

    # Clamp to min/max bounds
    optimal_size = max(min_size, min(optimal_size, max_size))

    # Dynamic batch sizing calculated silently

    return optimal_size


def intelligent_prefilter_jobs(jobs, resume_skills, resume_metadata, target_count=30, progress_callback=None):
    """
    Sophisticated multi-layer pre-filtering to select the best job candidates
    from the full cache for LLM analysis. Preserves accuracy while being efficient.
    Reduced to 30 jobs max to prevent LLM token limit issues.
    """
    # Send progress: Starting pre-filtering
    if progress_callback:
        progress_callback("Pre-filtering top candidates for you...")

    if len(jobs) <= target_count:
        return jobs

    # Stage 1A: Hard requirement filtering
    experience_level = resume_metadata.get('experience_level', 'student')
    years_experience = resume_metadata.get('years_of_experience', 0)
    is_student = resume_metadata.get('is_student', True)

    filtered_jobs = []
    for job in jobs:
        job_title = job.get('title', '').lower()
        job_description = job.get('description', '').lower()

        # Filter out senior/inappropriate roles
        senior_indicators = ['senior', 'lead', 'principal', 'staff', 'architect', 'manager', 'director']
        if any(indicator in job_title for indicator in senior_indicators):
            if experience_level in ['student', 'recent_graduate'] or years_experience < 3:
                continue  # Skip senior roles for junior candidates

        # Filter out high experience requirements
        import re
        exp_patterns = [r'(\d+)\+?\s*years?\s*(?:of\s+)?experience', r'(\d+)\+?\s*years?\s*(?:of\s+)?(?:software|development|programming)']
        skip_job = False
        for pattern in exp_patterns:
            matches = re.findall(pattern, f"{job_title} {job_description}")
            for match in matches:
                try:
                    required_years = int(match)
                    if required_years >= 5 and years_experience < 3:
                        skip_job = True
                        break
                except ValueError:
                    continue
            if skip_job:
                break

        if skip_job:
            continue

        filtered_jobs.append(job)

    # Return all filtered jobs (no hardcoded scoring)
    return filtered_jobs[:target_count]


def batch_analyze_jobs_with_llm(filtered_jobs, resume_skills, resume_text, resume_metadata, max_jobs_per_batch=None, use_parallel=True, model="claude-sonnet-4-5-20250929", enable_caching=True, progress_callback=None):
    """
    Comprehensive batch LLM analysis of pre-filtered jobs.
    Uses dynamic batch sizing and parallel processing for maximum speed.
    Automatically retries with smaller batches if truncation detected.

    Args:
        filtered_jobs: List of jobs to analyze
        resume_skills: List of candidate skills
        resume_text: Full resume text
        resume_metadata: Candidate metadata
        max_jobs_per_batch: Override automatic batch sizing (optional)
        use_parallel: Enable parallel processing (default: True)
        model: Claude model to use - "claude-sonnet-4-5-20250929" (default, slower but better) or "claude-haiku-3-5-20241022" (10x faster)
        enable_caching: Enable prompt caching for 40-60% speed improvement (default: True)
        progress_callback: Optional callback function to report progress (takes message string)
    """
    if not filtered_jobs:
        return []

    # Calculate optimal batch size if not provided
    if max_jobs_per_batch is None:
        max_jobs_per_batch = calculate_optimal_batch_size(filtered_jobs, resume_text)

    # If we have more jobs than max_jobs_per_batch, split into chunks
    if len(filtered_jobs) > max_jobs_per_batch:
        # Create chunks
        chunks = []
        for i in range(0, len(filtered_jobs), max_jobs_per_batch):
            chunk = filtered_jobs[i:i + max_jobs_per_batch]
            chunks.append((chunk, i + 1))  # (chunk_jobs, start_id)

        total_chunks = len(chunks)

        # Send progress: Starting batch analysis
        if progress_callback:
            progress_callback(f"Running AI career analysis (batch 1 of {total_chunks})...")

        # Process chunks in parallel or sequentially
        if use_parallel and total_chunks > 1:
            all_scores = _process_chunks_parallel(chunks, resume_skills, resume_text, resume_metadata, model, enable_caching, progress_callback=progress_callback)
        else:
            all_scores = _process_chunks_sequential(chunks, resume_skills, resume_text, resume_metadata, model, enable_caching, progress_callback=progress_callback)

        return all_scores

    # Single batch processing (no chunking needed)
    # Send progress for single batch
    if progress_callback:
        progress_callback("Running AI career analysis...")

    return _analyze_single_batch(filtered_jobs, resume_skills, resume_text, resume_metadata, start_id=1, model=model, enable_caching=enable_caching)


def _process_chunks_parallel(chunks: List[tuple], resume_skills, resume_text, resume_metadata, model, enable_caching, max_workers: int = 3, progress_callback=None) -> List[Dict]:
    """
    Process multiple chunks in parallel using ThreadPoolExecutor.

    Args:
        chunks: List of (chunk_jobs, start_id) tuples
        resume_skills: Candidate skills
        resume_text: Resume text
        resume_metadata: Metadata
        model: Claude model to use
        enable_caching: Whether to enable prompt caching
        max_workers: Maximum concurrent API calls (default: 3 to respect rate limits)
        progress_callback: Optional callback function to report progress

    Returns:
        Combined list of all job scores from all chunks
    """
    all_scores = []
    total_chunks = len(chunks)
    completed_chunks = 0

    # Use ThreadPoolExecutor for parallel API calls
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all chunks for processing
        future_to_chunk = {}
        for chunk_idx, (chunk_jobs, start_id) in enumerate(chunks):
            chunk_num = chunk_idx + 1
            future = executor.submit(
                _analyze_single_batch_with_retry,
                chunk_jobs,
                resume_skills,
                resume_text,
                resume_metadata,
                start_id,
                chunk_num,
                len(chunks),
                model,
                enable_caching
            )
            future_to_chunk[future] = (chunk_num, len(chunk_jobs))

        # Collect results as they complete
        for future in as_completed(future_to_chunk):
            chunk_num, chunk_size = future_to_chunk[future]
            try:
                chunk_scores = future.result()
                all_scores.extend(chunk_scores)
                completed_chunks += 1

                # Send progress after each batch completes (skip batch 1 since it was already reported)
                if progress_callback and completed_chunks < total_chunks:
                    next_batch = completed_chunks + 1
                    progress_callback(f"Running AI career analysis (batch {next_batch} of {total_chunks})...")

            except Exception:
                # Continue processing other chunks silently
                continue

    return all_scores


def _process_chunks_sequential(chunks: List[tuple], resume_skills, resume_text, resume_metadata, model, enable_caching, progress_callback=None) -> List[Dict]:
    """
    Process chunks one at a time (fallback for when parallel fails or is disabled).

    Args:
        chunks: List of (chunk_jobs, start_id) tuples
        resume_skills: Candidate skills
        resume_text: Resume text
        resume_metadata: Metadata
        model: Claude model to use
        enable_caching: Whether to enable prompt caching
        progress_callback: Optional callback function to report progress

    Returns:
        Combined list of all job scores from all chunks
    """
    all_scores = []

    for chunk_idx, (chunk_jobs, start_id) in enumerate(chunks):
        chunk_num = chunk_idx + 1
        total_chunks = len(chunks)

        # Send progress for each batch (skip batch 1 since it was already reported)
        if progress_callback and chunk_num > 1:
            progress_callback(f"Running AI career analysis (batch {chunk_num} of {total_chunks})...")

        try:
            chunk_scores = _analyze_single_batch_with_retry(
                chunk_jobs,
                resume_skills,
                resume_text,
                resume_metadata,
                start_id,
                chunk_num,
                total_chunks,
                model,
                enable_caching
            )
            all_scores.extend(chunk_scores)
        except Exception:
            continue

    return all_scores


def _analyze_single_batch_with_retry(chunk_jobs, resume_skills, resume_text, resume_metadata, start_id, chunk_num, total_chunks, model, enable_caching, max_retries: int = 2):
    """
    Analyze a single batch with automatic retry on failure.

    Args:
        chunk_jobs: Jobs in this chunk
        resume_skills: Candidate skills
        resume_text: Resume text
        resume_metadata: Metadata
        start_id: Starting job ID for this chunk
        chunk_num: Chunk number (for logging)
        total_chunks: Total number of chunks (for logging)
        model: Claude model to use
        enable_caching: Whether to enable prompt caching
        max_retries: Maximum retry attempts

    Returns:
        List of job scores for this chunk
    """
    for attempt in range(max_retries + 1):
        try:
            chunk_scores = _analyze_single_batch(
                chunk_jobs,
                resume_skills,
                resume_text,
                resume_metadata,
                start_id,
                model,
                enable_caching
            )
            return chunk_scores
        except Exception as e:
            if attempt < max_retries:
                # Retry with smaller batch if we have retries left
                if len(chunk_jobs) > 5:
                    smaller_batch_size = max(5, len(chunk_jobs) // 2)

                    # Split and retry recursively
                    return batch_analyze_jobs_with_llm(
                        chunk_jobs,
                        resume_skills,
                        resume_text,
                        resume_metadata,
                        max_jobs_per_batch=smaller_batch_size,
                        use_parallel=False,  # Don't use parallel for retries
                        model=model,
                        enable_caching=enable_caching
                    )
                else:
                    raise
            else:
                raise


def _analyze_single_batch(filtered_jobs, resume_skills, resume_text, resume_metadata, start_id=1, model="claude-sonnet-4-5-20250929", enable_caching=True):
    """
    Internal function to analyze a single batch of jobs.
    Separated for reusability in chunking logic.

    Args:
        filtered_jobs: Jobs to analyze in this batch
        resume_skills: Candidate's skills
        resume_text: Full resume text
        resume_metadata: Candidate metadata
        start_id: Starting job ID for this batch
        model: Claude model to use (sonnet or haiku)
        enable_caching: Enable prompt caching for speed (default: True)
    """
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

        # Create candidate profile summary
        experience_level = resume_metadata.get('experience_level', 'student')
        years_experience = resume_metadata.get('years_of_experience', 0)

        # Format jobs for batch analysis
        jobs_summary = []
        for i, job in enumerate(filtered_jobs):
            job_summary = {
                "job_id": start_id + i,
                "company": job.get('company', 'Unknown'),
                "title": job.get('title', 'Unknown'),
                "location": job.get('location', 'Unknown'),
                "description": job.get('description', '')[:500]  # Limit description length
            }
            jobs_summary.append(job_summary)

        # Create comprehensive batch analysis prompt
        # Use json.dumps to safely escape all strings
        candidate_profile = {
            "resume_skills": resume_skills,
            "experience_level": experience_level,
            "years_experience": years_experience,
            "resume_context": resume_text[:1500]
        }

        # Split prompt into cacheable and non-cacheable parts for prompt caching optimization

        # CACHEABLE PART 1: Static scoring instructions (same for all batches in all sessions)
        static_instructions = """For EACH job, provide detailed analysis using this WEIGHTED SCORING SYSTEM:

🏆 SCORING WEIGHTS (Total = 100 points):

1. **PROJECT DEPTH & REAL-WORLD IMPACT (35% - HIGHEST PRIORITY)**
   Look for evidence of:
   - ✅ PRODUCTION DEPLOYMENTS: "deployed to production", "live users", "in production"
   - ✅ REAL USER IMPACT: Actual user counts, engagement metrics, downloads, usage stats
   - ✅ TECHNICAL COMPLEXITY: System design, scalability, architecture, performance optimization
   - ✅ PROBLEM-SOLVING DEPTH: Specific technical challenges solved (not just "built a website")
   - ✅ PROJECT SCALE: Team size, codebase size, duration, iterations
   - ✅ TANGIBLE RESULTS: Revenue generated, users acquired, performance improvements (e.g., "reduced load time by 40%")

   🚫 IGNORE KEYWORD RESUMES: If resume just lists technologies without depth ("Built app using React, Node.js") = LOW SCORE
   ⭐ REWARD DEPTH: "Deployed React app to AWS with 500+ daily users, implemented Redis caching reducing API latency by 60%" = HIGH SCORE

2. **WORK EXPERIENCE QUALITY (25%)**
   - Real internships/jobs at actual companies >> Academic projects
   - Startup/company experience >> Side projects >> Coursework
   - Leadership roles, mentoring, team collaboration
   - Open source contributions, published work
   - Research with publications or citations

3. **SKILL ALIGNMENT WITH JOB (20%)**
   - How many DEMONSTRATED skills (not just mentioned) match the role?
   - Quality over quantity: Deep expertise in 2-3 technologies > Surface knowledge of 10
   - Consider technology stack alignment (e.g., React experience for React role)

4. **EXPERIENCE LEVEL APPROPRIATENESS (15%)**
   - Is this role suitable for candidate's level?
   - CRITICAL: Senior roles for juniors = 0 score
   - Entry-level roles for advanced candidates = lower score (they'd be bored)

5. **CAREER TRAJECTORY & GROWTH POTENTIAL (5%)**
   - Does this role advance their career?
   - Learning opportunities in the role
   - Company reputation and mentorship

📊 SCORING EXAMPLES:

HIGH SCORE (80-95):
- "Deployed full-stack e-commerce platform with 1000+ users, integrated Stripe payments, built CI/CD pipeline with GitHub Actions" → 85
- "Interned at Microsoft on Azure team, shipped feature used by 10K+ developers, reduced deployment time by 50%" → 92

MEDIUM SCORE (50-70):
- "Built multiple React projects including todo app and weather app with API integration" → 55
- "Completed 3 academic projects: database system, mobile app, web scraper" → 60

LOW SCORE (20-40):
- "Familiar with React, Node.js, Python, Java, AWS, Docker..." (just keywords, no depth) → 25
- "Course projects using various technologies" (no specifics) → 30

2. **REASONING** (2-3 sentences): Be SPECIFIC about:
   - What production/real-world experience stands out?
   - Which demonstrated skills (with depth) match this role?
   - Why this score vs higher/lower?

3. **RED_FLAGS**: Note if:
   - Resume is all keywords with no substance
   - Experience level mismatch
   - No evidence of actual deployments or real work

4. **SKILL_MATCHES**: Only list skills with DEMONSTRATED depth (not just mentioned)
5. **SKILL_GAPS**: Important skills for the role they don't show evidence of

⚠️ CRITICAL REQUIREMENTS:
- NO two jobs should have identical scores (vary based on specifics)
- HEAVILY PENALIZE keyword-only resumes without depth
- HEAVILY REWARD production deployments and real-world impact
- Value 1 production project > 10 tutorial projects
- Look for metrics, users, performance improvements, business impact
- Consider: "Would I hire this person based on proven results, not buzzwords?"

⚠️ JSON FORMAT REQUIREMENTS (CRITICAL):
- Return ONLY valid, parsable JSON
- NO markdown code blocks (no ```)
- NO extra text before or after JSON
- MUST include ALL required fields for EVERY job
- Required fields: job_id, company, title, match_score, reasoning
- Optional fields: red_flags, skill_matches, skill_gaps (provide empty arrays if none)
- Ensure proper JSON syntax: matching quotes, braces, brackets, commas
- Use double quotes (") for strings, NOT single quotes (')
- Escape special characters in strings (quotes, backslashes, newlines)
- ANALYZE ALL {len(filtered_jobs)} JOBS - do not skip any

Return ONLY this JSON structure:
{{
  "analysis_summary": "Overall assessment of candidate's market fit",
  "job_scores": [
    {{
      "job_id": 1,
      "company": "Company Name",
      "title": "Job Title",
      "match_score": 85,
      "reasoning": "Candidate deployed production app with 500+ users using React/Node stack matching role requirements. Demonstrated scaling and performance optimization experience. Strong fit for this full-stack internship.",
      "red_flags": [],
      "skill_matches": ["React", "Node.js", "AWS", "PostgreSQL"],
      "skill_gaps": ["TypeScript", "GraphQL"]
    }}
  ]
}}

IMPORTANT: Return complete JSON for all jobs. Do not truncate or abbreviate."""

        # CACHEABLE PART 2: Candidate profile (same for all batches in this session)
        candidate_context = f"""CANDIDATE PROFILE:
{json.dumps(candidate_profile, indent=2)}

You will analyze multiple job opportunities for this candidate using the scoring system provided."""

        # NON-CACHEABLE PART: Job-specific data (changes every batch)
        jobs_prompt = f"""JOBS TO ANALYZE ({len(filtered_jobs)} positions):
{json.dumps(jobs_summary, indent=2)}

Analyze each job and return complete JSON for all {len(filtered_jobs)} jobs."""

        # Removed debug logging for cleaner output

        # Calculate max tokens with content-aware sizing
        # Account for actual content length, not just job count
        total_job_content_length = sum(len(job.get('description', '')[:500]) for job in filtered_jobs)
        avg_job_content_length = total_job_content_length / len(filtered_jobs) if filtered_jobs else 0

        # Estimate response tokens per job (comprehensive analysis with all fields)
        estimated_response_tokens_per_job = 250

        # Estimate prompt overhead
        base_prompt_tokens = 2500  # Fixed instructions
        resume_tokens = len(resume_text[:1500]) // 4  # Resume context
        job_content_tokens = total_job_content_length // 4  # Job descriptions

        # Total estimated tokens needed
        estimated_prompt_tokens = base_prompt_tokens + resume_tokens + job_content_tokens
        estimated_response_tokens = len(filtered_jobs) * estimated_response_tokens_per_job
        estimated_total = estimated_prompt_tokens + estimated_response_tokens

        # Add 20% buffer for safety
        max_tokens = min(16000, int(estimated_response_tokens * 1.2))

        # Removed verbose token allocation logging

        # Build system message with prompt caching
        if enable_caching:
            # Use structured system message with cache control for better performance
            system_message = [
                {
                    "type": "text",
                    "text": "You are an expert technical recruiter who values DEMONSTRATED IMPACT over buzzwords. You heavily weight: production deployments, real users, measurable results, technical depth, and proven problem-solving. You penalize keyword-stuffed resumes without substance. You ensure scoring diversity by carefully weighing each candidate's real-world accomplishments. CRITICAL: Always return ONLY valid, complete, parsable JSON with no markdown formatting, no code blocks, and no extra text. Include ALL required fields for EVERY job analyzed. Never truncate or abbreviate your response.",
                    "cache_control": {"type": "ephemeral"}  # Cache system instructions
                },
                {
                    "type": "text",
                    "text": static_instructions,
                    "cache_control": {"type": "ephemeral"}  # Cache scoring criteria
                },
                {
                    "type": "text",
                    "text": candidate_context,
                    "cache_control": {"type": "ephemeral"}  # Cache candidate profile
                }
            ]
            pass  # Caching enabled silently
        else:
            # Fallback to simple string system message (no caching)
            system_message = f"You are an expert technical recruiter who values DEMONSTRATED IMPACT over buzzwords. You heavily weight: production deployments, real users, measurable results, technical depth, and proven problem-solving. You penalize keyword-stuffed resumes without substance. You ensure scoring diversity by carefully weighing each candidate's real-world accomplishments. CRITICAL: Always return ONLY valid, complete, parsable JSON with no markdown formatting, no code blocks, and no extra text. Include ALL required fields for EVERY job analyzed. Never truncate or abbreviate your response.\n\n{static_instructions}\n\n{candidate_context}"

        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_message,
            messages=[
                {
                    "role": "user",
                    "content": jobs_prompt  # Only job-specific data in user message
                }
            ]
        )

        # Process LLM response
        raw_response = response.content[0].text

        # Check if response was truncated
        if response.stop_reason == "max_tokens":
            raise Exception(f"Response truncated - reduce batch size from {len(filtered_jobs)} jobs")

        # Extract JSON from response
        response_text = extract_json_from_response(raw_response)

        # Clean, repair, and validate JSON
        try:
            result = clean_and_validate_llm_response(response_text, len(filtered_jobs))
        except Exception as validation_error:
            # This is likely truncation or malformed JSON - raise for retry
            raise Exception(f"Response validation failed - reduce batch size from {len(filtered_jobs)} jobs")

        job_scores = result.get("job_scores", [])

        return job_scores

    except Exception as e:
        print(f"❌ Error in batch LLM analysis: {e}")

        # Re-raise to allow caller to handle retries
        raise Exception(f"Batch LLM analysis failed: {str(e)}")

def enhance_batch_results(llm_scores, original_jobs, resume_skills=None):
    """
    Enhance LLM batch results with original job data and create rich descriptions.
    """
    enhanced_jobs = []
    
    for score_data in llm_scores:
        job_id = score_data.get("job_id", 1) - 1  # Convert to 0-based index
        
        if job_id < len(original_jobs):
            original_job = original_jobs[job_id]
            
            # Create enhanced job object
            enhanced_job = original_job.copy()
            enhanced_job['match_score'] = score_data.get('match_score', 0)
            
            # Create rich AI reasoning object with meaningful data
            match_score = score_data.get('match_score', 0)
            skill_matches = score_data.get('skill_matches', [])
            skill_gaps = score_data.get('skill_gaps', [])
            reasoning = score_data.get('reasoning', '').lower()
            
            # Fallback: If LLM didn't provide skill matches/gaps, extract them manually
            if not skill_matches and not skill_gaps:
                job_skills = original_job.get('required_skills', [])
                if job_skills and resume_skills:
                    # Use dynamic skill matching to get actual matches
                    try:
                        from matching.llm_skill_extractor import match_skills_dynamically
                        # Get real skill matches using the dynamic matching system
                        matches = match_skills_dynamically(job_skills, resume_skills, threshold=0.7)
                        skill_matches = [match["job_skill"] for match in matches]
                        
                        # Skills that weren't matched are gaps
                        skill_gaps = [skill for skill in job_skills if skill not in skill_matches]
                    except:
                        # Final fallback based on score
                        if match_score > 0:
                            # If there's a score > 0, assume some matches exist
                            skill_matches = job_skills[:min(2, len(job_skills))]
                            skill_gaps = job_skills[len(skill_matches):]
                        else:
                            # No matches, all skills are gaps
                            skill_matches = []
                            skill_gaps = job_skills[:5]  # Limit to 5 for display
                elif job_skills:
                    # No resume skills available, treat all job skills as gaps
                    skill_matches = []
                    skill_gaps = job_skills[:5]  # Limit to 5 for display
            
            # Determine resume complexity based on score, skills, AND real-world impact indicators
            # Look for production/impact keywords in the reasoning
            production_indicators = [
                'production', 'deployed', 'users', 'live', 'published', 'shipped',
                'performance', 'scale', 'optimization', 'real-world', 'impact',
                'metrics', 'revenue', 'intern', 'company', 'team', 'enterprise'
            ]
            
            impact_count = sum(1 for indicator in production_indicators if indicator in reasoning)
            
            # Advanced: High score + many skills + production impact
            if match_score >= 75 and len(skill_matches) >= 4 and impact_count >= 2:
                resume_complexity = "ADVANCED"
            # Intermediate: Good score + decent skills OR strong production impact
            elif match_score >= 60 or len(skill_matches) >= 3 or impact_count >= 3:
                resume_complexity = "INTERMEDIATE"
            else:
                resume_complexity = "ENTRY_LEVEL"
            
            # Determine experience match description based on score and impact
            if match_score >= 80:
                if impact_count >= 3:
                    experience_match = "Excellent - Proven production experience aligns perfectly"
                else:
                    experience_match = "Excellent - Your skills align perfectly with this role"
            elif match_score >= 70:
                if impact_count >= 2:
                    experience_match = "Strong - Real-world experience matches key requirements"
                else:
                    experience_match = "Strong - You have most key qualifications"
            elif match_score >= 60:
                experience_match = "Good - Solid foundation with room to grow"
            elif match_score >= 40:
                experience_match = "Moderate - Some gaps but achievable with effort"
            else:
                experience_match = "Limited - Significant skill development needed"
            
            enhanced_job['ai_reasoning'] = {
                "score": match_score,
                "resume_complexity": resume_complexity,
                "complexity_score": match_score,
                "experience_match": experience_match,
                "skill_match_count": len(skill_matches),
                "reasoning": score_data.get('reasoning', ''),
                "red_flags": score_data.get('red_flags', []),
                "skill_matches": skill_matches,
                "skill_gaps": skill_gaps
            }
            
            # Ensure we always have meaningful skill data for display
            if not enhanced_job['ai_reasoning']['skill_matches']:
                enhanced_job['ai_reasoning']['skill_matches'] = []
            if not enhanced_job['ai_reasoning']['skill_gaps']:
                enhanced_job['ai_reasoning']['skill_gaps'] = []
            
            # Create rich match description
            enhanced_job['match_description'] = create_rich_match_description(
                original_job, score_data, enhanced_job['ai_reasoning']
            )
            
            enhanced_jobs.append(enhanced_job)
    
    # Sort by match score
    enhanced_jobs.sort(key=lambda x: x['match_score'], reverse=True)
    
    return enhanced_jobs

def create_rich_match_description(job, score_data, ai_reasoning):
    """
    Create rich, detailed match description from LLM analysis.
    """
    company = job.get('company', 'Unknown Company')
    title = job.get('title', 'Unknown Position')
    location = job.get('location', 'Location not specified')
    score = score_data.get('match_score', 0)
    reasoning = score_data.get('reasoning', '')
    skill_matches = score_data.get('skill_matches', [])
    skill_gaps = score_data.get('skill_gaps', [])
    red_flags = score_data.get('red_flags', [])
    
    # Create opening based on score
    if score >= 80:
        opening = f"🎯 **{company}** - Excellent match! This {title} position is highly recommended for your profile."
    elif score >= 60:
        opening = f"✅ **{company}** - Strong fit! This {title} role aligns well with your background."
    elif score >= 40:
        opening = f"⚠️ **{company}** - Moderate match. This {title} position has potential but some gaps."
    else:
        opening = f"📊 **{company}** - Limited fit. This {title} role may not be ideal for your current profile."
    
    # Add AI reasoning
    ai_section = f"\n\n**🤖 AI Analysis:** {reasoning}"
    
    # Add skill analysis
    skill_section = f"\n\n**🎯 Skill Analysis:**"
    if skill_matches:
        skill_section += f"\n- ✅ **Your matching skills:** {', '.join(skill_matches)}"
    if skill_gaps:
        skill_section += f"\n- 📚 **Skills to develop:** {', '.join(skill_gaps[:3])}"
        if len(skill_gaps) > 3:
            skill_section += f" (+{len(skill_gaps) - 3} more)"
    
    # Add red flags if any
    red_flag_section = ""
    if red_flags:
        red_flag_section = f"\n\n**⚠️ Considerations:**"
        for flag in red_flags[:2]:  # Limit to 2 red flags
            red_flag_section += f"\n- {flag}"
    
    # Add location
    location_section = f"\n\n**📍 Location:** {location}"
    
    # Add final score
    score_section = f"\n\n**🎯 Match Score: {score}/100**"
    if score >= 70:
        score_section += " - **Highly Recommended**"
    elif score >= 40:
        score_section += " - **Worth Considering**"
    else:
        score_section += " - **May Not Be Ideal**"
    
    return opening + ai_section + skill_section + red_flag_section + location_section + score_section

def fuzzy_skill_match(resume_skill, job_skill):
    """
    Intelligent fuzzy matching for skills to handle variations.

    Examples:
    - "React" matches "ReactJS", "React.js"
    - "Node.js" matches "Node", "NodeJS"
    - "JavaScript" matches "JS"
    - "Python" matches "Python3"

    Returns: True if skills match, False otherwise
    """
    resume_lower = resume_skill.lower().strip()
    job_lower = job_skill.lower().strip()

    # Exact match
    if resume_lower == job_lower:
        return True

    # Direct substring match (bidirectional)
    if resume_lower in job_lower or job_lower in resume_lower:
        return True

    # Common skill variations (normalized matching)
    skill_variations = {
        'javascript': ['js', 'javascript', 'ecmascript'],
        'typescript': ['ts', 'typescript'],
        'react': ['react', 'reactjs', 'react.js'],
        'node.js': ['node', 'nodejs', 'node.js'],
        'vue': ['vue', 'vuejs', 'vue.js'],
        'angular': ['angular', 'angularjs', 'angular.js'],
        'python': ['python', 'python3', 'py'],
        'c++': ['c++', 'cpp', 'cplusplus'],
        'c#': ['c#', 'csharp'],
        'sql': ['sql', 'mysql', 'postgresql', 'postgres'],
        'aws': ['aws', 'amazon web services'],
        'gcp': ['gcp', 'google cloud'],
        'azure': ['azure', 'microsoft azure'],
        'docker': ['docker', 'containerization'],
        'kubernetes': ['kubernetes', 'k8s'],
    }

    # Check if either skill is in a variation group
    for canonical, variations in skill_variations.items():
        if resume_lower in variations and job_lower in variations:
            return True

    return False


def simple_keyword_scoring(job, resume_skills, resume_text=""):
    """
    Improved keyword-based scoring with fuzzy matching and stricter filtering.

    Scoring breakdown:
    - 85% from required_skills matches (primary signal)
    - 10% from bonus skills in title
    - 5% from role type alignment

    Key improvements:
    - Uses fuzzy matching for skill variations
    - Only scores based on required_skills (not random description mentions)
    - Returns 0 if no required skills match
    - Better handles skill variations (React vs ReactJS)
    """
    import re

    score = 0
    matched_skills = []
    skill_match_count = 0

    # Get job details
    job_skills = job.get('required_skills', [])
    job_title = job.get('title', '').lower()
    job_description = job.get('description', '').lower()

    # 1. Required Skills Matching (85 points max) - PRIMARY SIGNAL
    if job_skills and resume_skills:
        for job_skill in job_skills:
            for resume_skill in resume_skills:
                if fuzzy_skill_match(resume_skill, job_skill):
                    skill_match_count += 1
                    matched_skills.append(job_skill)
                    break

        # Calculate percentage of required skills matched
        if len(job_skills) > 0:
            skill_coverage = skill_match_count / len(job_skills)

            # Progressive scoring with diminishing returns
            if skill_coverage >= 0.8:  # 80%+ coverage
                score += 85
            elif skill_coverage >= 0.6:  # 60-79% coverage
                score += int(skill_coverage * 85)
            elif skill_coverage >= 0.4:  # 40-59% coverage
                score += int(skill_coverage * 70)
            elif skill_coverage >= 0.2:  # 20-39% coverage
                score += int(skill_coverage * 50)
            else:  # < 20% coverage
                score += int(skill_coverage * 30)

    # CRITICAL: If zero required skills matched, return 0 immediately
    # This prevents irrelevant jobs from appearing (e.g., C++ jobs for JS developers)
    if skill_match_count == 0 and job_skills:
        return 0

    # 2. Title bonus (10 points max) - Only if we have skill matches
    # Rewards when matched skills appear prominently in the title
    title_bonus = 0
    for matched_skill in matched_skills:
        pattern = r'\b' + re.escape(matched_skill.lower()) + r'\b'
        if re.search(pattern, job_title):
            title_bonus += 3
    score += min(title_bonus, 10)

    # 3. Role type alignment (5 points) - Contextual bonus
    # Check if resume skills align with common role patterns
    role_patterns = {
        'frontend': ['react', 'vue', 'angular', 'javascript', 'typescript', 'html', 'css'],
        'backend': ['node.js', 'python', 'java', 'spring', 'django', 'flask', 'sql'],
        'fullstack': ['react', 'node.js', 'javascript', 'typescript', 'sql'],
        'data': ['python', 'pandas', 'numpy', 'tensorflow', 'pytorch', 'sql'],
        'mobile': ['react native', 'flutter', 'swift', 'kotlin', 'ios', 'android'],
        'devops': ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'ci/cd'],
    }

    resume_skills_lower = [s.lower() for s in resume_skills]
    for role_type, role_skills in role_patterns.items():
        if role_type in job_title:
            # Check if candidate has relevant skills for this role type
            role_skill_matches = sum(1 for rs in resume_skills_lower if any(fuzzy_skill_match(rs, role_skill) for role_skill in role_skills))
            if role_skill_matches >= 2:
                score += 5
                break

    # Cap at 100
    return min(int(score), 100)


def create_keyword_match_description(job, score, matched_skills_count, total_required_skills):
    """
    Generate helpful match descriptions for keyword-based matches.
    """
    company = job.get('company', 'Unknown Company')
    title = job.get('title', 'Unknown Position')
    location = job.get('location', 'Location not specified')

    # Create opening based on score
    if score >= 80:
        opening = f"🎯 **{company}** - Strong keyword match! This {title} position aligns well with your skills."
    elif score >= 60:
        opening = f"✅ **{company}** - Good match. This {title} role shows solid alignment."
    elif score >= 40:
        opening = f"⚠️ **{company}** - Moderate match. This {title} position has some alignment."
    else:
        opening = f"📊 **{company}** - Partial match. This {title} role has limited alignment."

    # Add skill coverage info
    if total_required_skills > 0:
        coverage_pct = int((matched_skills_count / total_required_skills) * 100)
        skill_info = f"\n\n**📋 Skill Coverage:** You match {matched_skills_count} of {total_required_skills} required skills ({coverage_pct}%)"
    else:
        skill_info = "\n\n**📋 Skill Coverage:** Job requirements not specified"

    # Add location
    location_section = f"\n\n**📍 Location:** {location}"

    # Add score with recommendation
    score_section = f"\n\n**🎯 Match Score: {score}/100**"
    if score >= 70:
        score_section += " - **Recommended**"
    elif score >= 40:
        score_section += " - **Consider Applying**"
    else:
        score_section += " - **May Be a Stretch**"

    # Add note about quick mode
    note = "\n\n*Quick Match Mode - For deeper analysis, enable 'Think Deeper'*"

    return opening + skill_info + location_section + score_section + note


def simple_keyword_match(resume_skills, jobs, resume_text="", progress_callback=None):
    """
    Improved fast keyword-based matching with better descriptions.
    Used when LLM is disabled or unavailable.

    Key improvements:
    - Analyzes ALL jobs (no pre-filtering) since regex is fast
    - Uses fuzzy skill matching for accuracy
    - Generates helpful match descriptions
    - Returns top 100 results (increased from 50)

    Returns jobs with keyword match scores and descriptions.
    """
    matched_jobs = []

    # Send progress: Starting keyword matching
    if progress_callback:
        progress_callback("Matching jobs with keyword analysis...")

    print(f"🔍 Quick Mode: Analyzing {len(jobs)} jobs with keyword matching...")

    for job in jobs:
        score = simple_keyword_scoring(job, resume_skills, resume_text)

        # Only include jobs with some relevance (score > 0)
        if score > 0:
            job_copy = job.copy()
            job_copy['match_score'] = score

            # Count matched skills for description
            job_skills = job.get('required_skills', [])
            matched_count = 0
            if job_skills and resume_skills:
                for job_skill in job_skills:
                    for resume_skill in resume_skills:
                        if fuzzy_skill_match(resume_skill, job_skill):
                            matched_count += 1
                            break

            # Generate rich description
            job_copy['match_description'] = create_keyword_match_description(
                job, score, matched_count, len(job_skills)
            )

            job_copy['ai_reasoning'] = None  # No AI analysis in keyword mode
            matched_jobs.append(job_copy)

    # Sort by score descending
    matched_jobs.sort(key=lambda x: x['match_score'], reverse=True)

    print(f"✅ Quick Mode: Found {len(matched_jobs)} matching jobs")

    # Return top 100 results (analyze more jobs since it's fast)
    return matched_jobs[:100]


def _extract_resume_profile_haiku(resume_text: str) -> dict:
    """Uses Claude Haiku to quickly extract skills and experience level for accurate pre-filtering."""
    system_prompt = (
        "Extract the candidate's skills and experience level from the resume. "
        "Return ONLY valid JSON: "
        '{"skills": ["skill1", "skill2"], "experience_level": "student|entry_level|experienced", "years_of_experience": 0}'
    )
    user_prompt = f"RESUME:\n{resume_text[:3000]}"
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        raw = extract_json_from_response(response.content[0].text)
        return json.loads(raw)
    except Exception as e:
        print(f"❌ Haiku extraction failed: {e}")
        return {"skills": [], "experience_level": "student", "years_of_experience": 0}


def _prefilter_jobs_with_profile(profile: dict, jobs: List[Dict], target_count: int = 30) -> List[Dict]:
    """Accurate pre-filtering using Haiku-extracted profile and skill overlap scoring."""
    is_student = profile.get('experience_level') == 'student'
    years_experience = profile.get('years_of_experience', 0)
    resume_skills = [str(s).lower() for s in profile.get('skills', [])]
    
    scored_jobs = []
    for job in jobs:
        title = job.get('title', '').lower()
        desc = job.get('description', '').lower()

        # Filter out senior roles for juniors
        if is_student or years_experience < 3:
            if any(kw in title for kw in ['senior', 'lead', 'principal', 'staff', 'architect', 'manager', 'director']):
                continue

        # Filter out high experience requirements
        skip = False
        for match in re.findall(r'(\d+)\+?\s*years?\s*(?:of\s+)?experience', desc):
            if int(match) >= 5 and years_experience < 3:
                skip = True
                break
        if skip:
            continue

        # Calculate simple skill overlap
        overlap = 0
        job_skills = job.get('required_skills', [])
        for js in job_skills:
            js_lower = str(js).lower()
            if any(fuzzy_skill_match(rs, js_lower) for rs in resume_skills):
                overlap += 1
                
        scored_jobs.append((overlap, job))
        
    # Sort by overlap descending
    scored_jobs.sort(key=lambda x: x[0], reverse=True)
    return [job for _, job in scored_jobs][:target_count]


def analyze_and_match_single_call(resume_text: str, jobs: List[Dict], progress_callback=None):
    """
    Combined resume analysis + job matching in a SINGLE Claude Sonnet call.
    Uses Haiku for pre-filtering and XML prompting to prevent attention dilution.

    Returns: (skills, metadata, enhanced_jobs)
      - skills: list of skill strings
      - metadata: dict with experience_level, years_of_experience, is_student
      - enhanced_jobs: list of job dicts with match_score and ai_reasoning
    """
    if not resume_text.strip():
        return [], {}, []

    if progress_callback:
        progress_callback("Extracting profile with AI...")

    profile = _extract_resume_profile_haiku(resume_text)

    if progress_callback:
        progress_callback("Pre-filtering top candidates for you...")

    candidate_jobs = _prefilter_jobs_with_profile(profile, jobs, target_count=30)
    if not candidate_jobs:
        candidate_jobs = jobs[:15]  # Fallback: just take first 15

    if progress_callback:
        progress_callback("Analyzing resume with AI...")

    # Build XML compact job summaries to fix attention dilution
    jobs_xml = "<job_listings>\n"
    for i, job in enumerate(candidate_jobs):
        jobs_xml += f'  <job id="{i + 1}">\n'
        jobs_xml += f"    <company>{job.get('company', 'Unknown')}</company>\n"
        jobs_xml += f"    <title>{job.get('title', 'Unknown')}</title>\n"
        jobs_xml += f"    <location>{job.get('location', 'Unknown')}</location>\n"
        
        desc = job.get('description', '')[:400]
        # Escape XML to prevent breaking parsing
        desc = desc.replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        jobs_xml += f"    <description>{desc}</description>\n"
        jobs_xml += "  </job>\n"
    jobs_xml += "</job_listings>"

    system_prompt = (
        "You are an expert technical recruiter. Given a resume and XML job listings, "
        "score each job based on how well the candidate fits.\n\n"
        "SCORING (0-100):\n"
        "- 35% Project depth & real-world impact (production deployments, user metrics, measurable results)\n"
        "- 25% Work experience quality (internships/jobs > academic projects)\n"
        "- 20% Skill alignment with the specific role\n"
        "- 15% Experience level appropriateness (senior roles for juniors = 0)\n"
        "- 5%  Career trajectory fit\n\n"
        "Penalize keyword-stuffed resumes with no substance. Reward demonstrated impact.\n\n"
        "Return ONLY valid JSON, no markdown, no extra text:\n"
        "{\n"
        '  "job_scores": [\n'
        '    {"job_id": 1, "match_score": 85, "reasoning": "brief reason", '
        '"skill_matches": ["Python"], "skill_gaps": ["Kubernetes"]}\n'
        "  ]\n"
        "}"
    )

    user_prompt = (
        f"RESUME:\n{resume_text[:3000]}\n\n"
        f"JOBS TO ANALYZE ({len(candidate_jobs)} positions):\n"
        f"{jobs_xml}\n\n"
        f"Analyze the resume and score all {len(candidate_jobs)} jobs. Return JSON only."
    )

    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = extract_json_from_response(response.content[0].text)
        result = json.loads(raw)
    except Exception as e:
        print(f"❌ Combined LLM call failed: {e}")
        # Fallback: keyword match with extracted skills
        return profile.get('skills', []), profile, simple_keyword_match(profile.get('skills', []), jobs, resume_text, progress_callback=progress_callback)

    skills = profile.get("skills", [])
    metadata = {
        "experience_level": profile.get("experience_level", "student"),
        "years_of_experience": profile.get("years_of_experience", 0),
        "is_student": profile.get("is_student", profile.get("experience_level") == "student"),
    }

    if progress_callback:
        progress_callback("Enhancing results with career insights...")

    job_scores = result.get("job_scores", [])
    enhanced_jobs = enhance_batch_results(job_scores, candidate_jobs, skills)

    return skills, metadata, enhanced_jobs


def match_resume_to_jobs(resume_skills, jobs, resume_text="", use_llm=True, progress_callback=None):
    """
    Intelligent job matching system with optional LLM analysis.

    Args:
        resume_skills: List of candidate skills
        jobs: List of job postings to match against
        resume_text: Full resume text for context
        use_llm: If True, uses AI analysis. If False, uses keyword matching.
        progress_callback: Optional callback function to report progress (takes message string)

    Returns:
        List of matched jobs with scores and descriptions

    Modes:
        - LLM Mode (use_llm=True): 3-stage intelligent matching with AI career analysis
        - Keyword Mode (use_llm=False): Fast keyword-based scoring
        - Fallback: Automatically falls back to keyword if LLM fails
    """
    if not jobs:
        return []

    # If LLM disabled, use keyword matching directly
    if not use_llm:
        return simple_keyword_match(resume_skills, jobs, resume_text, progress_callback=progress_callback)

    # Extract resume metadata for filtering
    resume_metadata = {
        'experience_level': extract_user_experience_level(resume_skills, resume_text),
        'years_of_experience': 0,
        'is_student': True
    }

    # Try LLM matching with automatic fallback
    try:
        # STAGE 1: Intelligent Pre-filtering
        filtered_jobs = intelligent_prefilter_jobs(jobs, resume_skills, resume_metadata, target_count=30, progress_callback=progress_callback)

        if not filtered_jobs:
            # No jobs passed pre-filtering, fall back to keyword on all jobs
            return simple_keyword_match(resume_skills, jobs, resume_text, progress_callback=progress_callback)

        # STAGE 2: Batch LLM Analysis
        llm_scores = batch_analyze_jobs_with_llm(filtered_jobs, resume_skills, resume_text, resume_metadata, progress_callback=progress_callback)

        if not llm_scores:
            # LLM returned no scores, fall back to keyword
            return simple_keyword_match(resume_skills, jobs, resume_text, progress_callback=progress_callback)

        # STAGE 3: Enhanced Results Processing
        if progress_callback:
            progress_callback("Enhancing results with career insights...")

        enhanced_jobs = enhance_batch_results(llm_scores, filtered_jobs, resume_skills)

        return enhanced_jobs

    except Exception:
        # LLM matching failed, automatically fall back to keyword matching
        return simple_keyword_match(resume_skills, jobs, resume_text, progress_callback=progress_callback)


 