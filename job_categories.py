"""
Canonical job-category buckets and deterministic classification.

The ATS crawler ingests EVERY internship from each board (finance, marketing,
HR, ... not just SWE). This module maps the messy free-text `department` field
(or, when absent, the job title) onto a small fixed set of buckets that power the
upload-page department filter. Deterministic, no model — keep it on the
"deterministic crawler" side of the line.

Single source of truth: `crawlers/normalizer.py` and the GitHub scraper stamp
`metadata['category']` at insert time, `matching/matcher._passes_category_filter`
filters on it at match time, and the frontend mirrors CATEGORIES for its labels.
"""

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
    ("healthcare", [
        "healthcare", "health care", "nursing", "nurse", " medical", "clinical",
        "physician", "veterinar", " dvm", "pharmacy", "pharmac", "dental", "hospital",
        "patient care", "therapist", "therapy", "rehabilitation", "mental health",
        "public health", "biotech", "pre-med", "premed", "surgical", "diagnostic",
        "radiology", "oncology", "pathology", "epidemiol", "life sciences",
        "pharmaceutical", "med tech", "medtech",
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


def categorize_job(department, title, source):
    """
    Map a job onto a canonical bucket id (always one of CATEGORY_IDS).

    Priority: department text -> title text -> source default. github_internships
    is a curated SWE source, so anything unclassified there defaults to software;
    everything else unclassified -> other.
    """
    for text in (department, title):
        bucket = _bucket_from_text(text)
        if bucket:
            return bucket
    if source == "github_internships":
        return "software"
    return "other"
