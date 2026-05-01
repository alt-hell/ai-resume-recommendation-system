"""
extract.py  — POST /extract-skills
------------------------------------
Re-runs skill extraction on a previously uploaded resume (by resume_id),
or accepts raw text directly for ad-hoc extraction.

Useful for:
  - Debugging the extraction pipeline
  - Re-extracting after registry updates
  - Extracting from pasted text without file upload
"""

import logging

from fastapi import APIRouter, Body, HTTPException, Path, status

from app.database.memory import get_resumes_collection
from app.database.schemas import SkillExtractionResponse
from app.services.normalization import normalize_skills
from app.services.skill_extractor import extract_skills

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extract-skills", tags=["Skill Extraction"])


# ─────────────────────────────────────────────────────────────────────────────
# Re-extract from a stored resume
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/{resume_id}",
    response_model=SkillExtractionResponse,
    summary="Re-run skill extraction for a stored resume",
    description=(
        "Fetches a previously uploaded resume by ID and re-runs the full "
        "extraction + normalization pipeline. Updates the stored skills."
    ),
)
async def reextract_skills(
    resume_id: str = Path(..., description="resume_id from the /upload response"),
):
    """Re-extract skills from an existing resume document."""
    collection = get_resumes_collection()

    doc = await collection.find_one({"_id": resume_id})
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' not found.",
        )

    cleaned_text: str = doc.get("cleaned_text") or doc.get("raw_text", "")
    if not cleaned_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Stored resume has no extractable text.",
        )

    # Re-run extraction
    extraction = await extract_skills(cleaned_text)
    norm_result = normalize_skills(extraction.skills)
    projects_text = doc.get("projects_text")

    # Update the stored document
    await collection.update_one(
        {"_id": resume_id},
        {
            "$set": {
                "raw_skills": extraction.skills,
                "normalized_skills": norm_result.normalized,
                "unknown_skills": norm_result.unknown,
                "skill_categories": norm_result.categories,
                "extraction_source": extraction.source,
                "extraction_confidence": extraction.confidence,
                "match_rate": norm_result.match_rate,
            }
        },
    )

    return SkillExtractionResponse(
        resume_id=resume_id,
        filename=doc.get("filename", "unknown"),
        file_type=doc.get("file_type", "unknown"),
        extraction_source=extraction.source,
        extraction_confidence=round(extraction.confidence, 3),
        raw_skills=extraction.skills,
        normalized_skills=norm_result.normalized,
        unknown_skills=norm_result.unknown,
        skill_categories=norm_result.categories,
        match_rate=round(norm_result.match_rate, 3),
        total_skills=norm_result.known_count,
        projects_text=projects_text,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ad-hoc text extraction (no file upload needed)
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    summary="Extract skills from raw text (no file upload)",
    description=(
        "Send plain resume text in the request body and get back normalized skills. "
        "Nothing is stored — for quick testing only."
    ),
)
async def extract_from_text(
    text: str = Body(..., embed=True, description="Raw resume text"),
):
    """Extract and normalize skills from a plain text snippet."""
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request body 'text' must not be empty.",
        )

    extraction = await extract_skills(text)
    norm_result = normalize_skills(extraction.skills)

    return {
        "extraction_source": extraction.source,
        "extraction_confidence": round(extraction.confidence, 3),
        "raw_skills": extraction.skills,
        "normalized_skills": norm_result.normalized,
        "unknown_skills": norm_result.unknown,
        "skill_categories": norm_result.categories,
        "match_rate": round(norm_result.match_rate, 3),
        "total_skills": norm_result.known_count,
    }
