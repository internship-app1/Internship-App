import pytest

from pathlib import Path
from unittest.mock import patch

from job_database import Base, engine


@pytest.fixture
def frontend_static_dir():
    Path("frontend/build/static").mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def auth_override(frontend_static_dir, mock_lifespan_deps, reset_rate_limiter):
    from starlette.testclient import TestClient
    from app import app
    from auth import require_user

    app.dependency_overrides[require_user] = lambda: "test-user-id"
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.pop(require_user, None)


def test_save_cache_only_job_snapshot(auth_override):
    client = auth_override
    payload = {
        "job_hash": "cache-only-hash",
        "job_snapshot": {
            "job_hash": "cache-only-hash",
            "company": "Cache Only Co",
            "title": "Software Engineering Intern",
            "location": "Remote",
            "apply_link": "https://example.com/apply",
            "match_score": 91,
        },
    }

    with patch("app.upsert_saved_job", return_value={
        "job_hash": "cache-only-hash",
        "status": "saved",
        "notes": "",
        "deadline": None,
        "job": {
                "job_hash": "cache-only-hash",
                "company": "Cache Only Co",
                "title": "Software Engineering Intern",
                "location": "Remote",
                "apply_link": "https://example.com/apply",
                "match_score": 91,
        },
    }) as save_job:
        response = client.post("/api/saved-jobs", json=payload)

    assert response.status_code == 201, response.text
    save_job.assert_called_once()
    assert save_job.call_args.kwargs["job_snapshot"] == payload["job_snapshot"]
    body = response.json()
    assert body["job_hash"] == "cache-only-hash"
    assert body["job"]["company"] == "Cache Only Co"
    assert body["job"]["match_score"] == 91
