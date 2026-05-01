"""
dependencies.py
---------------
FastAPI dependency injection functions.

Provides:
  - get_db_collection() — injects the database
  - get_current_user()  — JWT-protected route dependency (optional)
  - verify_resume_exists() — reusable resume lookup
"""

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.database.memory import get_db, get_resumes_collection

logger = logging.getLogger(__name__)

# Optional Bearer token scheme (auto_error=False = routes work without a token too)
_bearer = HTTPBearer(auto_error=False)


# ─────────────────────────────────────────────────────────────────────────────
# Database dependency
# ─────────────────────────────────────────────────────────────────────────────

async def get_database():
    """
    Yield the active database.
    Raises RuntimeError if the DB was not initialized at startup.
    """
    return get_db()


# ─────────────────────────────────────────────────────────────────────────────
# Optional JWT auth (routes still work without a token)
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials],
        Security(_bearer),
    ] = None,
) -> Optional[dict]:
    """
    Optional JWT authentication dependency.

    If a valid Bearer token is provided, returns the decoded payload.
    If no token (or invalid token), returns None — routes are still reachable.

    Swap `auto_error=False` to `True` in `_bearer` and raise here to make
    routes JWT-protected.
    """
    if credentials is None:
        return None

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


# ─────────────────────────────────────────────────────────────────────────────
# Reusable resume existence check
# ─────────────────────────────────────────────────────────────────────────────

async def get_resume_or_404(resume_id: str) -> dict:
    """
    Dependency that fetches a resume by ID and raises 404 if not found.

    Usage:
        @router.get("/{resume_id}")
        async def my_endpoint(doc=Depends(get_resume_or_404)):
            ...
    """
    collection = get_resumes_collection()
    doc = await collection.find_one({"_id": resume_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Resume '{resume_id}' not found. "
                "Upload a resume first via POST /upload."
            ),
        )

    doc["_id"] = str(doc["_id"])  # ensure string for downstream use
    return doc
