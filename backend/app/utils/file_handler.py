"""
file_handler.py
---------------
Validates and temporarily stores uploaded resume files.

Responsibilities:
  - Validate file extension (PDF / DOCX only)
  - Validate file size (configurable limit)
  - Read file content into memory (BytesIO) for downstream parsers
  - Optionally persist to upload directory for debugging
"""

import io
import logging
import uuid
from pathlib import Path
from typing import Union

from fastapi import HTTPException, UploadFile, status

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({"pdf", "docx"})
MAX_SIZE_BYTES: int = settings.MAX_FILE_SIZE_MB * 1024 * 1024


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def read_upload(file: UploadFile) -> tuple[io.BytesIO, str, str]:
    """
    Validate and return the uploaded file as a BytesIO stream.

    Args:
        file: FastAPI UploadFile from the multipart form.

    Returns:
        (stream, filename, file_type) — stream is a BytesIO ready to be read.

    Raises:
        HTTPException 400: Invalid extension or oversized file.
    """
    filename = file.filename or "resume"
    file_type = _resolve_extension(filename)

    content: bytes = await file.read()

    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB. "
                f"Received {len(content) / (1024 * 1024):.1f} MB."
            ),
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    logger.info(
        "Accepted upload: '%s' (%s, %.1f KB)",
        filename,
        file_type,
        len(content) / 1024,
    )

    return io.BytesIO(content), filename, file_type


def save_to_disk(
    content: Union[bytes, io.BytesIO],
    filename: str,
    subdir: str = "",
) -> Path:
    """
    Persist a file to the upload directory.
    Returns the saved file path.

    Used for debugging and audit logging.
    """
    upload_root = Path(settings.UPLOAD_DIR)
    if subdir:
        upload_root = upload_root / subdir
    upload_root.mkdir(parents=True, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}_{filename}"
    dest = upload_root / unique_name

    if isinstance(content, io.BytesIO):
        content.seek(0)
        raw = content.read()
        content.seek(0)
    else:
        raw = content

    dest.write_bytes(raw)
    logger.debug("Saved upload to: %s", dest)
    return dest


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_extension(filename: str) -> str:
    """
    Extract and validate the file extension.

    Returns:
        Lowercase extension without the dot (e.g. "pdf").

    Raises:
        HTTPException 400: If extension is not allowed.
    """
    suffix = Path(filename).suffix.lower().lstrip(".")

    if not suffix:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not determine file type. Upload a .pdf or .docx file.",
        )

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type: '.{suffix}'. "
                "Only PDF and DOCX resumes are accepted."
            ),
        )

    return suffix
