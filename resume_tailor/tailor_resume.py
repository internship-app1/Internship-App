import io
import json
import os
import re
import subprocess
import tempfile
import anthropic
import pdfplumber

# ---------------------------------------------------------------------------
# Module-level prompt constant (injectable for evals)
# ---------------------------------------------------------------------------

TAILOR_SYSTEM_PROMPT = """You are a senior technical recruiter and resume writer with expertise in software engineering hiring. Your job is to tailor a candidate's resume for a target role — rephrasing existing content to maximize keyword alignment and ATS relevance while staying strictly truthful.

TRUTHFULNESS (non-negotiable):
- Every bullet must be grounded in facts explicitly stated in the original resume. Never write a bullet that is not directly supported by the source text.
- Rephrasing existing work using job description keywords is allowed; inventing new bullet points is not.
- WRONG: resume has no "data pipeline" work → adding "Developed data ingestion pipeline for ML-ready storage" (fabricated)
- WRONG: resume says "Anthropic/OpenAI/Gemini API" → writing "Claude/OpenAI/Gemini API" (modified verbatim content)
- RIGHT: resume has AWS S3 work → "Managed AWS S3 storage for 250+ files" front-loaded with job's storage keywords
- RIGHT: resume has Claude API work → rephrase as "LLM integration pipeline" if job mentions LLMs — same work, job-aligned language
- If the role is a poor fit, surface what genuinely overlaps and keep the rest accurate; do not pad.

KEYWORD ALIGNMENT (rephrase existing, never invent):
- Reword existing bullet content to front-load exact terms from the job description.
- Job says "distributed systems" → describe the real multi-tier data layer as "distributed" where accurate.
- Job says "AI agents" → describe the real agentic order-automation work using that language.
- Do NOT write a new bullet to cover a job requirement the resume never addressed.

SKILLS ACCURACY:
- Copy skill values faithfully from the resume. Do not rename tools (e.g. "Anthropic/OpenAI/Gemini API" must stay as-is, not become "Claude/OpenAI/Gemini API").
- Organize skills into dict categories; do not drop demonstrated skills from the original resume.

SPECIFICITY (never drop metrics):
- Preserve all original numbers, percentages, counts, and deployment evidence in every bullet.
- If a metric fits in the source it must appear in the tailored version — do not sacrifice metrics for concision.
- BAD: "Built internal tools including AWS S3 store" (dropped "250+ files" metric)
- GOOD: "Built React + Python internal tools: Intercom ticketing (5+ min saved, 50+ customers), AWS S3 store for 250+ files"
- BAD: "Improved system performance significantly"
- GOOD: "Reduced inference latency 52% (270s→130s) via dynamic batching and prompt caching"

LINE DENSITY — NO WIDOW LINES (secondary goal, never override truthfulness/specificity):
Each bullet must land in one of two zones:
  ZONE A (one tight line):  ≤115 chars  — fits fully on a single line, no wrap.
  ZONE B (two full lines):  ≥215 chars  — fills both lines wall-to-wall.
NEVER write a bullet in the dead zone (116–214 chars) — that length wraps to one line
PLUS a 1–5 word orphan on a second line, wasting ~90% of that line's width.

WORKED EXAMPLES (using real resume content):

WRONG — 152 chars, dead zone, widow "for dashboard configuration":
  "Built Python abstraction wrapper around Grafanalib on 3-person engineering team, achieving 83% code reduction (30+ lines to 5) for dashboard configuration"

FIX A (tighten to Zone A, ≤115): cut trailing clause:
  "Built Python Grafanalib abstraction for 3-person team, achieving 83% code reduction (30+ lines to 5 per dashboard)"  [113 chars ✓]

FIX B (expand to Zone B, ≥215): add the real deployment context:
  "Built Python abstraction wrapper around Grafanalib achieving 83% code reduction (30+ to 5 lines per dashboard), validated and deployed across 3 active Grafana production environments for 3-person engineering team"  [213 chars ✓]

WRONG — 153 chars, dead zone, widow "PostgreSQL database backend":
  "Building full-stack professor review platform serving 30,000+ students using TypeScript, React, Node.js, and Drizzle ORM with PostgreSQL database backend"

FIX B (expand to Zone B): weave in the shipped deliverable:
  "Building full-stack professor review platform for 30,000+ SJSU students using TypeScript, React, Node.js, Drizzle ORM, PostgreSQL; shipped review submission flow and Python GraphQL webscraper for automated course data ingestion"  [228 chars ✓]

RIGHT (Zone B, 245 chars — the template to follow):
  "Shipped production multi-channel B2B AI order agent (webhooks, WhatsApp, email, phone) using Claude Sonnet with RAG vector stores, owning full-stack features from conception through deployment across 7 enterprise clients processing 1,000+ orders"

DECISION RULE for dead-zone bullets:
- If the bullet has more real facts to add (other deliverables, metrics, tech versions,
  deployment scope) → EXPAND to Zone B (≥215 chars).
- If there are no additional truthful facts → TIGHTEN to Zone A (≤115 chars) by cutting
  the trailing redundant phrase.
- NEVER invent facts to reach Zone B. Fabricated filler is worse than a short bullet.

CONCISION (quality over brevity):
- Each experience role: 3–5 bullets. Each project: 2–3 bullets.
- Goal is density and no filler, NOT a character limit — never drop a metric to make a bullet shorter.
- Do NOT pack bullets shorter than ~80 chars; extend them by weaving in metrics and technology names.
- No filler: never write "collaborated with cross-functional teams," "leveraged best practices," or "demonstrated strong ability to."

JSON CONTRACT:
- Return ONLY valid JSON — no markdown fences, no commentary.
- All fields required: name, email, phone, website, github, linkedin, experience, education, skills, projects.
- skills must be a dict of string-to-string (category → comma-separated values), not a list."""


def extract_text_from_pdf(file_content: bytes) -> str:
    try:
        text = ""
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
        return text
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from PDF: {e}")


def tailor_resume_to_json(
    resume_text: str, job_title: str, company: str, job_description: str,
    system_prompt=None, temperature=None,
) -> dict:
    """Single Sonnet call: extract structured JSON + tailor bullets to the job."""
    sys_p = system_prompt if system_prompt is not None else TAILOR_SYSTEM_PROMPT
    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    create_kwargs = dict(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        system=sys_p,
        messages=[
            {
                "role": "user",
                "content": (
                    f"Target role: {job_title} at {company}\n"
                    f"Job description:\n{job_description}\n\n"
                    f"Resume to tailor:\n{resume_text}\n\n"
                    "TASK: Actively rewrite every experience and project bullet to maximize relevance for "
                    "the target role above. Do not copy bullets verbatim — rephrase each one to front-load "
                    "exact keywords and technologies from the job description while keeping all original "
                    "metrics and staying strictly truthful. Bullets that are already well-aligned can be "
                    "lightly rephrased; bullets that are off-topic should be reframed to highlight the most "
                    "relevant aspect of that work.\n\n"
                    "NO-WIDOW RULE: Every bullet must be EITHER ≤115 chars (one tight line) OR ≥215 "
                    "chars (two near-full lines). NEVER write a bullet in the 116–214 char dead zone — "
                    "that length creates a widow (1–5 word orphan on an otherwise empty line). "
                    "To fix a dead-zone bullet: if more real facts exist (other deliverables, tech "
                    "versions, team size, deployment scope) → expand to ≥215 chars; if no more "
                    "truthful content exists → tighten to ≤115 chars by cutting the trailing phrase. "
                    "Never invent facts to reach ≥215.\n\n"
                    "Return the tailored resume as JSON with this exact structure:\n"
                    "{\n"
                    '  "name": "Full Name",\n'
                    '  "email": "email@example.com",\n'
                    '  "phone": "555-555-5555",\n'
                    '  "website": "https://example.com",\n'
                    '  "github": "https://github.com/username",\n'
                    '  "linkedin": "https://linkedin.com/in/username",\n'
                    '  "experience": [\n'
                    '    {"company": "...", "location": "City, ST", "title": "...", "dates": "...", "bullets": ["..."]}\n'
                    "  ],\n"
                    '  "education": [\n'
                    '    {"school": "...", "location": "City, ST", "degree": "...", "dates": "..."}\n'
                    "  ],\n"
                    '  "skills": {\n'
                    '    "Programming Languages": "Python, Java",\n'
                    '    "Frameworks & Libraries": "React.js, Node.js",\n'
                    '    "Developer Tools": "Git, Docker"\n'
                    "  },\n"
                    '  "projects": [\n'
                    '    {"name": "Project Name (Tech1, Tech2)", "dates": "...", "bullets": ["..."]}\n'
                    "  ]\n"
                    "}"
                ),
            }
        ],
    )
    if temperature is not None:
        create_kwargs["temperature"] = temperature
    response = client.messages.create(**create_kwargs)
    raw = response.content[0].text.strip()
    # Strip markdown fences if model adds them anyway
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        stop = response.stop_reason
        raise RuntimeError(
            f"Resume JSON truncated (stop_reason={stop!r}): {e}. "
            "Increase max_tokens or shorten the resume."
        ) from e


def _latex_bullet(text: str) -> str:
    """
    Return a LaTeX \\item line for one bullet, injecting \\looseness hints so
    microtype can eliminate widow trailing lines:

    Zone A  (≤115 chars)  — already fits on one line, no hint needed.
    Squeeze (116–175 chars) — closer to one line: \\looseness=-1 asks TeX to
        try fitting in one fewer line; microtype's ±2% font expansion absorbs slack.
    Expand  (176–214 chars) — closer to two lines: \\looseness=1 asks TeX to
        use one more line, turning a partial second line into two near-full lines.
    Zone B  (≥215 chars)  — already two lines, no hint needed.
    """
    escaped = _escape_latex(text)
    char_len = len(text)
    if 116 <= char_len <= 175:
        return f"  \\item {{\\looseness=-1 {escaped}}}\n"
    if 176 <= char_len <= 214:
        return f"  \\item {{\\looseness=1 {escaped}}}\n"
    return f"  \\item {escaped}\n"


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters in plain text."""
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
        ("~", r"\textasciitilde{}"),
        ("^", r"\textasciicircum{}"),
    ]
    for char, escaped in replacements:
        text = text.replace(char, escaped)
    return text


def _href(url: str, display: str) -> str:
    """Build a LaTeX hyperlink."""
    return f"\\href{{{url}}}{{{display}}}"


def inject_into_template(data: dict) -> str:
    """Fill template.tex placeholders with the structured JSON data."""
    template_path = os.path.join(os.path.dirname(__file__), "template.tex")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()

    # Build experience section — company/location line then italic title/dates
    exp_blocks = []
    for job in data.get("experience", []):
        company = _escape_latex(job.get("company", ""))
        location = _escape_latex(job.get("location", ""))
        title = _escape_latex(job.get("title", ""))
        dates = _escape_latex(job.get("dates", ""))
        header = f"\\textbf{{{company}}} \\hfill {location} \\\\\n\\textit{{{title}}} \\hfill \\textit{{{dates}}}"
        bullets = "".join(_latex_bullet(b) for b in job.get("bullets", []))
        exp_blocks.append(
            f"{header}\n"
            "\\begin{itemize}[nosep, leftmargin=*]\n"
            + bullets
            + "\\end{itemize}"
        )
    experience_latex = "\n\n".join(exp_blocks) if exp_blocks else "No experience listed."

    # Build education section — bold school/location then italic degree/dates
    edu_blocks = []
    for edu in data.get("education", []):
        school = _escape_latex(edu.get("school", ""))
        location = _escape_latex(edu.get("location", ""))
        degree = _escape_latex(edu.get("degree", ""))
        dates = _escape_latex(edu.get("dates", ""))
        edu_blocks.append(
            f"\\textbf{{{school}}} \\hfill {location} \\\\\n"
            f"\\textit{{{degree}}} \\hfill {dates}"
        )
    education_latex = "\n\n".join(edu_blocks) if edu_blocks else "No education listed."

    # Build skills section — bold category labels, one per line
    skills_data = data.get("skills", {})
    if isinstance(skills_data, dict):
        lines = []
        items = list(skills_data.items())
        for i, (category, value) in enumerate(items):
            escaped_cat = _escape_latex(category)
            escaped_val = _escape_latex(value)
            ending = " \\\\" if i < len(items) - 1 else ""
            lines.append(f"\\textbf{{{escaped_cat}:}} {escaped_val}{ending}")
        skills_latex = "\n".join(lines)
    else:
        skills_latex = ", ".join(_escape_latex(s) for s in skills_data) if skills_data else "No skills listed."

    # Build projects section — bold name/dates then bullets
    proj_blocks = []
    for proj in data.get("projects", []):
        name = _escape_latex(proj.get("name", ""))
        dates = _escape_latex(proj.get("dates", ""))
        bullets = "".join(_latex_bullet(b) for b in proj.get("bullets", []))
        proj_blocks.append(
            f"\\textbf{{{name}}} \\hfill {dates}\n"
            "\\begin{itemize}[nosep, leftmargin=*]\n"
            + bullets
            + "\\end{itemize}"
        )
    projects_latex = "\n\n".join(proj_blocks) if proj_blocks else ""

    # Build contact link placeholders
    email = data.get("email", "")
    email_latex = _href(f"mailto:{email}", _escape_latex(email)) if email else ""

    website = data.get("website", "")
    website_display = website.replace("https://", "").replace("http://", "").rstrip("/")
    website_latex = _href(website, _escape_latex(website_display)) if website else ""

    github = data.get("github", "")
    github_latex = _href(github, "github") if github else ""

    linkedin = data.get("linkedin", "")
    linkedin_latex = _href(linkedin, "linkedin") if linkedin else ""

    template = template.replace("{{NAME}}", _escape_latex(data.get("name", "Name")))
    template = template.replace("{{PHONE}}", _escape_latex(data.get("phone", "")))
    template = template.replace("{{EMAIL}}", email_latex)
    template = template.replace("{{WEBSITE}}", website_latex)
    template = template.replace("{{GITHUB}}", github_latex)
    template = template.replace("{{LINKEDIN}}", linkedin_latex)
    template = template.replace("{{EDUCATION}}", education_latex)
    template = template.replace("{{SKILLS}}", skills_latex)
    template = template.replace("{{EXPERIENCE_BULLETS}}", experience_latex)
    template = template.replace("{{PROJECTS}}", projects_latex)

    return template


def _count_pdf_pages(pdf_bytes: bytes) -> int:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return len(pdf.pages)


FONT_SIZES = [11, 10, 9, 8]


def compile_to_single_page(latex_source: str) -> bytes:
    for size in FONT_SIZES:
        versioned = latex_source.replace("{{FONT_SIZE}}", str(size))
        pdf_bytes = compile_latex_to_pdf(versioned)
        if _count_pdf_pages(pdf_bytes) <= 1:
            return pdf_bytes
    return pdf_bytes  # return smallest attempt if still > 1 page


def compile_latex_to_pdf(latex_source: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        tex_path = os.path.join(tmpdir, "resume.tex")
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(latex_source)

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory",
            tmpdir,
            tex_path,
        ]

        for _ in range(2):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

        if result.returncode != 0:
            log_snippet = result.stdout[-2000:] if result.stdout else result.stderr[-2000:]
            raise RuntimeError(f"pdflatex failed (exit {result.returncode}):\n{log_snippet}")

        pdf_path = os.path.join(tmpdir, "resume.pdf")
        if not os.path.exists(pdf_path):
            raise RuntimeError("pdflatex ran but produced no PDF file")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("Output file does not appear to be a valid PDF")

    return pdf_bytes


def tailor_resume(
    file_content: bytes, job_title: str, company: str, job_description: str
) -> bytes:
    text = extract_text_from_pdf(file_content)
    if not text.strip():
        raise ValueError("Could not extract text from PDF")
    data = tailor_resume_to_json(text, job_title, company, job_description)
    latex = inject_into_template(data)
    return compile_to_single_page(latex)
