"""
Canonical job-category buckets and deterministic classification.

The ATS crawler ingests EVERY internship from each board (finance, marketing,
HR, ... not just SWE). This module maps the messy free-text `department` field
(or, when absent, the job title) onto a small fixed set of buckets that power the
upload-page department filter.

Classification pipeline (title-first, embedding-augmented):
  1. Embedding similarity on title  — handles vocab gaps and resolves keyword
     conflicts (e.g. "Clinical AI Intern" → healthcare, not data_ml).
  2. Keyword match on title         — fast path for unambiguous titles.
  3. Keyword match on department    — fallback when title is generic ("Intern").
  4. Source default                 — github_internships → software, else other.

Single source of truth: `crawlers/normalizer.py` and the GitHub scraper stamp
`metadata['category']` at insert time, `matching/matcher._passes_category_filter`
filters on it at match time, and the frontend mirrors CATEGORIES for its labels.
"""
import threading

# (id, human label) — order is the UI display order. `other` is the catch-all.
CATEGORIES = [
    ("software", "Software Engineering"),
    ("data_ml", "Data / ML / AI"),
    ("hardware", "Hardware / Embedded"),
    ("security", "Security"),
    ("product", "Product"),
    ("design", "Design / UX"),
    ("business", "Business & Finance"),
    ("healthcare", "Healthcare / Medical"),
    ("legal", "Legal"),
    ("policy", "Policy / Gov / Nonprofit"),
    ("education", "Education"),
    ("other", "Other / Unclassified"),
]

CATEGORY_IDS = {cid for cid, _ in CATEGORIES}

# Keyword rules, checked in THIS order — most specific first so a technical role
# is claimed before the broad "software"/"business" buckets. Each entry:
# (bucket_id, [substrings]). First bucket with any substring in the text wins.
_RULES = [
    ("security", [
        "security", "infosec", "appsec", "cyber", "cryptograph", "pen test", "pentest",
    ]),
    ("data_ml", [
        "machine learning", "ml engineer", " ml ", "deep learning", "data scien",
        "data engineer", "data analy", "analytics", "artificial intelligence",
        " ai ", "ai/ml", "nlp", "computer vision", "research scientist",
        "applied scientist", "quant", "data intern", "data team", "data,",
    ]),
    ("hardware", [
        "hardware", "embedded", "firmware", "electrical", "robotic", "mechanical",
        "fpga", "asic", "silicon", "chip", " rf ", "circuit", "pcb", "controls",
    ]),
    ("design", [
        "ux", "ui design", "user experience", "user interface", "product design",
        "graphic design", "visual design", "ux/ui", "design system", "designer",
        "creative", "brand design",
    ]),
    # Checked before healthcare to prevent "therapy" (a company/product name) from
    # firing when the title is clearly editorial/media.
    ("business", ["editorial", "media relations", "content creator", "journalist"]),
    ("healthcare", [
        "healthcare", "health care", "nursing", "nurse", " medical", "clinical",
        "physician", "veterinar", " dvm", "pharmacy", "pharmac", "dental", "hospital",
        "patient care", "therapist", "therapy", "rehabilitation", "mental health",
        "public health", "biotech", "pre-med", "premed", "surgical", "diagnostic",
        "radiology", "oncology", "pathology", "epidemiol", "life sciences",
        "pharmaceutical", "med tech", "medtech",
        "health econom", "outcomes research", " heor", "pharmacoeconom",
        "health outcomes", "real world evidence", " rwe ",
    ]),
    ("legal", [
        " legal", "attorney", "counsel", "paralegal", "litigation", "law clerk",
        "judicial", "law intern", "summer associate", " law ", "regulatory affairs",
        "damages", "compliance intern", "compliance analyst",
    ]),
    ("policy", [
        "policy", "government", "nonprofit", "non-profit", "advocacy", "legislative",
        "congressional", "public sector", "civic tech", "political science",
        "diplomat", "social impact", " ngo", "public affairs", "public administration",
        "foreign affairs", "international relations", "sustainability intern",
    ]),
    ("education", [
        "teacher", "teaching", "tutor", "curriculum", "instructional design",
        "classroom", "educator", "edtech", "ed tech", "academic advisor",
        "student success", "student services", "school program", "higher education",
    ]),
    ("business", [
        "marketing", "sales", "finance", "financ", "account", "recruit", "talent",
        "human resources", " hr ", "people ops", "people operations", "people team",
        "operations", "supply chain", "business develop", "biz dev",
        "communication", "customer success", "customer support", "customer experience",
        "content", "partnership", "go to market", "go-to-market", "gtm",
        "administrat", "procurement", "consulting", "strategy", "community",
        "social media", "public relations", "growth marketing",
        "private equity", "investment bank", "venture capital", "asset management",
    ]),
    ("software", [
        "software", "swe", "developer", "back end", "backend", "front end",
        "frontend", "full stack", "full-stack", "devops", "site reliability",
        " sre ", "infrastructure", "platform engineer", "platform team", "mobile",
        " ios ", "android", "web develop", "cloud", "systems engineer",
        "distributed systems", "programmer", "programming", "engineering", "engineer",
    ]),
    ("product", [
        "product manage", "product management", "product owner", "associate product",
        "product analyst", "product intern", "product,", "product team", "product",
    ]),
]


def _bucket_from_text(text):
    """Return the first matching bucket id for `text`, or None."""
    if not text:
        return None
    # pad so " ml "/" ai "/" hr " word-ish matches work at string boundaries
    t = " " + text.lower() + " "
    for bucket, keywords in _RULES:
        if any(kw in t for kw in keywords):
            return bucket
    return None


# ── Embedding-based classification ────────────────────────────────────────────
# One descriptive phrase per category — the semantic centroid for all-MiniLM-L6-v2.
# "other" is deliberately absent; low-confidence titles fall through to source default.
_CATEGORY_ANCHORS = {
    "software":   "software engineer developer programming backend frontend web mobile cloud devops",
    "data_ml":    "data science machine learning artificial intelligence analytics NLP data engineering model training",
    "hardware":   "hardware embedded firmware electrical mechanical engineering FPGA circuit chip",
    "security":   "cybersecurity information security network penetration testing vulnerability cryptography",
    "product":    "product management product manager roadmap user story feature prioritization product strategy",
    "design":     "UX design UI user experience visual design graphic interaction design portfolio",
    "business":   "marketing sales finance business development operations consulting strategy editorial media communications",
    "healthcare": "healthcare clinical medical nursing hospital patient care pharmacy public health biomedical health economics outcomes research pharmacoeconomics epidemiology",
    "legal":      "legal attorney paralegal law regulation litigation compliance judicial",
    "policy":     "government policy legislation advocacy public sector civic international relations nonprofit social impact regulatory affairs",
    "education":  "teaching tutoring curriculum education edtech academic student learning classroom instructor",
}

_category_vecs = None
_category_vecs_lock = threading.Lock()


def _get_category_vecs():
    global _category_vecs
    if _category_vecs is None:
        with _category_vecs_lock:
            if _category_vecs is None:
                from matching.embedder import embed_text
                _category_vecs = {cat: embed_text(phrase) for cat, phrase in _CATEGORY_ANCHORS.items()}
    return _category_vecs


def _classify_with_embeddings(text):
    """
    Return best-matching category if similarity is clear, else None.

    Requires best cosine similarity > 0.20 AND a gap of > 0.05 over the
    second-best match to avoid coin-flip assignments. Returns None when the
    model is unavailable so keyword matching takes over gracefully.
    """
    if not text:
        return None
    try:
        from matching.embedder import embed_text, cosine_similarity
        vec = embed_text(text)
        if not vec:
            return None
        vecs = _get_category_vecs()
        scores = {cat: cosine_similarity(vec, cv) for cat, cv in vecs.items()}
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_cat, best_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        if best_score > 0.20 and (best_score - second_score) > 0.05:
            return best_cat
        return None
    except Exception:
        return None  # degrade gracefully to keyword matching


def categorize_job(department, title, source):
    """
    Map a job onto a canonical bucket id (always one of CATEGORY_IDS).

    Priority:
      1. Embedding on title  — resolves conflicts keywords can't (context-aware).
      2. Keyword on title    — fast unambiguous path.
      3. Keyword on dept     — fallback for generic titles like "Intern".
      4. Source default      — github_internships → software; else other.
    """
    # 1. Embedding on title (handles vocab gaps + multi-signal disambiguation)
    bucket = _classify_with_embeddings(title) if title else None
    if bucket:
        return bucket

    # 2. Keyword match on title
    bucket = _bucket_from_text(title)
    if bucket:
        return bucket

    # 3. Keyword match on department (ATS dept fields are org-structure, not role)
    bucket = _bucket_from_text(department)
    if bucket:
        return bucket

    # 4. Source default
    if source == "github_internships":
        return "software"
    return "other"
