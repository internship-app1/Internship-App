"""
Clerk JWT verification for FastAPI.
Validates Bearer tokens from the Authorization header and returns the verified user_id.
"""
import base64
import json
import os
import time

import httpx
import jwt
from fastapi import HTTPException, Request

# In-memory JWKS cache — refreshed every hour
_jwks_cache: dict = {"keys": None, "fetched_at": 0.0}
_JWKS_CACHE_TTL = 3600  # seconds


def _get_jwks_url() -> str:
    """Derive the Clerk JWKS URL from CLERK_PUBLISHABLE_KEY (or the React equivalent)."""
    key = (
        os.getenv("CLERK_PUBLISHABLE_KEY")
        or os.getenv("REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY")
        or ""
    ).strip()
    if not key:
        raise RuntimeError(
            "Neither CLERK_PUBLISHABLE_KEY nor REACT_APP_CLERK_PUBLISHABLE_CLIENT_KEY is set."
        )

    # Strip pk_live_ or pk_test_ prefix to get the base64url-encoded domain
    for prefix in ("pk_live_", "pk_test_"):
        if key.startswith(prefix):
            encoded = key[len(prefix):]
            break
    else:
        raise RuntimeError(f"Unrecognized Clerk publishable key format: {key[:20]}...")

    # Add base64 padding if needed
    padding = (4 - len(encoded) % 4) % 4
    encoded += "=" * padding

    domain = base64.b64decode(encoded).decode("utf-8").rstrip("$")
    return f"https://{domain}/.well-known/jwks.json"


def _fetch_jwks() -> list:
    """Return JWKS keys, using cache when fresh."""
    now = time.time()
    if _jwks_cache["keys"] and (now - _jwks_cache["fetched_at"]) < _JWKS_CACHE_TTL:
        return _jwks_cache["keys"]

    jwks_url = _get_jwks_url()
    resp = httpx.get(jwks_url, timeout=10)
    resp.raise_for_status()
    keys = resp.json()["keys"]
    _jwks_cache["keys"] = keys
    _jwks_cache["fetched_at"] = now
    return keys


def verify_clerk_token(token: str) -> dict:
    """Verify a Clerk JWT and return its decoded payload."""
    keys = _fetch_jwks()
    last_error: Exception = Exception("No keys available")

    for jwk_data in keys:
        try:
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk_data))
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_aud": False},  # Clerk tokens don't set aud by default
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as exc:
            last_error = exc
            continue

    raise HTTPException(status_code=401, detail=f"Invalid token: {last_error}")


async def require_user(request: Request) -> str:
    """
    FastAPI dependency — extracts and verifies the Clerk JWT from the Authorization header.
    Returns the verified Clerk user_id (the 'sub' claim).
    Raises 401 if the header is missing, malformed, or the token is invalid/expired.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Expected: Bearer <token>",
        )

    token = auth_header[len("Bearer "):]
    payload = verify_clerk_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token is missing 'sub' claim")

    return user_id
