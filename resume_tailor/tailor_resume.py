import copy
import io
import json
import logging
import os
import re
import subprocess
import tempfile
import anthropic
import pdfplumber

logger = logging.getLogger(__name__)

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

NO DUPLICATE BULLETS (hard rule):
- Every bullet within an entry must cover a DISTINCT achievement, deliverable, or metric.
- NEVER repeat the same metric, technology combination, or outcome across multiple bullets in the same entry.
- If two potential bullets cover the same work, MERGE them into one richer bullet rather than listing both.
- BAD: Bullet 1 ends "...migrated 7+ dashboards with unit test coverage on configuration layer" AND Bullet 2 is "Migrated 7+ dashboards with unit test coverage on configuration layer" — this is a literal duplicate, forbidden.
- BAD: Two bullets both starting "Engineered dual-model Claude pipeline (Haiku 4.5 for skill extraction, Sonnet 4.5..." — same subject, forbidden.
- GOOD: One comprehensive bullet merging all facts about that work.

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
    # Cap the JD to bound input cost/latency; scraped descriptions are well under this.
    job_description = (job_description or "")[:6000]
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


_STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "in", "of", "to", "with", "at", "by",
    "on", "is", "was", "are", "were", "that", "this", "from", "as", "via", "into",
    "using", "across", "through", "its", "our", "we", "i", "my", "their",
}


def _key_words(text: str) -> set:
    return {
        w.lower().strip(".,;:()'\"")
        for w in text.split()
        if w.lower().strip(".,;:()'\"") not in _STOP_WORDS and len(w) > 2
    }


def _are_near_duplicates(a: str, b: str, threshold: float = 0.60) -> bool:
    """True if the shorter bullet's key content is substantially contained in the longer."""
    words_a = _key_words(a)
    words_b = _key_words(b)
    if not words_a or not words_b:
        return False
    shorter = words_a if len(words_a) <= len(words_b) else words_b
    longer = words_a if len(words_a) > len(words_b) else words_b
    overlap = len(shorter & longer) / len(shorter)
    return overlap >= threshold


def _deduplicate_bullets(data: dict) -> dict:
    """Remove near-duplicate bullets within each entry (experience and projects).

    A bullet is dropped if >= 60% of its key words appear in an already-kept bullet
    in the same entry. This catches both exact repeats and cases where one bullet is
    a paraphrased subset of another.
    """
    data = copy.deepcopy(data)
    for section in ("experience", "projects"):
        for entry in data.get(section, []):
            bullets = entry.get("bullets", [])
            if len(bullets) <= 1:
                continue
            keep: list[str] = []
            for bullet in bullets:
                if any(_are_near_duplicates(bullet, kept) for kept in keep):
                    logger.info("Dropped near-duplicate bullet: %s…", bullet[:60])
                    continue
                keep.append(bullet)
            entry["bullets"] = keep
    return data


def _latex_bullet(text: str) -> str:
    """Return a plain LaTeX \\item line for one bullet.

    Widow elimination is handled by the closed-loop measure→rewrite→recompile
    pipeline (see refine_to_no_widows), NOT by per-bullet TeX spacing hints —
    the old approach was a no-op (the hint was reset by the closing brace before
    the paragraph broke) and could not express a font-dependent constraint anyway.
    """
    return f"  \\item {_escape_latex(text)}\n"


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


# ---------------------------------------------------------------------------
# Closed-loop widow elimination
#
# Instead of predicting wrapped width from character counts (which depend on the
# font and so cannot be fixed constants), we MEASURE the compiled PDF: derive the
# chars-per-line C from the widest rendered line, measure each bullet's last
# wrapped line, and rewrite only the bullets whose last line is a short orphan.
# ---------------------------------------------------------------------------

# A wrapped bullet's last physical line is a "widow" if it fills less than this
# fraction of the rendered line width C. This is the ONLY widow threshold — there
# are no font-dependent character constants anywhere in the widow logic.
# Set high (0.85) to push the LLM toward last lines that are nearly wall-to-wall.
WIDOW_THRESHOLD = 0.85

# Hard floor for the deterministic backstop. After the LLM rounds, ANY bullet whose
# last line is still below this fraction is trimmed to a single (full) line for free —
# guaranteeing no genuinely-short orphan can ship. The 0.70–0.85 band is left as
# content-preserving two-liners (the LLM tried; the line is "mostly full").
BACKSTOP_FLOOR = 0.70

# The itemize bullet glyph emitted by pdftotext -layout for this template
# (enumitem default first level). Confirmed empirically against a compiled PDF.
_BULLET_GLYPH = "•"  # •


def _pdftotext_layout(pdf_bytes: bytes) -> str:
    """Return the `pdftotext -layout` rendering of a PDF as text."""
    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = os.path.join(tmpdir, "doc.pdf")
        txt_path = os.path.join(tmpdir, "doc.txt")
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)
        subprocess.run(
            ["pdftotext", "-layout", pdf_path, txt_path],
            capture_output=True, check=True, timeout=30,
        )
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read()


def max_full_line_len(pdf_bytes: bytes) -> int:
    """Chars-per-line C at the active font, measured from the compiled PDF.

    The \\hfill header/location and project/date lines span the full text block,
    so the widest rstripped layout line equals C. This self-calibrates at any
    font size — no hardcoded constant.
    """
    text = _pdftotext_layout(pdf_bytes)
    widths = [len(line.rstrip()) for line in text.splitlines() if line.strip()]
    return max(widths) if widths else 0


def measure_bullets(pdf_bytes: bytes):
    """Measure each itemize bullet's first and LAST physical line widths.

    Returns a list of (first_line_width, last_wrapped_line_width) in document
    order — experience bullets first, then projects — matching
    inject_into_template's render order. A single-line bullet yields
    (width, 0). Widths are rstripped rendered widths (leading indent included),
    so they share the same scale as max_full_line_len's C.

    Note: we report the LAST wrapped line (not strictly the "second"), because a
    bullet may wrap to 3+ lines and the orphan is always the final line.
    """
    text = _pdftotext_layout(pdf_bytes)
    lines = text.splitlines()
    pairs = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip(" ")
        if stripped.startswith(_BULLET_GLYPH):
            first_width = len(line.rstrip())
            last_width = 0
            j = i + 1
            while j < n:
                nxt = lines[j]
                if not nxt.strip():
                    j += 1
                    continue  # defensively skip blank lines
                nxt_stripped = nxt.lstrip(" ")
                lead = len(nxt) - len(nxt_stripped)
                if nxt_stripped.startswith(_BULLET_GLYPH):
                    break       # next bullet
                if lead == 0:
                    break       # section header or new entry header (col 0)
                last_width = len(nxt.rstrip())  # indented continuation line
                j += 1
            pairs.append((first_width, last_width))
            i = j
        else:
            i += 1
    return pairs


def _flatten_bullet_locations(data: dict):
    """Bullet locations in render order: experience bullets, then projects.

    Each location is a (section, entry_index, bullet_index) tuple, aligned 1:1
    with measure_bullets' output order.
    """
    locations = []
    for section in ("experience", "projects"):
        for j, entry in enumerate(data.get(section, [])):
            for k in range(len(entry.get("bullets", []))):
                locations.append((section, j, k))
    return locations


# Compact system prompt for the widow-fix call. This is a trivial constrained edit,
# so it uses Haiku (3x cheaper than Sonnet) and a ~150-token instruction instead of
# re-sending the full 2k-token TAILOR_SYSTEM_PROMPT on every call.
_WIDOW_FIX_SYSTEM = (
    "You rewrite resume bullet points to fix line-wrapping 'widows' (a short orphan "
    "on the last line). Hard rules: every fact must come verbatim in meaning from the "
    "provided resume — never invent companies, metrics, technologies, dates, or "
    "outcomes, and keep all original numbers. Output only the rewritten bullets."
)

# Haiku is the right tier for this constrained one-line edit; full ID matches the
# model used elsewhere in the pipeline for fast ops.
_WIDOW_FIX_MODEL = "claude-haiku-4-5-20251001"


def _batch_widow_rewrite(items, cap: int, resume_text: str):
    """Rewrite ALL widowed bullets in ONE Haiku call. Returns {index: new_text}.

    `items` is a list of (index, bullet_text, fill_pct). The resume is sent once
    (not per bullet), and a compact system prompt replaces the 2k-token tailoring
    prompt — so cost is one cheap call per round instead of N expensive ones.
    """
    if not items:
        return {}
    client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

    lines = []
    for idx, bullet, fill_pct in items:
        lines.append(
            f'[{idx}] (last line only {fill_pct:.0f}% full) "{bullet}"'
        )
    bullets_block = "\n".join(lines)

    user_msg = (
        f"Resume (the ONLY source of truth for facts):\n{resume_text}\n\n"
        f"The page fits about {cap} characters per line. Each bullet below wrapped to a "
        f"widow — a nearly-empty last line. Rewrite EACH one to EITHER:\n"
        f"  A) fit on ONE line: <= {cap} characters, OR\n"
        f"  B) fill TWO lines: extend with real resume facts so the second line is at "
        f"least 75% full (roughly {int(cap * 1.75)}-{int(cap * 2)} characters total).\n"
        f"Prefer B (extend with true detail) when the resume has more facts for that work; "
        f"otherwise tighten to A. Never invent facts.\n\n"
        f"Bullets to fix (keyed by number):\n{bullets_block}\n\n"
        f'Return ONLY a JSON object mapping each bullet number to its rewritten text, '
        f'e.g. {{"0": "rewritten bullet", "3": "rewritten bullet"}}. No commentary.'
    )

    resp = client.messages.create(
        model=_WIDOW_FIX_MODEL,
        max_tokens=min(4000, 250 + 160 * len(items)),
        system=_WIDOW_FIX_SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        logger.warning("widow rewrite returned non-JSON, skipping round: %s", e)
        return {}
    out = {}
    for k, v in parsed.items():
        try:
            out[int(k)] = _clean_bullet_text(v)
        except (ValueError, TypeError):
            continue
    return out


def _trim_to_single_line(text: str, cap: int) -> str:
    """Trim a bullet at a word boundary so it renders on ONE line (<= ~92% of C).

    Deterministic, no API. A single line is never a widow, so this is the free
    backstop that guarantees full-width output even if the model can't extend.
    """
    target = max(20, int(cap * 0.92))
    if len(text) <= target:
        return text
    out = ""
    for w in text.split():
        candidate = (out + " " + w).strip()
        if len(candidate) > target:
            break
        out = candidate
    return out or text[:target]


def _clean_bullet_text(text: str) -> str:
    """Normalize a model-returned bullet to a single clean line."""
    text = text.strip()
    # Drop a leading bullet glyph / dash the model may have added
    text = re.sub(r"^[•\-\*]\s*", "", text)
    # Collapse internal newlines/whitespace to single spaces
    text = " ".join(text.split())
    # Strip wrapping quotes if present
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        text = text[1:-1].strip()
    return text


def rewrite_widowed_bullets(data: dict, widows, cap: int, resume_text: str, rewrite_fn) -> dict:
    """Rewrite the widowed bullets in `data`, matched BY POSITION.

    `widows` is a list of (bullet_index, fill_pct) in measure_bullets /
    _flatten_bullet_locations order. `rewrite_fn(items, cap, resume_text) ->
    {index: new_text}` is the injectable BATCH seam — one call fixes every widow
    (Haiku in prod, a hand-authored map in the no-API eval). Returns a NEW data dict.
    """
    data = copy.deepcopy(data)
    locations = _flatten_bullet_locations(data)

    items = []
    for idx, fill_pct in widows:
        if idx >= len(locations):
            logger.warning("widow index %d out of range (%d bullets)", idx, len(locations))
            continue
        section, j, k = locations[idx]
        items.append((idx, data[section][j]["bullets"][k], fill_pct))

    if not items:
        return data

    try:
        rewrites = rewrite_fn(items, cap, resume_text)
    except Exception as e:
        logger.warning("batch rewrite_fn failed: %s", e)
        return data

    for idx, new_bullet in (rewrites or {}).items():
        if idx >= len(locations) or not new_bullet:
            continue
        section, j, k = locations[idx]
        data[section][j]["bullets"][k] = new_bullet
    return data


def _compile_at_font(latex_source: str, size: int) -> bytes:
    """Compile the template at one specific font size."""
    return compile_latex_to_pdf(latex_source.replace("{{FONT_SIZE}}", str(size)))


def _lock_font(data: dict):
    """Compile at the largest font that fits one page; return (pdf, font)."""
    latex = inject_into_template(data)
    candidate = None
    for size in FONT_SIZES:
        candidate = _compile_at_font(latex, size)
        if _count_pdf_pages(candidate) <= 1:
            return candidate, size
    return candidate, FONT_SIZES[-1]  # even 8pt spilled — smallest attempt


def _recompile_locked(data: dict, font: int):
    """Recompile at the locked font, stepping down one size only if it spilled to 2 pages."""
    pdf = _compile_at_font(inject_into_template(data), font)
    if _count_pdf_pages(pdf) > 1:
        idx = FONT_SIZES.index(font)
        if idx + 1 < len(FONT_SIZES):
            font = FONT_SIZES[idx + 1]
            pdf = _compile_at_font(inject_into_template(data), font)
    return pdf, font


def refine_to_no_widows(data: dict, resume_text: str, rewrite_fn, max_rounds: int = 3) -> bytes:
    """Lock the font, then close the loop: measure → rewrite → recompile, with a
    free deterministic backstop that guarantees full-width bullets.

    Stage 1 (LLM, content-preserving): up to `max_rounds` cheap batched rewrites
    that try to EXTEND each widow toward WIDOW_THRESHOLD using real resume facts.
    Each round re-measures at the LOCKED font (C is font-dependent) and only the
    still-widowed bullets are sent back, so the model self-corrects on fresh
    measurements. The font is only ever stepped DOWN, never recomputed, to avoid
    oscillation.

    Stage 2 (deterministic, free): any bullet whose last line is STILL below
    BACKSTOP_FLOOR is trimmed to a single full line — no API, no fabrication. This
    is the hard guarantee that no genuinely-short orphan can ship even if the model
    failed to extend.
    """
    pdf, font = _lock_font(data)

    # ---- Stage 1: LLM extend rounds (preferred — keeps content) ----
    for _ in range(max_rounds):
        cap = max_full_line_len(pdf)
        if cap <= 0:
            break
        pairs = measure_bullets(pdf)
        locations = _flatten_bullet_locations(data)
        if len(locations) != len(pairs):
            logger.warning(
                "bullet count mismatch (data=%d, measured=%d) — skipping LLM widow rewrite",
                len(locations), len(pairs),
            )
            break
        widows = [
            (i, (l2 / cap) * 100)
            for i, (l1, l2) in enumerate(pairs)
            if l2 and (l2 / cap) < WIDOW_THRESHOLD
        ]
        if not widows:
            break
        new_data = rewrite_widowed_bullets(data, widows, cap, resume_text, rewrite_fn)
        if new_data is data:
            break
        data = new_data
        pdf, font = _recompile_locked(data, font)

    # ---- Stage 2: deterministic backstop — guarantee no orphan below the floor ----
    for _ in range(2):  # at most 2 passes (a trim can change wrapping once)
        cap = max_full_line_len(pdf)
        if cap <= 0:
            break
        pairs = measure_bullets(pdf)
        locations = _flatten_bullet_locations(data)
        if len(locations) != len(pairs):
            break
        bad = [i for i, (l1, l2) in enumerate(pairs) if l2 and (l2 / cap) < BACKSTOP_FLOOR]
        if not bad:
            break
        logger.info("deterministic backstop trimming %d residual widow(s) to one line", len(bad))
        data = copy.deepcopy(data)
        for i in bad:
            section, j, k = locations[i]
            data[section][j]["bullets"][k] = _trim_to_single_line(
                data[section][j]["bullets"][k], cap
            )
        pdf, font = _recompile_locked(data, font)

    return pdf


def tailor_resume(
    file_content: bytes, job_title: str, company: str, job_description: str
) -> bytes:
    text = extract_text_from_pdf(file_content)
    if not text.strip():
        raise ValueError("Could not extract text from PDF")
    data = tailor_resume_to_json(text, job_title, company, job_description)
    data = _deduplicate_bullets(data)
    return refine_to_no_widows(data, text, rewrite_fn=_batch_widow_rewrite)
