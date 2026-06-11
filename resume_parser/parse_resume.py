import logging
import pdfplumber
import re
import os
import io
import json
import anthropic
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Bounds on resume input to prevent resource-exhaustion via crafted files.
MAX_PDF_PAGES = 15
# Cap decompressed image size to defend against decompression-bomb images.
MAX_IMAGE_PIXELS = 40_000_000  # ~40 MP


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

SKILL COUNT HARD LIMIT:
- Maximum 12 skills total. If you exceed 12, cut the weakest ones.
- The burden of proof is INCLUSION, not exclusion. When uncertain, exclude.
- A skill listed ONLY in a self-reported section = automatic exclusion, no exceptions.

EXAMPLES OF SKILL CATEGORIES TO EXTRACT:
NOTE: ONLY EXTRACT IF PROJECT OR EXPERIENCE BACKS IT UP
- Programming Languages: Python, Java, JavaScript, TypeScript, C++, C#, Go, Rust, PHP, Ruby, etc.
- Web Technologies: React, Angular, Vue, HTML, CSS, Node.js, Express, Django, Flask, etc.
- Databases: SQL, MySQL, PostgreSQL, MongoDB, Redis, etc.
- Cloud Platforms: AWS, Azure, GCP, Docker, Kubernetes, etc.
- Tools & Frameworks: Git, TensorFlow, PyTorch, Pandas, NumPy, etc.
- Domain Knowledge: Machine Learning, Data Analysis, Software Engineering, etc.
- AI Coding Tools: Cursor, Antigravity, Claude code, Codex, Gemini, etc.

SELF-REPORTED SKILL LISTS:
- Treat any dedicated "SKILLS" or "TECHNOLOGIES" section as aspirational unless
  corroborated by a project, job, or course that explicitly uses that technology.
- A skill listed ONLY in a self-reported skills section with no supporting
  project/experience evidence = DO NOT extract it.
- DO NOT infer skills from background assumptions, including:
  - "This CS program likely teaches X"
  - "Students at this level typically know X"
  - "X is commonly required for Y language"
  Every skill must be explicitly mentioned in the resume AND corroborated
  by a specific project, job, or coursework bullet. No exceptions.

STANDARDIZATION RULES:
- Use "JavaScript" instead of "JS"
- Use "TypeScript" instead of "TS"
- Use "Python" instead of "Python3" or "Py"
- Use "Machine Learning" instead of "ML"
- Use "SQL" for general database skills
- Use specific database names when mentioned (MySQL, PostgreSQL, etc.)
- Use "Git" for version control
- Use full framework names (React, Angular, Vue, etc.)

Please analyze the user's resume text provided in the next message.
Return your response as a JSON object with this exact structure:

PROJECT CLASSIFICATION CRITERIA:
Classify each project into exactly one of these standard types:
- "AI/ML (Computer Vision)" - e.g., CNNs, YOLO, OpenCV, object detection, image classification, segmentation.
- "AI/ML (NLP/GenAI)" - e.g., LLMs, RAG, prompt engineering, BERT, text classification, transformers, vector databases (Pinecone, Chroma).
- "AI/ML (Traditional/Analytics)" - e.g., regression, decision trees, scikit-learn, clustering, forecasting, predictive modeling.
- "Data Engineering / ETL" - e.g., data scrapers, ETL pipelines, Spark/Hadoop big data processing, Kafka streams, custom data warehouses.
- "Full-Stack Web App" - REQUIRES both a visible frontend UI layer AND backend logic. e.g., CRUD portals, SaaS products with auth, dashboards with database integrations. Backend-only APIs or microservices with no frontend do NOT qualify.
- "Frontend Only" - e.g., portfolio websites, static landing pages, UI clones, CSS/design-focused projects.
- "Mobile App" - e.g., iOS (Swift/SwiftUI), Android (Kotlin/Java), or cross-platform (Flutter, React Native) applications.
- "System/Infrastructure" - e.g., operating systems (xv6), custom compilers/interpreters, distributed databases, network sockets (C/C++), custom memory allocators, backend-only microservices and APIs with no frontend.
- "Cybersecurity / Blockchain" - e.g., penetration testing scripts, smart contracts (Solidity), cryptography tools, network sniffers, vulnerability scanners.
- "Game Development" - e.g., Unity/C# games, Unreal Engine, Pygame, custom C++ 2D/3D physics engines, VR/AR simulations.
- "Embedded Systems / IoT / Robotics" - e.g., Arduino/Raspberry Pi automation, firmware development, C/C++ hardware drivers, sensor networking, ROS (Robot Operating System). Takes priority over "System/Infrastructure" when the project runs on specific hardware (Arduino, STM32, Raspberry Pi, ARM Cortex).
- "Developer Tool / Automation" - e.g., CLI tools, custom libraries (npm/pip packages), browser extensions, Discord/Slack bots, shell scripting automations.

IMPACT EXTRACTION RULES:
1. Seek concrete evidence of DEPLOYMENT (e.g., keywords like "deployed", "live at", "production environment", "AWS", "Vercel", "App Store", "live link") or even an embedded link to the project works.
2. Capture NUMERICAL METRICS representing:
   - Scale (e.g., "500+ users", "10k requests/sec", "2GB of logs").
   - Speed/Performance (e.g., "reduced latency by 40%", "increased throughput by 2x", "decreased page load time by 1.2s").
   - Financial/Business Value (e.g., "saved $1,200/month in cloud costs", "won $5k hackathon grand prize").
3. DO NOT capture vague claims (e.g., "made it fast") unless accompanied by a concrete action or metric.

{
    "skills": [
        "Python", "C++", "Docker", "React"
    ],
    "experience_level": "student/entry_level/experienced",
    "years_of_experience": 1,
    "is_student": true,
    "confidence_notes": "Extracted computer vision project from university research section.",
    "projects": [
        {
            "name": "Project Name",
            "type": "Select from PROJECT CLASSIFICATION CRITERIA",
            "technologies": ["C++", "ROS", "OpenCV"],
            "is_deployed": true/false,
            "project_complexity": "High/Medium/Low",
            "has_link": true/false,
            "summary": "Brief summary highlighting complexity and outcomes."
        }
    ],
    "impact_highlights": [
        {
            "description": "Full description of accomplishment with context.",
            "metric": "Key measurable metric (e.g. 95% accuracy, 200 users)",
            "dimension": "performance / scale / deployment / speed / business_value"
        }
    ],
    "confidence_metrics": [
        {
            "confidence_level": "high/medium/low",
            "confidence_score": 0.85,
            "confidence_notes": "Brief explanation of your extraction approach"
        }
    ]
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
            max_tokens=2048,
            system=RESUME_ANALYSIS_SYSTEM_PROMPT + " Always return valid JSON only.",
            messages=[
                {"role": "user", "content": resume_text}
            ]
        )

        if response.stop_reason == "max_tokens":
            logger.warning("extract_skills_with_llm hit max_tokens — response likely truncated")
            raise Exception("LLM response cut off at max_tokens; JSON may be incomplete")

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
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.warning(f"Error processing image: {e}")
            text = ""
    else:
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages[:MAX_PDF_PAGES]:
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
        "confidence_notes": result.get("confidence_notes", ""),
        "projects": result.get("projects", []),
        "impact_highlights": result.get("impact_highlights", []),
        "confidence_metrics": result.get("confidence_metrics", [])
    }

    logger.info(f"Extracted {len(skills)} skills — {metadata['experience_level']} ({metadata['years_of_experience']} years)")
    logger.info(f"Extracted {len(metadata['projects'])} projects, {len(metadata['impact_highlights'])} impact highlights, and {len(metadata['confidence_metrics'])} confidence metrics")
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
            Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
            image = Image.open(io.BytesIO(file_content))
            text = pytesseract.image_to_string(image)
        except Exception as e:
            logger.warning(f"Error processing image: {e}")
    else:
        try:
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                for page in pdf.pages[:MAX_PDF_PAGES]:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
        except Exception as e:
            logger.warning(f"Error processing PDF: {e}")

    return text


def extract_skills_with_llm_full(
    resume_text: str,
    system_prompt: str = None,
    temperature: float = None,
) -> Dict[str, Any]:
    """
    Enhanced version that returns full metadata along with skills.
    This is used by parse_resume() to get complete resume analysis.

    Args:
        resume_text: Raw text of the resume.
        system_prompt: Override the system prompt (used by evals; defaults to
            RESUME_ANALYSIS_SYSTEM_PROMPT so production behaviour is unchanged).
        temperature: Override model temperature (used by evals for determinism;
            None = API default, matching current production behaviour).
    """
    if system_prompt is None:
        system_prompt = RESUME_ANALYSIS_SYSTEM_PROMPT
    try:
        client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        create_kwargs = dict(
            model="claude-haiku-4-5-20251001",
            max_tokens=2500,
            system=system_prompt + " Always return valid JSON only.",
            messages=[
                {"role": "user", "content": resume_text}
            ]
        )
        if temperature is not None:
            create_kwargs["temperature"] = temperature
        response = client.messages.create(**create_kwargs)

        # Detect truncation before attempting to parse — truncated JSON produces
        # a cryptic json.loads error that's hard to diagnose otherwise.
        if response.stop_reason == "max_tokens":
            raise Exception(
                f"LLM skill extraction failed: response was truncated at {response.usage.output_tokens} tokens "
                f"(stop_reason=max_tokens). Increase max_tokens or shorten the resume input."
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
