"""
job_links.py  — GET /job-links/{resume_id}
-------------------------------------------
Returns top 5 real job application links for the user's predicted role.

Uses JSearch API (via RapidAPI) for live job search results,
with a fallback to smart platform search URLs.
"""

import logging

from fastapi import APIRouter, HTTPException, Path, status

from app.database.memory import get_recommendations_collection, get_resumes_collection
from app.services.job_links import generate_job_links

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/job-links", tags=["Job Links"])


@router.get(
    "/{resume_id}",
    summary="Get top 5 job application links for a resume",
    description=(
        "Returns real job listings matching the user's predicted role and skills. "
        "Uses JSearch API for live data, with fallback to search URLs. "
        "Run POST /upload first to get a resume_id."
    ),
)
async def get_job_links(
    resume_id: str = Path(..., description="resume_id from /upload"),
):
    """Get job application links based on resume analysis."""

    # ── 1. Load resume ────────────────────────────────────────────────────
    resumes = get_resumes_collection()
    resume_doc = await resumes.find_one({"_id": resume_id})

    if resume_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' not found.",
        )

    normalized_skills: list[str] = resume_doc.get("normalized_skills", [])

    if not normalized_skills:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No skills found. Upload resume first via POST /upload.",
        )

    # ── 2. Get predicted role ─────────────────────────────────────────────
    # Try stored recommendation first
    recs = get_recommendations_collection()
    rec_doc = await recs.find_one({"resume_id": resume_id})

    if rec_doc:
        predicted_role = rec_doc.get("predicted_role", "")
    else:
        # Quick prediction
        from app.services.recommendation_engine import predict_role
        predicted_role, _ = predict_role(normalized_skills)

    if not predicted_role:
        predicted_role = "Software Developer"  # Safe fallback

    # ── 3. Generate job links ─────────────────────────────────────────────
    try:
        result = await generate_job_links(
            predicted_role=predicted_role,
            skills=normalized_skills,
            location="India",
            num_results=5,
        )
    except Exception as exc:
        logger.error("Job links generation failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job links generation failed: {str(exc)}",
        )

    # ── 4. Build response ─────────────────────────────────────────────────
    return {
        "resume_id": resume_id,
        "predicted_role": predicted_role,
        "source": result.source,
        "total_found": result.total_found,
        "jobs": [j.to_dict() for j in result.jobs],
    }
