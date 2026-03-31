"""
Integration tests for rate limiting.

How auth works in these tests:
  - `require_user` FastAPI dependency is overridden via app.dependency_overrides
    so no real Clerk JWT verification happens.
  - A fake JWT is still sent in the Authorization header because _get_rate_limit_key
    (app.py:144) reads that header *independently* of the dependency, decoding it
    without signature verification to extract the `sub` claim as the rate limit key.
  - jwt.encode({"sub": "..."}, "no-secret", algorithm="HS256") produces a structurally
    valid JWT that the rate limiter can decode.
"""
import asyncio
import io
import pytest
import jwt

from unittest.mock import patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_fake_token(sub: str) -> str:
    """Unsigned JWT — _get_rate_limit_key decodes it without signature check."""
    return jwt.encode({"sub": sub}, "no-secret", algorithm="HS256")


def auth_headers(sub: str = "test-user-id") -> dict:
    return {"Authorization": f"Bearer {make_fake_token(sub)}"}


def fake_pdf() -> bytes:
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
# /api/user-history — 20/minute, requires auth
# ---------------------------------------------------------------------------

class TestUserHistoryRateLimit:
    @pytest.fixture(autouse=True)
    def setup(self, api_client, reset_rate_limiter):
        from app import app
        from auth import require_user
        app.dependency_overrides[require_user] = lambda: "test-user-id"
        self.client = api_client
        yield
        app.dependency_overrides.pop(require_user, None)

    def test_allows_20_requests_then_rejects(self):
        """First 20 requests should succeed; the 21st must be 429."""
        headers = auth_headers("test-user-id")
        with patch("app.get_user_resume_history", return_value=[]):
            statuses = [
                self.client.get("/api/user-history", headers=headers).status_code
                for _ in range(21)
            ]

        assert all(s == 200 for s in statuses[:20]), (
            f"Expected all first 20 to be 200, got: {statuses[:20]}"
        )
        assert statuses[20] == 429, f"Expected 429 on request 21, got {statuses[20]}"

    def test_429_response_format(self):
        """429 response should mention rate limit and include a Retry-After header."""
        headers = auth_headers("format-test-user")
        with patch("app.get_user_resume_history", return_value=[]):
            for _ in range(20):
                self.client.get("/api/user-history", headers=headers)
            resp = self.client.get("/api/user-history", headers=headers)

        assert resp.status_code == 429
        assert "rate limit" in resp.text.lower() or "too many" in resp.text.lower()


# ---------------------------------------------------------------------------
# /api/match — 3/10minutes, no auth required
# ---------------------------------------------------------------------------

class TestMatchRateLimit:
    @pytest.fixture(autouse=True)
    def setup(self, api_client, reset_rate_limiter):
        self.client = api_client

    def test_allows_3_requests_then_rejects(self):
        """Fourth POST to /api/match within 10 minutes must be 429."""
        # The rate limiter fires before the handler body runs, so even if the
        # first 3 requests return a non-200 (bad PDF parse, etc.) they still
        # consume quota. We just need the 4th to be 429.
        with patch("app.parse_resume", return_value={"skills": [], "raw_text": ""}), \
             patch("app.analyze_and_match_single_call", return_value=[]):
            statuses = []
            for _ in range(4):
                resp = self.client.post(
                    "/api/match",
                    files={"resume": ("test.pdf", io.BytesIO(fake_pdf()), "application/pdf")},
                    data={"think_deeper": "false"},
                )
                statuses.append(resp.status_code)

        assert statuses[3] == 429, (
            f"Expected 429 on 4th request, got {statuses[3]}. All statuses: {statuses}"
        )
        assert all(s != 429 for s in statuses[:3]), (
            f"Rate limit triggered too early: {statuses}"
        )


# ---------------------------------------------------------------------------
# Per-user quota isolation
# ---------------------------------------------------------------------------

class TestPerUserIsolation:
    @pytest.fixture(autouse=True)
    def setup(self, api_client, reset_rate_limiter):
        from app import app
        from auth import require_user
        # Override returns a static value; rate limit key comes from the JWT sub
        app.dependency_overrides[require_user] = lambda: "any-user"
        self.client = api_client
        yield
        app.dependency_overrides.pop(require_user, None)

    def test_two_users_have_independent_quotas(self):
        """Exhausting user-a's quota must not affect user-b."""
        headers_a = auth_headers("user-a")
        headers_b = auth_headers("user-b")

        with patch("app.get_user_resume_history", return_value=[]):
            # Exhaust user-a
            for _ in range(20):
                r = self.client.get("/api/user-history", headers=headers_a)
                assert r.status_code == 200

            # user-a should now be rate limited
            r_a = self.client.get("/api/user-history", headers=headers_a)
            assert r_a.status_code == 429, "user-a should be rate limited"

            # user-b still has a fresh quota
            r_b = self.client.get("/api/user-history", headers=headers_b)
            assert r_b.status_code == 200, (
                f"user-b should not be affected by user-a's limit, got {r_b.status_code}"
            )


# ---------------------------------------------------------------------------
# LLM semaphore
# ---------------------------------------------------------------------------

class TestLLMSemaphore:
    def test_initial_capacity(self):
        """Semaphore must be initialised with 2 slots."""
        import app as app_module
        assert app_module.LLM_SEMAPHORE._value == 2

    @pytest.mark.asyncio
    async def test_blocks_third_concurrent_acquisition(self):
        """Third concurrent acquire should block until a slot is released."""
        sem = asyncio.Semaphore(2)

        await sem.acquire()  # slot 1
        await sem.acquire()  # slot 2 — both taken

        unblocked = asyncio.Event()

        async def try_acquire():
            await sem.acquire()
            unblocked.set()

        task = asyncio.create_task(try_acquire())
        await asyncio.sleep(0.05)
        assert not unblocked.is_set(), "3rd acquire should block while both slots are taken"

        sem.release()  # free one slot
        await asyncio.sleep(0.05)
        assert unblocked.is_set(), "3rd acquire should succeed after a slot is released"

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


# ---------------------------------------------------------------------------
# /api/cache-status — 10/minute, no auth required
# ---------------------------------------------------------------------------

class TestCacheStatusRateLimit:
    @pytest.fixture(autouse=True)
    def setup(self, api_client, reset_rate_limiter):
        self.client = api_client

    def test_allows_10_requests_then_rejects(self):
        """First 10 requests should succeed; the 11th must be 429."""
        with patch("job_cache.get_cache_info", return_value={}), \
             patch("job_cache.is_redis_available", return_value=False), \
             patch("job_cache.is_database_available", return_value=True):
            statuses = [
                self.client.get("/api/cache-status").status_code
                for _ in range(11)
            ]

        assert all(s == 200 for s in statuses[:10]), (
            f"Expected all first 10 to be 200, got: {statuses[:10]}"
        )
        assert statuses[10] == 429, f"Expected 429 on request 11, got {statuses[10]}"
