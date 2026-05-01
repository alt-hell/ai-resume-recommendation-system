"""
trends.py  — GET /trends
--------------------------
Returns aggregated skill demand trends computed from the job dataset.

Query params:
  - top_n       : How many skills to return (default 30, max 100)
  - category    : Filter by skill category (optional)
  - role        : Filter trends for a specific job role (optional)
"""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.database.schemas import TrendResponse
from app.services.trend_analysis import get_skill_trends, get_trending_skills_for_role
from app.core.constants import JOB_ROLES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trends", tags=["Skill Trends"])


@router.get(
    "",
    response_model=TrendResponse,
    summary="Get overall skill demand trends",
    description=(
        "Returns the most in-demand skills across all job roles, "
        "computed from the job dataset. Results include demand scores (0–1), "
        "trend labels ('rising' / 'stable' / 'declining'), and category grouping."
    ),
)
async def skill_trends(
    top_n: int = Query(default=30, ge=5, le=100, description="Number of top skills to return"),
    category: str | None = Query(default=None, description="Filter by skill category"),
):
    """Return global skill demand trends, optionally filtered by category."""
    try:
        data = get_skill_trends(top_n=top_n)
    except Exception as exc:
        logger.error("Trend analysis failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Trend analysis failed: {str(exc)}",
        )

    top_skills = data["top_skills"]
    by_category = data["by_category"]

    # Apply category filter if requested
    if category:
        cat_lower = category.lower()
        top_skills = [s for s in top_skills if s["category"].lower() == cat_lower]
        by_category = {
            k: v for k, v in by_category.items()
            if k.lower() == cat_lower
        }

        if not top_skills:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No skills found for category '{category}'.",
            )

    return TrendResponse(
        total_jobs_analyzed=data["total_jobs_analyzed"],
        top_skills=top_skills,
        by_category=by_category,
    )


@router.get(
    "/role/{role_name}",
    summary="Get top skills for a specific job role",
    description=(
        "Returns the most in-demand skills specifically for the given job role. "
        f"Available roles: {', '.join(JOB_ROLES[:5])}, ..."
    ),
)
async def role_specific_trends(
    role_name: str,
    top_n: int = Query(default=10, ge=3, le=20),
):
    """Return top skills for a given job role."""
    # Normalize role name (handle URL encoding like %20 for spaces)
    role_name = role_name.replace("%20", " ").strip()

    # Validate role
    role_lower = role_name.lower()
    matched_role = next(
        (r for r in JOB_ROLES if r.lower() == role_lower), None
    )

    if matched_role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Role '{role_name}' not recognized. "
                f"Available roles: {JOB_ROLES}"
            ),
        )

    try:
        skills = get_trending_skills_for_role(matched_role, top_n=top_n)
    except Exception as exc:
        logger.error("Role trend analysis failed for '%s': %s", matched_role, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return {
        "role": matched_role,
        "top_skills": skills,
        "count": len(skills),
    }
