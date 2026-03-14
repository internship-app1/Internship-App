import io
import json
import os
import re
import subprocess
import tempfile
import anthropic
import pdfplumber


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
    resume_text: str, job_title: str, company: str, job_description: str
) -> dict:
    """Single Sonnet call: extract structured JSON + tailor bullets to the job."""
    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2500,
        system=(
            "You are a resume tailoring specialist. Given a resume and a target job, "
            "extract the candidate's information and reword the experience bullet points "
            "to better highlight relevance for the role. "
            "Return ONLY valid JSON matching the schema exactly — no markdown fences, no commentary."
        ),
        messages=[
            {
                "role": "user",
                "content": (
                    f"Target role: {job_title} at {company}\n"
                    f"Job description:\n{job_description}\n\n"
                    f"Resume:\n{resume_text}\n\n"
                    "Return JSON with this exact structure:\n"
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
        bullets = "".join(f"  \\item {_escape_latex(b)}\n" for b in job.get("bullets", []))
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
        bullets = "".join(f"  \\item {_escape_latex(b)}\n" for b in proj.get("bullets", []))
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
