"""
Shared pytest fixtures used across all test modules.
External services (Anthropic, S3, Redis) are always mocked so tests run
without real credentials.
"""
import os
import pytest
from unittest.mock import patch

# Point the database at an in-memory SQLite instance before any module imports
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("CLAUDE_API_KEY", "test-key")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test-key-id")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test-secret")
os.environ.setdefault("AWS_BUCKET_NAME", "test-bucket")
os.environ.setdefault("AWS_REGION", "us-east-1")
# Use in-memory rate limit storage so tests never need a real Redis server
os.environ.setdefault("REDIS_URL", "memory://")


@pytest.fixture()
def sample_resume_data() -> dict:
    """Minimal structured resume JSON as returned by tailor_resume_to_json."""
    return {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "555-123-4567",
        "website": "https://janedoe.dev",
        "github": "https://github.com/janedoe",
        "linkedin": "https://linkedin.com/in/janedoe",
        "experience": [
            {
                "company": "Acme Corp",
                "location": "San Francisco, CA",
                "title": "Software Engineering Intern",
                "dates": "May 2024 – Aug 2024",
                "bullets": [
                    "Built REST API endpoints using FastAPI",
                    "Reduced query time by 40% with index optimization",
                ],
            }
        ],
        "education": [
            {
                "school": "State University",
                "location": "Austin, TX",
                "degree": "B.S. Computer Science",
                "dates": "2021 – 2025",
            }
        ],
        "skills": {
            "Programming Languages": "Python, JavaScript",
            "Frameworks": "FastAPI, React",
        },
        "projects": [
            {
                "name": "InternTracker (Python, React)",
                "dates": "Jan 2024",
                "bullets": ["Built a tool to track internship applications"],
            }
        ],
    }


@pytest.fixture()
def minimal_pdf_bytes() -> bytes:
    """
    Smallest valid single-page PDF (no text needed — just enough for
    pdfplumber to open it and report one page).
    """
    return (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj "
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj "
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj "
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer<</Size 4/Root 1 0 R>>\n"
        b"startxref\n190\n%%EOF"
    )


# ---------------------------------------------------------------------------
# Rate limiting test fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=False)
def mock_lifespan_deps():
    """
    Prevent the app lifespan from connecting to Redis or scraping jobs.
    Applied explicitly in rate limiting tests (not autouse globally).
    """
    with patch("job_cache.init_redis", return_value=False), \
         patch("job_cache.get_cache_info", return_value={}), \
         patch("job_cache.get_cached_jobs", return_value=[]):
        yield


@pytest.fixture(autouse=False)
def reset_rate_limiter():
    """
    Swap the limiter's backing storage for a fresh MemoryStorage before
    each test so rate-limit counters don't bleed between tests.

    slowapi's Limiter keeps a reference at both limiter._storage and
    limiter._limiter.storage (they point to the same object). We patch
    both so the FixedWindowRateLimiter uses the fresh in-memory store.
    """
    from limits.storage import MemoryStorage
    from app import limiter

    fresh = MemoryStorage()
    old = limiter._storage
    limiter._storage = fresh
    limiter._limiter.storage = fresh
    yield
    limiter._storage = old
    limiter._limiter.storage = old


@pytest.fixture(autouse=False)
def api_client(mock_lifespan_deps):
    """TestClient wrapping the FastAPI app. Lifespan deps are already mocked."""
    from starlette.testclient import TestClient
    from app import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
