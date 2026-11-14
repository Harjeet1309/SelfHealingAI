"""
API Auth — Shared Token Guard
==============================
Protects sensitive /inject/* and /ai/report endpoints from unauthenticated
callers (e.g. a rogue process or accidental exposure to the internet).

Usage
-----
Add `token: str = Depends(require_token)` to any FastAPI route that should
be protected.  The caller must supply the token in one of two ways:

    1. Header: Authorization: Bearer <token>
    2. Query param: ?token=<token>   (convenient for browser / curl demos)

Configuration
-------------
Set the INJECT_TOKEN environment variable. If it is empty or not set, token
auth is DISABLED and a startup warning is printed — this preserves backwards
compatibility when running locally without any env file.

    # docker-compose.yml  (or .env)
    INJECT_TOKEN=changeme-super-secret-token-2025
"""

import os
import logging

from fastapi import Depends, HTTPException, Header, Query, status

logger = logging.getLogger(__name__)

_TOKEN = os.getenv("INJECT_TOKEN", "").strip()

if not _TOKEN:
    logger.warning(
        "[Auth] ⚠️  INJECT_TOKEN is not set — /inject/* and /ai/report "
        "endpoints are UNPROTECTED. Set INJECT_TOKEN in the environment "
        "before running in production."
    )
else:
    logger.info("[Auth] ✅  Token auth enabled for protected endpoints.")


def require_token(
    authorization: str = Header(None, alias="Authorization"),
    token: str = Query(None, description="API auth token (alternative to header)"),
):
    """
    FastAPI dependency that enforces a shared secret token.

    - If INJECT_TOKEN is not configured, every call passes (backwards-compat).
    - Accepts the token as:
        Authorization: Bearer <token>
        OR  ?token=<token>
    """
    if not _TOKEN:
        return  # Auth disabled — no-op

    # Extract from Authorization: Bearer <token>
    header_token = None
    if authorization and authorization.lower().startswith("bearer "):
        header_token = authorization[7:].strip()

    provided = header_token or token

    if not provided:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth token. Supply 'Authorization: Bearer <token>' header or '?token=' query param.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if provided != _TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid auth token.",
        )
