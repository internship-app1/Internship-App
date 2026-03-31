import logging
import pdfplumber
import re
import os
import io
import json
import anthropic
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

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

# Static system prompt for resume analysis (cached across calls)
RESUME_ANALYSIS_SYSTEM_PROMPT = """You are an expert resume analyzer. Your task is to extract ONLY the technical and professional skills that this person actually possesses based on their resume content.

CRITICAL INSTRUCTIONS:
1. ONLY extract skills the person actually has experience with or claims to know
2. DO NOT extract skills mentioned in negative contexts (e.g., "I have never used Python", "I want to learn React")
3. DO NOT extract skills from job descriptions they're applying to
4. DO NOT extract skills from courses they want to take in the future
5. Focus on concrete evidence: work experience, projects, education, certifications
6. USE STANDARD SKILL NAMES (e.g., "JavaScript" not "JS", "Python" not "Python3", "Machine Learning" not "ML")
7. PRIORITIZE skills with demonstrated project/work experience over just "familiar with"
8. BE CONSERVATIVE - it's better to extract 5-8 strong skills than 20 weak ones

SKILL CATEGORIES TO EXTRACT:
- Programming Languages: Python, Java, JavaScript, TypeScript, C++, C#, Go, Rust, PHP, Ruby, etc.
- Web Technologies: React, Angular, Vue, HTML, CSS, Node.js, Express, Django, Flask, etc.
- Databases: SQL, MySQL, PostgreSQL, MongoDB, Redis, etc.
- Cloud Platforms: AWS, Azure, GCP, Docker, Kubernetes, etc.
- Tools & Frameworks: Git, TensorFlow, PyTorch, Pandas, NumPy, etc.
- Soft Skills: Leadership, Communication, Project Management, Teamwork, etc.
- Domain Knowledge: Machine Learning, Data Analysis, Software Engineering, etc.

STANDARDIZATION RULES:
- Use "JavaScript" instead of "JS"
- Use "TypeScript" instead of "TS"
- Use "Python" instead of "Python3" or "Py"
- Use "Machine Learning" instead of "ML"
- Use "Artificial Intelligence" instead of "AI"
- Use "SQL" for general database skills
- Use specific database names when mentioned (MySQL, PostgreSQL, etc.)
- Use "Git" for version control
- Use full framework names (React, Angular, Vue, etc.)

Please analyze the user's resume text provided in the next message.
Return your response as a JSON object with this exact structure:
{
    "skills": [
        "skill1",
        "skill2",
        "skill3"
    ],
    "experience_level": "student/recent_graduate/entry_level/experienced",
    "years_of_experience": 0,
    "is_student": true/false,
    "confidence_notes": "Brief explanation of your extraction approach"
}
"""

def extract_skills_with_llm(resume_text: str) -> List[str]:
    """
    Use Claude to extract skills from resume text with context awareness.
    Returns a list of skills that the person actually possesses.
    """
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=RESUME_ANALYSIS_SYSTEM_PROMPT + " Always return valid JSON only.",
            messages=[
                {"role": "user", "content": resume_text}
            ]
        )

        # Parse the JSON response
        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)
        skills = result.get("skills", [])
        experience_level = result.get("experience_level", "student")
        years = result.get("years_of_experience", 0)
        is_student = result.get("is_student", True)
        
        logger.info(f"LLM extracted {len(skills)} skills — {experience_level} ({years}yr), student={is_student}")

        return skills

    except Exception as e:
        logger.error(f"Error with LLM skill extraction: {e}")
        # Re-raise the exception to be handled by the calling function
        raise Exception(f"LLM skill extraction failed: {str(e)}")



def parse_resume(file_content, filename, use_llm=True, progress_callback=None):
    """
    Parse resume from file content and extract skills using LLM.
    Args:
        file_content: The file content to parse
        filename: The filename for file type detection
        use_llm: DEPRECATED - always uses LLM now, kept for backward compatibility
        progress_callback: Optional callback function to report progress (takes message string)
    Returns tuple: (skills_list, resume_text, metadata_dict)
    """
    ext = os.path.splitext(filename)[1].lower() if filename else ''
    text = ""

    # Send progress: Starting text extraction
    if progress_callback:
        progress_callback("Extracting text from resume...")

    if ext in [".png", ".jpg", ".jpeg"]:
        try:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.warning(f"Error processing image: {e}")
            text = ""
    else:
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
        except Exception as e:
            logger.warning(f"Error processing PDF: {e}")
            text = ""

    # Check if text was extracted successfully
    if not text.strip():
        logger.warning("No text extracted from resume — cannot perform skill extraction")
        return [], "", {}

    # Send progress: Starting AI analysis
    if progress_callback:
        progress_callback("Analyzing resume with AI...")

    logger.info("Starting LLM-based resume analysis...")

    # LLM extraction with full metadata (NO FALLBACK)
    result = extract_skills_with_llm_full(text)
    skills = result.get("skills", [])
    metadata = {
        "experience_level": result.get("experience_level", "student"),
        "years_of_experience": result.get("years_of_experience", 0),
        "is_student": result.get("is_student", True),
        "confidence_notes": result.get("confidence_notes", "")
    }

    logger.info(f"Extracted {len(skills)} skills — {metadata['experience_level']} ({metadata['years_of_experience']} years)")
    return skills, text, metadata

def extract_text_only(file_content: bytes, filename: str, progress_callback=None) -> str:
    """
    Extract raw text from a resume file without any LLM calls.
    Used as the first step in the combined single-call pipeline.
    Returns the extracted text string (empty string on failure).
    """
    if progress_callback:
        progress_callback("Extracting text from resume...")

    ext = os.path.splitext(filename)[1].lower() if filename else ''
    text = ""

    if ext in [".png", ".jpg", ".jpeg"]:
        try:
            from PIL import Image
            import pytesseract
            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.warning(f"Error processing image: {e}")
    else:
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
        except Exception as e:
            logger.warning(f"Error processing PDF: {e}")

    return text


def extract_skills_with_llm_full(resume_text: str) -> Dict[str, Any]:
    """
    Enhanced version that returns full metadata along with skills.
    This is used by parse_resume() to get complete resume analysis.
    """
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            system=RESUME_ANALYSIS_SYSTEM_PROMPT + " Always return valid JSON only.",
            messages=[
                {"role": "user", "content": resume_text}
            ]
        )

        response_text = extract_json_from_response(response.content[0].text)
        result = json.loads(response_text)
        
        logger.info(f"LLM extracted {len(result.get('skills', []))} skills — {result.get('experience_level', 'unknown')} ({result.get('years_of_experience', 0)}yr)")

        return result

    except Exception as e:
        logger.error(f"Error with LLM skill extraction: {e}")
        raise Exception(f"LLM skill extraction failed: {str(e)}")


def is_valid_resume(text):
    """Check if the text appears to be from a valid resume"""
    if not text or len(text.strip()) < 100:
        return False
    
    # Look for common resume indicators
    resume_indicators = [
        'experience', 'education', 'skills', 'work', 'employment', 
        'university', 'college', 'degree', 'bachelor', 'master', 
        'resume', 'cv', 'curriculum vitae', 'contact', 'email', 
        'phone', 'project', 'intern', 'job', 'position'
    ]
    
    text_lower = text.lower()
    found_indicators = sum(1 for indicator in resume_indicators if indicator in text_lower)
    
    # Require at least 3 resume indicators
    return found_indicators >= 3
