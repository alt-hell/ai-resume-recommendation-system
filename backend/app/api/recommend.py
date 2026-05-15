"""
recommend.py  — GET /recommend/{resume_id}
-------------------------------------------
Runs the ML recommendation engine on a stored resume:
  - Loads normalized skills from in-memory store
  - Predicts the best-matching job role (XGBoost or rule-based)
  - Computes skill gap against role requirements
  - Builds a prioritized learning path
  - Returns full RecommendationResponse
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, status

from app.database.memory import get_recommendations_collection, get_resumes_collection
from app.database.schemas import RecommendationResponse, SkillGap
from app.services.recommendation_engine import predict_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recommend", tags=["Recommendations"])


@router.get(
    "/{resume_id}",
    response_model=RecommendationResponse,
    summary="Get career recommendations for a resume",
    description=(
        "Uses the pre-trained XGBoost model to predict the best-matching job role "
        "from the resume's normalized skills, then returns the skill gap, "
        "matched skills, learning path, and salary range."
    ),
)
async def get_recommendation(
    resume_id: str = Path(..., description="resume_id from the /upload response"),
):
    """Predict role, compute gap, build learning path, persist, and return."""

    # ── 1. Load the stored resume ─────────────────────────────────────────────
    resumes = get_resumes_collection()
    doc = await resumes.find_one({"_id": resume_id})

    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resume '{resume_id}' not found. Upload your resume first via POST /upload.",
        )

    normalized_skills: list[str] = doc.get("normalized_skills", [])
    projects_text: Optional[str] = doc.get("projects_text")

    if not normalized_skills:
        # ── Return course suggestions instead of 422 ─────────────────────────
        correlation_courses = [
            {
                "title": "Business Analytics Program",
                "icon_type": "briefcase",
                "provider": "TheCorrelation",
                "duration": "3 Months",
                "mode": "Online + Live Sessions",
                "description": "Master the art of transforming business data into strategic decisions. Learn to build dashboards, interpret KPIs, and drive growth with data-backed insights.",
                "benefits": [
                    "Industry-aligned curriculum designed with hiring managers",
                    "Real-world capstone projects with live datasets",
                    "1-on-1 mentorship from industry professionals",
                    "Placement assistance and interview preparation",
                ],
                "skills_covered": ["SQL", "Excel", "Power BI", "Tableau", "Statistics", "Python"],
                "career_outcomes": {
                    "salary_range": "6 - 15 LPA",
                    "roles": ["Business Analyst", "Data Analyst", "MIS Analyst", "Strategy Analyst"],
                },
                "url": "https://thecorrelation.in",
            },
            {
                "title": "Data Science Elevate Program",
                "icon_type": "beaker",
                "provider": "TheCorrelation",
                "duration": "4 Months",
                "mode": "Online + Live Sessions",
                "description": "Build predictive models, work with machine learning algorithms, and master the complete data science pipeline from data wrangling to deployment.",
                "benefits": [
                    "Hands-on projects across healthcare, finance, and e-commerce",
                    "Learn from IIT/IIM alumni and industry experts",
                    "End-to-end ML pipeline building and deployment",
                    "Resume building and portfolio development support",
                ],
                "skills_covered": ["Python", "Machine Learning", "Pandas", "scikit-learn", "Statistics", "Deep Learning"],
                "career_outcomes": {
                    "salary_range": "8 - 25 LPA",
                    "roles": ["Data Scientist", "ML Engineer", "AI Developer", "Research Analyst"],
                },
                "url": "https://thecorrelation.in/courses/chartered-data-science",
            },
            {
                "title": "Data Analytics Mastery",
                "icon_type": "chart",
                "provider": "TheCorrelation",
                "duration": "2.5 Months",
                "mode": "Online + Live Sessions",
                "description": "Transform raw data into compelling stories and actionable insights. No prior coding experience required — start your analytics career from scratch.",
                "benefits": [
                    "Zero-to-hero curriculum for complete beginners",
                    "Interactive dashboard building with real company data",
                    "Dedicated career support and job referrals",
                    "Lifetime access to course materials and community",
                ],
                "skills_covered": ["SQL", "Excel", "Tableau", "Power BI", "Python Basics", "Data Visualization"],
                "career_outcomes": {
                    "salary_range": "5 - 12 LPA",
                    "roles": ["Data Analyst", "BI Analyst", "Reporting Analyst", "Analytics Consultant"],
                },
                "url": "https://thecorrelation.in/courses/applied-data-analytics",
            },
            {
                "title": "Generative AI & LLM Engineering",
                "icon_type": "chip",
                "provider": "TheCorrelation",
                "duration": "3 Months",
                "mode": "Online + Live Sessions",
                "description": "Master the most in-demand skill of 2025. Learn to build AI-powered applications, fine-tune large language models, and architect production-grade GenAI systems.",
                "benefits": [
                    "Build 5+ GenAI projects including RAG and AI agents",
                    "Learn prompt engineering, LangChain, and vector databases",
                    "Industry-recognized certification upon completion",
                    "Access to exclusive GenAI job board and referrals",
                ],
                "skills_covered": ["Python", "Prompt Engineering", "LangChain", "OpenAI API", "RAG", "Vector Databases"],
                "career_outcomes": {
                    "salary_range": "10 - 30 LPA",
                    "roles": ["GenAI Engineer", "LLM Developer", "AI Solutions Architect", "Prompt Engineer"],
                },
                "url": "https://thecorrelation.in",
            },
        ]

        no_skills_doc = {
            "resume_id": resume_id,
            "predicted_role": "Career Starter",
            "confidence": 0.0,
            "role_description": "Begin your career journey with industry-leading programs from TheCorrelation.",
            "salary_range_inr": {"min": 500000, "max": 3000000},
            "candidate_skills": [],
            "skill_gap": [],
            "matched_skills": [],
            "top_3_roles": [],
            "learning_path": ["SQL", "Python", "Excel", "Statistics", "Data Visualization"],
            "estimated_gap_weeks": 12,
            "domain_fit_percentage": 0.0,
            "advanced_insights": (
                "We could not detect any technical skills from your resume. "
                "This is a great starting point — explore our curated programs below "
                "to build a strong foundation in high-demand career fields."
            ),
            "project_skills": [],
            "course_recommendation": None,
            "interview_prep": [],
            "action_verb_feedback": None,
            "is_general_skills_user": True,
            "career_exploration_suggestions": [],
            "is_no_skills_user": True,
            "correlation_courses": correlation_courses,
            "generated_at": datetime.utcnow(),
        }

        recs = get_recommendations_collection()
        await recs.replace_one({"resume_id": resume_id}, no_skills_doc, upsert=True)
        logger.info("No-skills response stored for resume=%s", resume_id)
        return RecommendationResponse(**no_skills_doc)

    try:
        from app.services.recommendation_engine import recommend
        result = await recommend(normalized_skills, target_role=None, projects_text=projects_text)
    except Exception as exc:
        logger.error("Recommendation engine failed for '%s': %s", resume_id, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation engine error: {str(exc)}",
        )

    from app.core.constants import ROLE_DESCRIPTIONS, ROLE_SALARY_RANGES, LEARNING_RESOURCES

    role = result.predicted_role
    role_description = ROLE_DESCRIPTIONS.get(role, f"Professional in {role}")
    salary_range_inr = ROLE_SALARY_RANGES.get(role, {"min": 800000, "max": 2500000})

    # Assemble skill gap list
    skill_gap_out = []
    if result.skill_gap:
        for sk in result.skill_gap.essential_missing:
            res = LEARNING_RESOURCES.get(sk, {}).get("url", None)
            yt_url = f"https://www.youtube.com/results?search_query=Learn+{sk.replace(' ', '+')}+tutorial+2025"
            skill_gap_out.append({"skill": sk, "category": "essential", "is_core": True, "learning_resource": res, "youtube_url": yt_url})
        for sk in result.skill_gap.recommended_missing:
            res = LEARNING_RESOURCES.get(sk, {}).get("url", None)
            yt_url = f"https://www.youtube.com/results?search_query=Learn+{sk.replace(' ', '+')}+tutorial+2025"
            skill_gap_out.append({"skill": sk, "category": "recommended", "is_core": False, "learning_resource": res, "youtube_url": yt_url})

    essential_count = len(result.skill_gap.essential_missing) if result.skill_gap else 0
    estimated_gap_weeks = max(1, essential_count * 2)

    learning_path = result.skill_gap.essential_missing[:5] if result.skill_gap else []

    top_3_roles = [r.to_dict() for r in result.all_role_scores[:3]]
    
    # Calculate matched skills
    missing_set = set()
    if result.skill_gap:
        missing_set = set(result.skill_gap.essential_missing + result.skill_gap.recommended_missing)
    matched_skills = [s for s in result.user_skills if s not in missing_set]

    # ── Detect general/basic skills users ──────────────────────────────────────
    GENERAL_SKILLS = {
        "excel", "advanced excel", "communication", "leadership", "teamwork",
        "problem solving", "time management", "project management", "agile",
        "presentation", "microsoft office", "word", "powerpoint", "outlook",
        "google sheets", "management", "analytical thinking", "critical thinking",
        "negotiation", "customer service", "sales", "marketing", "hr",
        "accounting", "finance", "operations", "logistics", "supply chain",
    }
    user_skills_lower = {s.lower() for s in result.user_skills}
    general_count = len(user_skills_lower & GENERAL_SKILLS)
    is_general = general_count >= (len(result.user_skills) * 0.5) or result.confidence < 0.35

    career_exploration = []
    if is_general:
        career_exploration = [
            {
                "title": "Data Analytics",
                "icon_type": "chart",
                "description": "Transform raw data into actionable business insights. No coding prerequisites -- start with Excel and SQL.",
                "why_learn": "Data Analytics is one of the fastest-growing fields with 25%+ YoY job growth. Average salary: 6-15 LPA.",
                "prerequisites": "Basic computer skills and logical thinking -- you already have these!",
                "skills_to_learn": ["SQL", "Excel", "Tableau", "Power BI", "Python basics"],
                "explore_url": "https://thecorrelation.in/courses/applied-data-analytics",
                "youtube_url": "https://www.youtube.com/results?search_query=data+analytics+roadmap+for+beginners+2025",
            },
            {
                "title": "Business Analytics",
                "icon_type": "briefcase",
                "description": "Use data to drive strategic business decisions. Perfect for professionals with business domain knowledge.",
                "why_learn": "Companies need professionals who combine business acumen with data skills. Average salary: 8-18 LPA.",
                "prerequisites": "Business understanding and analytical mindset -- your existing skills are a huge advantage!",
                "skills_to_learn": ["SQL", "Statistics", "Tableau", "Power BI", "Python"],
                "explore_url": "https://thecorrelation.in/courses/chartered-bussiness-analytics",
                "youtube_url": "https://www.youtube.com/results?search_query=business+analytics+career+guide+2025",
            },
            {
                "title": "Data Science",
                "icon_type": "beaker",
                "description": "Build predictive models and uncover hidden patterns in data using ML and statistics.",
                "why_learn": "Data Science remains the #1 most sought-after tech role. Average salary: 10-25 LPA.",
                "prerequisites": "Start with Python basics and math -- structured programs make it easy to learn step by step.",
                "skills_to_learn": ["Python", "Statistics", "Machine Learning", "Pandas", "scikit-learn"],
                "explore_url": "https://thecorrelation.in/courses/chartered-data-science",
                "youtube_url": "https://www.youtube.com/results?search_query=data+science+roadmap+for+beginners+2025",
            },
            {
                "title": "Generative AI & LLMs",
                "icon_type": "chip",
                "description": "Work with cutting-edge AI models like ChatGPT, build AI applications, and automate workflows.",
                "why_learn": "GenAI is the hottest field in tech right now with massive demand and premium salaries. Average salary: 12-30 LPA.",
                "prerequisites": "Basic Python knowledge is enough to start -- many no-code tools available too!",
                "skills_to_learn": ["Python", "Prompt Engineering", "LangChain", "OpenAI API", "RAG"],
                "explore_url": "https://thecorrelation.in",
                "youtube_url": "https://www.youtube.com/results?search_query=generative+ai+career+roadmap+2025",
            },
        ]

    # ── 3. Persist recommendation ─────────────────────────────────────────────
    rec_doc = {
        "resume_id": resume_id,
        "predicted_role": role,
        "confidence": result.confidence,
        "role_description": role_description,
        "salary_range_inr": salary_range_inr,
        "candidate_skills": result.user_skills,
        "skill_gap": skill_gap_out,
        "matched_skills": matched_skills,
        "top_3_roles": top_3_roles,
        "learning_path": learning_path,
        "estimated_gap_weeks": estimated_gap_weeks,
        "domain_fit_percentage": result.domain_fit_percentage,
        "advanced_insights": result.advanced_insights,
        "project_skills": result.project_skills,
        "course_recommendation": result.course_recommendation,
        "interview_prep": result.interview_prep,
        "action_verb_feedback": result.action_verb_feedback,
        "is_general_skills_user": is_general,
        "career_exploration_suggestions": career_exploration,
        "is_no_skills_user": False,
        "correlation_courses": [],
        "generated_at": datetime.utcnow(),
    }

    recs = get_recommendations_collection()
    await recs.replace_one(
        {"resume_id": resume_id},
        rec_doc,
        upsert=True,
    )

    logger.info(
        "Recommendation stored: resume=%s role='%s' confidence=%.2f gap=%d general=%s",
        resume_id,
        role,
        result.confidence,
        len(skill_gap_out),
        is_general,
    )

    # ── 4. Build response ─────────────────────────────────────────────────────
    return RecommendationResponse(**rec_doc)
