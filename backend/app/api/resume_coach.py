"""
resume_coach.py  — GET /resume-coach/{resume_id}
--------------------------------------------------
Generates personalized resume improvement advice:
  - Resume quality score (broken down by category)
  - Improvement tips tailored to the user's resume
  - Project suggestions based on target role + skill gaps
  - Perfect resume blueprint for the target role
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, status

from app.database.memory import get_resumes_collection, get_recommendations_collection
from app.core.constants import (
    PROJECT_SUGGESTIONS, RESUME_TIPS, ROLE_SKILL_MAP,
    LEARNING_RESOURCES, ROLE_DESCRIPTIONS,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resume-coach", tags=["Resume Coach"])


def _calculate_resume_score(resume_doc: dict, rec_doc: Optional[dict]) -> dict:
    """
    Calculate a breakdown resume score (0-100).
    
    Categories:
      - skills_score (35%): How well skills match target role
      - projects_score (25%): Project section quality
      - structure_score (20%): Resume structure quality
      - action_verbs_score (20%): Use of strong action verbs
    """
    # Skills score: based on match rate and number of skills
    normalized_skills = resume_doc.get("normalized_skills", [])
    total_skills = len(normalized_skills)
    match_rate = resume_doc.get("match_rate", 0)
    
    if total_skills >= 10:
        skills_score = min(100, match_rate * 100 * 0.7 + 30)
    elif total_skills >= 5:
        skills_score = min(85, match_rate * 100 * 0.6 + 20)
    else:
        skills_score = min(50, total_skills * 10)

    # Projects score: based on projects_text presence and quality
    projects_text = resume_doc.get("projects_text", "") or ""
    if len(projects_text) > 500:
        projects_score = 85
    elif len(projects_text) > 200:
        projects_score = 65
    elif len(projects_text) > 50:
        projects_score = 40
    else:
        projects_score = 15

    # Check if project skills are backed
    if rec_doc:
        project_skills = rec_doc.get("project_skills", [])
        if len(project_skills) >= 3:
            projects_score = min(100, projects_score + 15)

    # Structure score: based on text length, sections, formatting
    raw_text = resume_doc.get("raw_text", "") or ""
    text_len = len(raw_text)
    if 800 <= text_len <= 5000:
        structure_score = 80
    elif 400 <= text_len < 800:
        structure_score = 60
    elif text_len > 5000:
        structure_score = 55  # Too long
    else:
        structure_score = 30  # Too short

    # Check for common sections
    text_lower = raw_text.lower()
    section_keywords = ["experience", "education", "skills", "projects", "summary", "objective"]
    sections_found = sum(1 for kw in section_keywords if kw in text_lower)
    structure_score = min(100, structure_score + sections_found * 5)

    # Action verbs score
    action_verbs = {"developed", "architected", "built", "created", "designed",
                    "implemented", "managed", "led", "optimized", "spearheaded",
                    "engineered", "integrated", "deployed", "automated", "improved",
                    "reduced", "increased", "launched", "delivered", "maintained"}
    found_verbs = [v for v in action_verbs if v in text_lower]
    if len(found_verbs) >= 6:
        action_verbs_score = 95
    elif len(found_verbs) >= 4:
        action_verbs_score = 75
    elif len(found_verbs) >= 2:
        action_verbs_score = 55
    else:
        action_verbs_score = 20

    # Weighted total
    overall = (
        skills_score * 0.35 +
        projects_score * 0.25 +
        structure_score * 0.20 +
        action_verbs_score * 0.20
    )

    return {
        "overall": round(overall),
        "skills_score": round(skills_score),
        "projects_score": round(projects_score),
        "structure_score": round(structure_score),
        "action_verbs_score": round(action_verbs_score),
        "total_skills": total_skills,
        "action_verbs_found": len(found_verbs),
        "sections_found": sections_found,
    }


def _generate_improvement_tips(resume_doc: dict, rec_doc: Optional[dict], score: dict) -> list[dict]:
    """Generate personalized improvement tips based on resume analysis."""
    tips = []
    priority_counter = 0

    # Skills-based tips
    if score["total_skills"] < 5:
        priority_counter += 1
        tips.append({
            "category": "skills",
            "priority": "high",
            "tip": "Add more technical skills to your resume",
            "detail": f"Only {score['total_skills']} skills were detected. Aim for 8-12 relevant skills grouped by category.",
            "order": priority_counter,
        })

    unknown_skills = resume_doc.get("unknown_skills", [])
    if len(unknown_skills) > 3:
        priority_counter += 1
        tips.append({
            "category": "skills",
            "priority": "medium",
            "tip": "Use industry-standard skill names",
            "detail": f"{len(unknown_skills)} skills weren't recognized. Use standard names like 'React' instead of 'ReactJS framework'.",
            "order": priority_counter,
        })

    # Project-based tips
    projects_text = resume_doc.get("projects_text", "") or ""
    if len(projects_text) < 50:
        priority_counter += 1
        tips.append({
            "category": "projects",
            "priority": "high",
            "tip": "Add a dedicated projects section",
            "detail": "No significant projects section was detected. Add 2-3 impactful projects with problem statement, tech stack, and outcome.",
            "order": priority_counter,
        })
    elif len(projects_text) < 200:
        priority_counter += 1
        tips.append({
            "category": "projects",
            "priority": "medium",
            "tip": "Expand your project descriptions",
            "detail": "Your projects section is thin. For each project, describe the problem, your approach, technologies used, and measurable impact.",
            "order": priority_counter,
        })

    # Action verb tips
    if score["action_verbs_found"] < 3:
        priority_counter += 1
        tips.append({
            "category": "content",
            "priority": "high",
            "tip": "Use stronger action verbs",
            "detail": "Start bullet points with powerful verbs: Developed, Architected, Optimized, Deployed, Engineered, Automated.",
            "order": priority_counter,
        })

    # Structure tips
    if score["sections_found"] < 4:
        priority_counter += 1
        tips.append({
            "category": "structure",
            "priority": "medium",
            "tip": "Include all essential resume sections",
            "detail": "A strong resume needs: Summary, Experience/Projects, Skills, Education. Add any missing sections.",
            "order": priority_counter,
        })

    # Skill gap tips (from recommendation)
    if rec_doc:
        skill_gap = rec_doc.get("skill_gap", [])
        core_gaps = [g for g in skill_gap if g.get("is_core")]
        if core_gaps:
            gap_names = [g["skill"] for g in core_gaps[:3]]
            priority_counter += 1
            tips.append({
                "category": "skills",
                "priority": "high",
                "tip": f"Learn core skills: {', '.join(gap_names)}",
                "detail": f"These are essential skills for your target role that are missing from your resume. Prioritize learning them.",
                "order": priority_counter,
            })

    # Add generic tips from RESUME_TIPS that are relevant
    for category, cat_tips in RESUME_TIPS.items():
        for t in cat_tips:
            # Only add a few generic tips if we don't have many specific ones
            if len(tips) < 8:
                priority_counter += 1
                tips.append({
                    "category": category,
                    "priority": "low",
                    "tip": t["tip"],
                    "detail": t["detail"],
                    "order": priority_counter,
                })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tips.sort(key=lambda x: (priority_order.get(x["priority"], 3), x["order"]))

    return tips[:12]  # Cap at 12 tips


def _get_project_suggestions(predicted_role: str, skill_gap: list) -> list[dict]:
    """Get project suggestions for the predicted role."""
    suggestions = PROJECT_SUGGESTIONS.get(predicted_role, [])

    # If no exact match, try partial match
    if not suggestions:
        for role_key, projects in PROJECT_SUGGESTIONS.items():
            if any(word in predicted_role for word in role_key.split()):
                suggestions = projects
                break

    # If still empty, return generic full-stack projects
    if not suggestions:
        suggestions = PROJECT_SUGGESTIONS.get("Full Stack Developer", [])

    # Prioritize projects that use skills from the gap
    gap_skills = {g.get("skill", "").lower() for g in skill_gap} if skill_gap else set()

    def _relevance(project):
        tech = {t.lower() for t in project.get("tech_stack", [])}
        return len(tech & gap_skills)

    suggestions = sorted(suggestions, key=_relevance, reverse=True)

    return suggestions[:5]


def _build_resume_blueprint(predicted_role: str, normalized_skills: list, skill_gap: list) -> dict:
    """Build a 'perfect resume' blueprint for the target role."""
    role_skills = ROLE_SKILL_MAP.get(predicted_role, {})
    required = role_skills.get("required", [])
    bonus = role_skills.get("bonus", [])

    user_set = {s.lower() for s in normalized_skills}
    
    required_status = []
    for skill in required:
        required_status.append({
            "skill": skill,
            "have": skill.lower() in user_set,
        })

    bonus_status = []
    for skill in bonus:
        bonus_status.append({
            "skill": skill,
            "have": skill.lower() in user_set,
        })

    sections_checklist = [
        {"section": "Professional Summary", "description": f"2-3 lines positioning yourself as a {predicted_role} candidate"},
        {"section": "Technical Skills", "description": "Grouped by: Languages, Frameworks, Databases, Cloud, Tools"},
        {"section": "Projects", "description": f"2-3 projects demonstrating {predicted_role} capabilities with measurable outcomes"},
        {"section": "Experience", "description": "Reverse chronological with quantified achievements using action verbs"},
        {"section": "Education", "description": "Degree, institution, graduation year, relevant coursework"},
        {"section": "Certifications", "description": "Industry certifications relevant to this role"},
    ]

    return {
        "target_role": predicted_role,
        "required_skills": required_status,
        "bonus_skills": bonus_status,
        "required_coverage": sum(1 for s in required_status if s["have"]) / max(len(required_status), 1) * 100,
        "sections_checklist": sections_checklist,
    }


@router.get(
    "/{resume_id}",
    summary="Get personalized resume coaching",
    description=(
        "Analyzes the uploaded resume and generates personalized improvement advice, "
        "project suggestions, resume quality score, and a blueprint for the ideal resume."
    ),
)
async def get_resume_coaching(
    resume_id: str = Path(..., description="resume_id from the /upload response"),
):
    """Generate comprehensive resume coaching."""

    # Load resume
    resumes = get_resumes_collection()
    resume_doc = await resumes.find_one({"_id": resume_id})

    if resume_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' not found. Upload your resume first.",
        )

    # Load recommendation (may not exist yet)
    recs = get_recommendations_collection()
    rec_doc = await recs.find_one({"resume_id": resume_id})

    predicted_role = rec_doc.get("predicted_role", "Full Stack Developer") if rec_doc else "Full Stack Developer"
    skill_gap = rec_doc.get("skill_gap", []) if rec_doc else []
    normalized_skills = resume_doc.get("normalized_skills", [])

    # Generate coaching data
    score = _calculate_resume_score(resume_doc, rec_doc)
    tips = _generate_improvement_tips(resume_doc, rec_doc, score)
    projects = _get_project_suggestions(predicted_role, skill_gap)
    blueprint = _build_resume_blueprint(predicted_role, normalized_skills, skill_gap)

    logger.info(
        "Resume coaching generated: resume=%s role='%s' score=%d tips=%d projects=%d",
        resume_id, predicted_role, score["overall"], len(tips), len(projects),
    )

    return {
        "resume_id": resume_id,
        "predicted_role": predicted_role,
        "score": score,
        "improvement_tips": tips,
        "project_suggestions": projects,
        "blueprint": blueprint,
        "has_recommendation": rec_doc is not None,
    }
