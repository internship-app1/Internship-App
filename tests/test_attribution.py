"""Tests for POST /api/track-attribution — UTM first-touch recording."""
import pytest
from fastapi.testclient import TestClient

from job_database import UserAttribution, init_database


@pytest.fixture(scope="module", autouse=True)
def _file_backed_db(tmp_path_factory):
    """Use a file-backed SQLite so tables survive across threads (same as test_mcp_api)."""
    import job_database as jd
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    db_path = tmp_path_factory.mktemp("attrdb") / "test.db"
    old_engine, old_sl = jd.engine, jd.SessionLocal
    jd.engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    jd.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=jd.engine)
    jd.Base.metadata.create_all(jd.engine)
    yield
    jd.engine, jd.SessionLocal = old_engine, old_sl


@pytest.fixture()
def client():
    import app as appmod
    from auth import require_user
    appmod.app.dependency_overrides[require_user] = lambda: "user_test_attr"
    yield TestClient(appmod.app)
    appmod.app.dependency_overrides.clear()


@pytest.fixture()
def client_unauthed():
    import app as appmod
    return TestClient(appmod.app)


class TestTrackAttribution:
    UTM_PAYLOAD = {
        "utm_source": "billboard",
        "utm_medium": "cpa",
        "utm_campaign": "summer-2026",
        "utm_content": "ad-v1",
        "utm_term": "",
        "first_seen_at": "2026-06-12T20:00:00.000Z",
    }

    def test_records_attribution(self, client):
        r = client.post("/api/track-attribution", json=self.UTM_PAYLOAD)
        assert r.status_code == 200
        assert r.json() == {"ok": True}

        import job_database as jd
        db = jd.get_db()
        row = db.query(UserAttribution).filter_by(user_id="user_test_attr").first()
        db.close()
        assert row is not None
        assert row.utm_source == "billboard"
        assert row.utm_medium == "cpa"
        assert row.utm_campaign == "summer-2026"
        assert row.first_seen_at is not None

    def test_idempotent_second_call_no_overwrite(self, client):
        second_payload = {**self.UTM_PAYLOAD, "utm_source": "google"}
        r = client.post("/api/track-attribution", json=second_payload)
        assert r.status_code == 200

        import job_database as jd
        db = jd.get_db()
        rows = db.query(UserAttribution).filter_by(user_id="user_test_attr").all()
        db.close()
        assert len(rows) == 1
        assert rows[0].utm_source == "billboard"  # first-touch preserved

    def test_requires_auth(self, client_unauthed):
        r = client_unauthed.post("/api/track-attribution", json=self.UTM_PAYLOAD)
        assert r.status_code == 401

    def test_empty_body_does_not_crash(self, client):
        import app as appmod
        from auth import require_user
        appmod.app.dependency_overrides[require_user] = lambda: "user_empty_body"
        r = TestClient(appmod.app).post("/api/track-attribution", json={})
        appmod.app.dependency_overrides.clear()
        assert r.status_code == 200
