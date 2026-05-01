"""
upload.py  — POST /upload
--------------------------
Accepts a resume file (PDF or DOCX), parses it, cleans the text,
extracts + normalizes skills, persists to MongoDB, and returns
the full extraction result.

This is the primary entry point — all other endpoints reference
the `resume_id` returned here.
"""

import asyncio
import logging
import time
from datetime import datetime

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.database.memory import get_resumes_collection
from app.database.schemas import SkillExtractionResponse
from app.services.normalization import normalize_skills
from app.services.resume_parser import parse_resume_from_bytes, ParsedResume
from app.services.skill_extractor import extract_skills
from app.utils.file_handler import read_upload
from app.utils.text_cleaner import clean_resume_text
from app.services.recommendation_engine import predict_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["Resume Upload"])


def _sync_pipeline(file_bytes: bytes, filename: str, file_type: str):
    """
    Run ALL CPU-bound work in a single synchronous function so it can
    be offloaded to a thread pool via asyncio.to_thread().
    This keeps the FastAPI event loop completely free.
    """
    t0 = time.perf_counter()

    # ── Parse raw text ────────────────────────────────────────────────────
    raw_text = parse_resume_from_bytes(file_bytes, filename)
    t1 = time.perf_counter()
    logger.info("⏱  Parse: %.0f ms", (t1 - t0) * 1000)

    parsed = ParsedResume(
        raw_text=raw_text,
        pages=[raw_text],
        file_type=file_type,
        page_count=1,
    )

    if parsed.is_empty:
        raise ValueError("No readable text found in the uploaded file.")

    # ── Clean text ────────────────────────────────────────────────────────
    cleaned = clean_resume_text(parsed)
    t2 = time.perf_counter()
    logger.info("⏱  Clean: %.0f ms", (t2 - t1) * 1000)

    return parsed, cleaned


@router.post(
    "",
    response_model=SkillExtractionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and analyze a resume",
    description=(
        "Upload a PDF or DOCX resume. The system parses the text, "
        "extracts skills using section-based + NER strategies, normalizes "
        "them to canonical forms, and stores the result in MongoDB. "
        "Returns a `resume_id` used by all downstream endpoints."
    ),
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF or DOCX resume file (max 10 MB)"),
):
    """
    Full pipeline: upload → parse → clean → extract → normalize → store → respond.
    """
    pipeline_start = time.perf_counter()

    # ── 1. Validate and read file ─────────────────────────────────────────────
    stream, filename, file_type = await read_upload(file)
    size_bytes = stream.getbuffer().nbytes

    logger.info("Processing upload: '%s' (%s, %d bytes)", filename, file_type, size_bytes)

    try:
        # ── 2 & 3. Parse + Clean (offloaded to thread pool) ───────────────────
        parsed, cleaned = await asyncio.to_thread(
            _sync_pipeline, stream.getvalue(), filename, file_type
        )

        if parsed.is_empty:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "No readable text found in the uploaded file. "
                    "Ensure the file is not password-protected or image-only."
                ),
            )

        # ── 4. Extract skills ─────────────────────────────────────────────────
        t3 = time.perf_counter()
        extraction = await extract_skills(cleaned.full_text)
        t4 = time.perf_counter()
        logger.info("⏱  Extract skills: %.0f ms", (t4 - t3) * 1000)

        # ── 5. Normalize skills ───────────────────────────────────────────────
        norm_result = await asyncio.to_thread(normalize_skills, extraction.skills)
        t5 = time.perf_counter()
        logger.info("⏱  Normalize: %.0f ms", (t5 - t4) * 1000)

        # ── Extract Projects Text & Fast Prediction ───────────────────────────
        projects_text = cleaned.sections.get("PROJECTS")
        predicted_role = None
        if norm_result.normalized:
            try:
                predicted_role, _ = await asyncio.to_thread(
                    predict_role, norm_result.normalized
                )
            except Exception as e:
                logger.warning(f"Fast prediction failed: {e}")
        t6 = time.perf_counter()
        logger.info("⏱  Predict role: %.0f ms", (t6 - t5) * 1000)

        # ── 6. Persist to MongoDB ─────────────────────────────────────────────
        doc = {
            "filename": filename,
            "file_type": file_type,
            "size_bytes": size_bytes,
            "raw_text": parsed.raw_text,
            "cleaned_text": cleaned.full_text,
            "raw_skills": extraction.skills,
            "normalized_skills": norm_result.normalized,
            "unknown_skills": norm_result.unknown,
            "skill_categories": norm_result.categories,
            "extraction_source": extraction.source,
            "extraction_confidence": extraction.confidence,
            "match_rate": norm_result.match_rate,
            "projects_text": projects_text,
            "predicted_role": predicted_role,
            "uploaded_at": datetime.utcnow(),
        }

        collection = get_resumes_collection()
        insert_result = await collection.insert_one(doc)
        resume_id = str(insert_result.inserted_id)

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        logger.info(
            "✅ Resume stored: id=%s, skills=%d, normalized=%d — TOTAL %.0f ms",
            resume_id,
            len(extraction.skills),
            len(norm_result.normalized),
            total_ms,
        )

        # ── 7. Return response ────────────────────────────────────────────────
        return SkillExtractionResponse(
            resume_id=resume_id,
            filename=filename,
            file_type=file_type,
            extraction_source=extraction.source,
            extraction_confidence=round(extraction.confidence, 3),
            raw_skills=extraction.skills,
            normalized_skills=norm_result.normalized,
            unknown_skills=norm_result.unknown,
            skill_categories=norm_result.categories,
            match_rate=round(norm_result.match_rate, 3),
            total_skills=norm_result.known_count,
            projects_text=projects_text,
            predicted_role=predicted_role,
        )

    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve),
        )
    except Exception as exc:
        logger.error("Upload pipeline failed for '%s': %s", filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process resume: {str(exc)}",
        )
