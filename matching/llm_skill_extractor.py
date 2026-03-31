"""
LLM-based skill extraction for job descriptions.
This replaces all hardcoded skill lists with dynamic, AI-powered extraction.
"""

import difflib
import logging
import os
import json
import hashlib
from dotenv import load_dotenv
import anthropic
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# ---------------------------------------------------------------------------
# Known skill synonyms (normalized → canonical). Score 1.0 on match.
# ---------------------------------------------------------------------------
_SYNONYMS: Dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "node": "node.js",
    "nodejs": "node.js",
    "postgres": "postgresql",
    "psql": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "py": "python",
    "python3": "python",
    "tf": "tensorflow",
    "torch": "pytorch",
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "dl": "deep learning",
    "gcp": "google cloud platform",
    "aws": "amazon web services",
    "azure": "microsoft azure",
    "reactjs": "react",
    "react.js": "react",
    "vuejs": "vue",
    "vue.js": "vue",
    "angularjs": "angular",
    "expressjs": "express",
    "express.js": "express",
    "cpp": "c++",
    "c sharp": "c#",
    "golang": "go",
    "rb": "ruby",
    "ror": "ruby on rails",
    "mysql": "mysql",
}

def extract_json_from_response(text: str) -> str:
    """Extract JSON from Claude response, handling markdown code blocks."""
    # Remove markdown code blocks if present
    if "```json" in text:
        # Extract content between ```json and ```
        start = text.find("```json") + 7
        end = text.find("```", start)
        return text[start:end].strip()
    elif "```" in text:
        # Extract content between ``` and ```
        start = text.find("```") + 3
        end = text.find("```", start)
        return text[start:end].strip()
    # Return as-is if no code blocks
    return text.strip()

# Simple in-memory cache for job skills to avoid re-processing
_job_skills_cache = {}

def _db_get_job_skills(cache_key: str):
    """Check DB for previously persisted LLM job-skill extraction."""
    try:
        from job_database import get_db, close_db, CacheMetadata
        db = get_db()
        try:
            entry = db.query(CacheMetadata).filter(
                CacheMetadata.cache_type == f"job_skills_{cache_key}"
            ).first()
            if entry and entry.cache_metadata:
                data = json.loads(entry.cache_metadata)
                return data.get("skills")
        finally:
            close_db(db)
    except Exception as e:
        logger.warning(f"DB job-skills cache read failed: {e}")
    return None

def _db_set_job_skills(cache_key: str, skills: List[str]) -> None:
    """Persist LLM job-skill extraction to DB."""
    try:
        from job_database import get_db, close_db, CacheMetadata
        from datetime import datetime
        db = get_db()
        try:
            db.query(CacheMetadata).filter(
                CacheMetadata.cache_type == f"job_skills_{cache_key}"
            ).delete()
            entry = CacheMetadata(
                cache_type=f"job_skills_{cache_key}",
                job_count=0,
                new_jobs_added=0,
                status="success",
                cache_metadata=json.dumps({"skills": skills}),
            )
            db.add(entry)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            close_db(db)
    except Exception as e:
        logger.warning(f"DB job-skills cache write failed: {e}")

def extract_job_skills_with_llm(job_title: str, job_description: str, company: str = "") -> List[str]:
    """
    Use GPT-5 to dynamically extract required skills from job postings.
    This replaces all hardcoded skill lists with intelligent extraction.
    Includes caching to prevent timeouts.
    """
    # Create cache key from job content
    cache_key = hashlib.md5(f"{job_title}{job_description}{company}".encode()).hexdigest()

    # Check in-memory cache first
    if cache_key in _job_skills_cache:
        return _job_skills_cache[cache_key]

    # Check DB cache before calling LLM
    db_skills = _db_get_job_skills(cache_key)
    if db_skills is not None:
        _job_skills_cache[cache_key] = db_skills
        return db_skills

    # If job description is too short, raise error
    if len(job_description.strip()) < 50:
        raise Exception(f"Job description too short (<50 chars) for: {job_title}")

    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

        prompt = f"""You are an expert job requirements analyzer. Analyze this internship role and extract the SPECIFIC technical skills required.

CRITICAL INSTRUCTIONS:
1. PAY CLOSE ATTENTION to the job title - it reveals the role's focus (Frontend, Backend, Mobile, Data, Security, etc.)
2. If the job title mentions specific technologies (e.g., "React", "Python", "AWS"), ALWAYS include them
3. Infer role-specific skills based on the job title:
   - Frontend/Front-End → JavaScript, React/Angular/Vue, HTML, CSS, TypeScript
   - Backend/Back-End → Python/Java/Go, SQL, API Development, Microservices
   - Full Stack → JavaScript, Python/Java, SQL, React, Backend, Frontend
   - Mobile → Swift, Kotlin, Java, Mobile Development, iOS/Android
   - Data Scientist/Analyst → Python, SQL, Data Analysis, Machine Learning, Statistics
   - Data Engineer → Python, SQL, ETL, Data Pipelines, Spark
   - DevOps/Cloud → AWS/Azure/GCP, Docker, Kubernetes, CI/CD, Terraform
   - Security/Cybersecurity → Security, Cryptography, Network Security, Python
   - ML/AI → Python, Machine Learning, TensorFlow/PyTorch, Deep Learning
   - QA/Test → Testing, Automation, Selenium, Python/Java
4. Extract any specific technologies mentioned in the description
5. Return 5-8 concrete, specific skills (not generic terms like "programming")

Return ONLY valid JSON in this exact format (no markdown, no code blocks):
{{
    "required_skills": ["skill1", "skill2", "skill3", ...],
    "role_type": "frontend/backend/fullstack/mobile/data/security/devops/general",
    "confidence": "high/medium/low"
}}

Job Information:
Company: {company}
Title: {job_title}
Description: {job_description}"""

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=800,
            system="You are a technical recruiter who understands what skills are needed for different software engineering roles. You infer specific technical requirements from job titles and descriptions. Always return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)

        # Get required skills
        all_skills = result.get("required_skills", [])

        # Cache the result in memory and DB
        _job_skills_cache[cache_key] = all_skills
        _db_set_job_skills(cache_key, all_skills)

        return all_skills
        
    except Exception as e:
        logger.error(f"Error with LLM job skill extraction: {e}")
        raise Exception(f"LLM job skill extraction failed: {str(e)}")



def calculate_skill_similarity(skill1: str, skill2: str) -> float:
    """
    Calculate similarity between two skills using pure Python — no LLM calls.
    Hierarchy: exact match → synonym dict → substring containment → difflib ratio.
    """
    s1 = skill1.lower().strip()
    s2 = skill2.lower().strip()

    # 1. Exact match
    if s1 == s2:
        return 1.0

    # 2. Synonym normalisation — if both resolve to the same canonical name
    c1 = _SYNONYMS.get(s1, s1)
    c2 = _SYNONYMS.get(s2, s2)
    if c1 == c2:
        return 1.0

    # 3. Substring containment
    if s1 in s2 or s2 in s1:
        return 0.85

    # 4. difflib ratio as fallback
    return difflib.SequenceMatcher(None, s1, s2).ratio()

def match_skills_dynamically(job_skills: List[str], resume_skills: List[str], threshold: float = 0.7) -> List[Dict[str, Any]]:
    """
    Match job skills to resume skills using exact matching only.
    No fuzzy matching, no hardcoded synonyms - only exact string matches.
    """
    matches = []

    # Only exact matching
    for job_skill in job_skills:
        for resume_skill in resume_skills:
            # Exact match (case-insensitive)
            if job_skill.lower().strip() == resume_skill.lower().strip():
                matches.append({
                    "job_skill": job_skill,
                    "resume_skill": resume_skill,
                    "similarity_score": 1.0
                })
                break  # Only match once per job skill

    return matches


def extract_job_metadata_with_llm(job_title: str, job_description: str, company: str = "") -> Dict[str, Any]:
    """
    Extract job metadata (experience level, location preferences, etc.) using LLM.
    """
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

        prompt = f"""Analyze this job posting and extract key metadata for matching purposes.

EXTRACT THE FOLLOWING:
1. Experience level required (entry_level, mid_level, senior_level, student/intern)
2. Years of experience required (if mentioned)
3. Education requirements (if any)
4. Work arrangement (remote, hybrid, on-site, flexible)
5. Job type (internship, full-time, part-time, contract)
6. Industry/domain focus
7. Team size or company size hints
8. Urgency indicators

Return ONLY valid JSON (no markdown, no code blocks):
{{
    "experience_level": "entry_level",
    "years_required": 2,
    "education_requirements": ["Bachelor's degree"],
    "work_arrangement": "hybrid",
    "job_type": "internship",
    "industry": "technology",
    "urgency": "high",
    "team_size": "small",
    "extraction_confidence": "high"
}}

Job Information:
Company: {company}
Title: {job_title}
Description: {job_description}"""

        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=500,
            system="You are a job posting analyzer that extracts metadata for matching purposes. Always return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)
        return result
        
    except Exception as e:
        logger.error(f"Error extracting job metadata: {e}")
        return {
            "experience_level": "entry_level",  # Default for internships
            "years_required": 0,
            "work_arrangement": "unknown",
            "job_type": "internship",
            "extraction_confidence": "low"
        }

# Simple in-memory cache for candidate profiles
_candidate_profile_cache = {}

def _db_get_candidate_profile(cache_key: str):
    """Check DB for a persisted candidate profile analysis (stored in ResumeCache.skills JSON)."""
    try:
        from job_database import get_db, close_db, ResumeCache
        from datetime import datetime
        db = get_db()
        try:
            entry = db.query(ResumeCache).filter(
                ResumeCache.user_id == "__profile__",
                ResumeCache.resume_hash == cache_key,
                ResumeCache.expires_at > datetime.utcnow(),
            ).first()
            if entry and entry.skills:
                data = json.loads(entry.skills)
                profile = data.get("__profile__")
                return profile
        finally:
            close_db(db)
    except Exception as e:
        logger.warning(f"DB candidate-profile cache read failed: {e}")
    return None

def _db_set_candidate_profile(cache_key: str, profile: Dict[str, Any]) -> None:
    """Persist candidate profile analysis to DB via ResumeCache."""
    try:
        from job_database import get_db, close_db, ResumeCache
        from datetime import datetime, timedelta
        db = get_db()
        try:
            db.query(ResumeCache).filter(
                ResumeCache.user_id == "__profile__",
                ResumeCache.resume_hash == cache_key,
            ).delete()
            entry = ResumeCache(
                user_id="__profile__",
                resume_hash=cache_key,
                results=json.dumps([]),
                skills=json.dumps({"__profile__": profile}),
                expires_at=datetime.utcnow() + timedelta(hours=24),
            )
            db.add(entry)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            close_db(db)
    except Exception as e:
        logger.warning(f"DB candidate-profile cache write failed: {e}")

def analyze_candidate_profile_with_llm(resume_skills: List[str], resume_text: str = "") -> Dict[str, Any]:
    """
    Analyze candidate profile once and cache the result for the session.
    This replaces repeated analysis for each job matching.
    """
    # Create cache key from resume content
    cache_key = hashlib.md5(f"{str(resume_skills)}{resume_text}".encode()).hexdigest()

    # Check in-memory cache first
    if cache_key in _candidate_profile_cache:
        return _candidate_profile_cache[cache_key]

    # Check DB cache before calling LLM
    db_profile = _db_get_candidate_profile(cache_key)
    if db_profile is not None:
        _candidate_profile_cache[cache_key] = db_profile
        return db_profile

    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

        prompt = f"""Analyze this candidate's profile and create a comprehensive summary for job matching.

CANDIDATE INFORMATION:
Skills: {resume_skills}
Resume Text: {resume_text}

ANALYZE AND EXTRACT:
1. Top 8-10 strongest technical skills (prioritized by proficiency/relevance)
2. Experience level (student, recent_graduate, entry_level, experienced)
3. Career interests and direction (frontend, backend, fullstack, data, mobile, etc.)
4. Learning style and adaptability indicators
5. Leadership/collaboration potential
6. Industry preferences (if any)
7. Work style preferences (startup vs big tech, remote vs office, etc.)
8. Growth potential and trajectory

Return ONLY valid JSON (no markdown, no code blocks):
{{
    "top_skills": ["Python", "React", "SQL", "JavaScript", "Git"],
    "experience_level": "student",
    "career_direction": "fullstack",
    "specialization_areas": ["web development", "backend apis"],
    "learning_indicators": "strong self-learner, enjoys new technologies",
    "leadership_potential": "medium",
    "adaptability_score": "high",
    "preferred_industries": ["technology", "startups"],
    "work_style": "collaborative, prefers hands-on learning",
    "growth_trajectory": "rapid learner with strong fundamentals",
    "confidence_level": "high"
}}"""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=800,
            system="You are an expert career counselor and technical recruiter who understands candidate potential and job fit. Always return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)
        
        logger.info(f"Candidate profile: {result.get('experience_level')} {result.get('career_direction')} developer")

        # Cache in memory and DB
        _candidate_profile_cache[cache_key] = result
        _db_set_candidate_profile(cache_key, result)

        return result
        
    except Exception as e:
        logger.error(f"Error analyzing candidate profile: {e}")
        # Fallback to basic analysis
        return {
            "top_skills": resume_skills[:8],
            "experience_level": "student",
            "career_direction": "general",
            "confidence_level": "low"
        }

def llm_deep_ranking(candidate_profile: Dict[str, Any], top_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Use LLM to intelligently rank the top 30 jobs and return the best 10.
    This replaces mechanical scoring with intelligent compatibility analysis.
    """
    if not top_jobs:
        return []
    
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

        # Prepare candidate summary
        candidate_summary = f"""Experience Level: {candidate_profile.get('experience_level', 'unknown')}
Career Direction: {candidate_profile.get('career_direction', 'general')}
Top Skills: {', '.join(candidate_profile.get('top_skills', []))}
Specializations: {', '.join(candidate_profile.get('specialization_areas', []))}
Learning Style: {candidate_profile.get('learning_indicators', 'adaptable')}
Growth Potential: {candidate_profile.get('growth_trajectory', 'steady learner')}"""

        # Prepare job summaries
        job_summaries = []
        for i, job in enumerate(top_jobs, 1):
            job_summary = f"{i}. {job.get('company', 'Unknown')} - {job.get('title', 'Unknown')}"
            if job.get('required_skills'):
                job_summary += f" | Skills: {', '.join(job.get('required_skills', [])[:5])}"
            if job.get('location'):
                job_summary += f" | Location: {job.get('location', 'N/A')}"
            job_summaries.append(job_summary)

        prompt = f"""You are an expert career counselor. Analyze this candidate and rank these job opportunities for the BEST CAREER FIT.

CANDIDATE PROFILE:
{candidate_summary}

JOB OPPORTUNITIES:
{chr(10).join(job_summaries)}

RANKING CRITERIA:
1. Skill alignment and transferability
2. Growth and learning opportunities
3. Career trajectory fit
4. Company culture compatibility
5. Role progression potential
6. Learning curve appropriateness
7. Long-term career impact

Return ONLY valid JSON (no markdown, no code blocks) with top 10 jobs ranked by best fit:
{{
    "rankings": [
        {{
            "job_index": 1,
            "compatibility_score": 95,
            "reasoning": "Perfect skill match with excellent growth opportunities",
            "growth_potential": "high",
            "skill_development": "React, advanced JS patterns",
            "career_impact": "strong foundation for fullstack career"
        }},
        ...
    ],
    "overall_analysis": "This candidate shows strong potential for frontend development roles..."
}}

Focus on COMPATIBILITY and GROWTH, not just skill matching."""

        response = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1500,
            system="You are a senior career counselor and technical recruiter with deep understanding of career development and job fit. Always return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)
        rankings = result.get("rankings", [])
        
        logger.info(f"LLM deep ranking completed: {len(rankings)} jobs ranked")
        
        # Map rankings back to job objects with enhanced descriptions
        ranked_jobs = []
        for ranking in rankings[:10]:  # Top 10 only
            job_index = ranking.get("job_index", 1) - 1  # Convert to 0-based index
            
            if 0 <= job_index < len(top_jobs):
                job = top_jobs[job_index].copy()
                
                # Enhanced match description using LLM reasoning (frontend-friendly format)
                enhanced_description = f"🎯 Compatibility Score: {ranking.get('compatibility_score', 0)}/100\n\n✨ Why This Role Fits You:\n{ranking.get('reasoning', 'Good skill alignment')}\n\n🚀 Growth Opportunities:\n• Skill Development: {ranking.get('skill_development', 'Various technical skills')}\n• Career Impact: {ranking.get('career_impact', 'Valuable experience')}\n• Growth Potential: {ranking.get('growth_potential', 'Good')}\n\n📍 Location: {job.get('location', 'Not specified')}"
                
                job['match_score'] = ranking.get('compatibility_score', 0)
                job['match_description'] = enhanced_description.strip()
                ranked_jobs.append(job)
        
        logger.info(f"Returning {len(ranked_jobs)} intelligently ranked jobs")
        return ranked_jobs

    except Exception as e:
        logger.error(f"Error in LLM deep ranking: {e} — falling back to score-based ranking")
        
        # Fallback: return jobs sorted by their existing match scores
        return sorted(top_jobs, key=lambda x: x.get('match_score', 0), reverse=True)[:10]
