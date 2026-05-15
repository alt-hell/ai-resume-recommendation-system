"""
career_advisor.py — POST /career-advisor
------------------------------------------
AI-powered career advisor using Google Gemini API (free tier).
Fully context-aware: answers ONLY based on the user's uploaded resume.
Falls back to rule-based responses if API is unavailable.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.database.memory import get_resumes_collection, get_recommendations_collection
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/career-advisor", tags=["Career Advisor"])


class CareerQuestion(BaseModel):
    resume_id: Optional[str] = None
    question: str


# ── Generic prompts shown when no resume is uploaded ─────────────────────────
DEFAULT_PROMPTS = [
    "How do I transition from manual testing to DevOps?",
    "What certifications should I get for Data Science?",
    "How can I move from non-tech to data analytics?",
    "What is the career scope in GenAI and LLMs?",
    "What skills do I need for a cloud engineer role?",
    "How to build a portfolio for frontend development?",
    "What are the highest-paying tech roles in 2025?",
    "How to prepare for a system design interview?",
]

FALLBACK_RESPONSES = {
    "data": "Data Science and Analytics are among the most in-demand fields today. Start with Python, SQL, and statistics fundamentals. Platforms like Kaggle offer great hands-on practice. Focus on building projects that demonstrate your analytical thinking.",
    "devops": "DevOps engineers bridge development and operations. Key skills include Docker, Kubernetes, CI/CD pipelines, and cloud platforms (AWS/GCP/Azure). Start with Linux fundamentals and version control, then progress to containerization.",
    "frontend": "Modern frontend development revolves around React, TypeScript, and responsive design. Build a portfolio with 3-5 projects showcasing different skills. Learn about web performance, accessibility, and testing.",
    "backend": "Backend development requires strong fundamentals in a language (Python/Java/Node.js), databases (SQL + NoSQL), REST APIs, and system design. Focus on building scalable, well-tested applications.",
    "ml": "Machine Learning engineering combines ML theory with production engineering. Master Python, scikit-learn, TensorFlow/PyTorch, and MLOps tools. Deploy models using Docker and cloud services.",
    "career": "To advance your tech career: 1) Build a strong GitHub portfolio, 2) Contribute to open source, 3) Network on LinkedIn, 4) Get relevant certifications, 5) Practice system design interviews.",
    "default": "Focus on building practical skills through projects. The tech industry values demonstrated ability over credentials. Start with fundamentals, build projects, and continuously learn.",
}


def _get_fallback(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["data science", "data analyst", "analytics", "data"]):
        return FALLBACK_RESPONSES["data"]
    elif any(w in q for w in ["devops", "docker", "kubernetes", "ci/cd", "cloud"]):
        return FALLBACK_RESPONSES["devops"]
    elif any(w in q for w in ["frontend", "react", "ui", "ux", "web"]):
        return FALLBACK_RESPONSES["frontend"]
    elif any(w in q for w in ["backend", "api", "server", "database"]):
        return FALLBACK_RESPONSES["backend"]
    elif any(w in q for w in ["machine learning", "ml", "ai", "deep learning", "genai"]):
        return FALLBACK_RESPONSES["ml"]
    elif any(w in q for w in ["career", "salary", "job", "interview", "resume"]):
        return FALLBACK_RESPONSES["career"]
    return FALLBACK_RESPONSES["default"]


def _build_resume_context(resume_doc: dict, rec_doc: Optional[dict]) -> str:
    """
    Build a rich, structured resume context block for the LLM system prompt.
    This gives the AI deep knowledge of the user's background.
    """
    parts = []

    # Skills
    skills = resume_doc.get("normalized_skills", [])
    if skills:
        parts.append(f"CURRENT SKILLS: {', '.join(skills)}")

    # Skill categories
    categories = resume_doc.get("skill_categories", {})
    if categories:
        cat_lines = []
        for cat, cat_skills in categories.items():
            if cat_skills:
                cat_lines.append(f"  - {cat}: {', '.join(cat_skills)}")
        if cat_lines:
            parts.append("SKILL CATEGORIES:\n" + "\n".join(cat_lines))

    # Match rate & confidence
    match_rate = resume_doc.get("match_rate", 0)
    confidence = resume_doc.get("extraction_confidence", 0)
    if match_rate:
        parts.append(f"SKILL MATCH RATE: {round(match_rate * 100)}% of skills are industry-recognized")

    # Projects
    projects_text = resume_doc.get("projects_text", "")
    if projects_text and len(projects_text.strip()) > 20:
        # Truncate to ~500 chars to avoid token overuse
        truncated = projects_text.strip()[:500]
        parts.append(f"PROJECTS SECTION FROM RESUME:\n{truncated}")

    # Recommendation data (if available)
    if rec_doc:
        role = rec_doc.get("predicted_role", "")
        if role:
            parts.append(f"PREDICTED BEST-FIT ROLE: {role}")

        role_confidence = rec_doc.get("confidence", 0)
        if role_confidence:
            parts.append(f"ROLE MATCH CONFIDENCE: {round(role_confidence * 100)}%")

        domain_fit = rec_doc.get("domain_fit_percentage", 0)
        if domain_fit:
            parts.append(f"DOMAIN FIT: {round(domain_fit)}%")

        # Skill gaps
        gaps = rec_doc.get("skill_gap", [])
        if isinstance(gaps, list) and gaps:
            essential = [g.get("skill", "") for g in gaps if isinstance(g, dict) and g.get("is_core")]
            recommended = [g.get("skill", "") for g in gaps if isinstance(g, dict) and not g.get("is_core")]
            if essential:
                parts.append(f"ESSENTIAL MISSING SKILLS (must learn): {', '.join(essential)}")
            if recommended:
                parts.append(f"RECOMMENDED MISSING SKILLS (nice to have): {', '.join(recommended)}")

        # Matched skills
        matched = rec_doc.get("matched_skills", [])
        if matched:
            parts.append(f"SKILLS THAT MATCH TARGET ROLE: {', '.join(matched)}")

        # Learning path
        learning_path = rec_doc.get("learning_path", [])
        if learning_path:
            parts.append(f"RECOMMENDED LEARNING PATH: {' → '.join(learning_path)}")

        # Top 3 roles
        top_roles = rec_doc.get("top_3_roles", [])
        if top_roles:
            role_strs = []
            for r in top_roles:
                name = r.get("role", r.get("name", ""))
                score = r.get("score", r.get("confidence", 0))
                if name:
                    role_strs.append(f"{name} ({round(score * 100 if score <= 1 else score)}%)")
            if role_strs:
                parts.append(f"TOP 3 MATCHING ROLES: {', '.join(role_strs)}")

    return "\n".join(parts)


def _build_personalized_prompts(resume_doc: dict, rec_doc: Optional[dict]) -> list[str]:
    """Generate suggested prompts personalized to the user's resume profile."""
    prompts = []
    skills = resume_doc.get("normalized_skills", [])
    role = rec_doc.get("predicted_role", "") if rec_doc else ""
    gaps = rec_doc.get("skill_gap", []) if rec_doc else []
    essential_gaps = [g.get("skill", "") for g in gaps if isinstance(g, dict) and g.get("is_core")]

    if role:
        prompts.append(f"What should I focus on to become a stronger {role}?")
        prompts.append(f"What companies are hiring for {role} roles right now?")
        prompts.append(f"What projects should I build to showcase my {role} skills?")

    if essential_gaps:
        top_gap = essential_gaps[0]
        prompts.append(f"How do I quickly learn {top_gap}?")
        if len(essential_gaps) >= 2:
            prompts.append(f"What's the best roadmap to learn {essential_gaps[0]} and {essential_gaps[1]}?")

    if skills:
        prompts.append("Based on my skills, what alternative career paths can I explore?")
        prompts.append("How can I leverage my current skills for a higher salary?")

    prompts.append("What are the weakest areas of my resume and how can I fix them?")

    return prompts[:8]


@router.post(
    "",
    summary="Ask TheCorrelation AI Career Advisor a question",
    description=(
        "Uses Google Gemini API to provide career advice personalized to the user's "
        "uploaded resume. The AI only answers based on the user's resume context. "
        "Requires resume_id for context-aware responses."
    ),
)
async def ask_career_advisor(payload: CareerQuestion):
    """Generate AI-powered, resume-context-aware career advice."""
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    # ── Load user's resume context ────────────────────────────────────────
    resume_context = ""
    resume_doc = None
    rec_doc = None

    if payload.resume_id:
        resumes = get_resumes_collection()
        resume_doc = await resumes.find_one({"_id": payload.resume_id})
        if resume_doc:
            recs = get_recommendations_collection()
            rec_doc = await recs.find_one({"resume_id": payload.resume_id})
            resume_context = _build_resume_context(resume_doc, rec_doc)

    # ── Build context-aware system prompt ─────────────────────────────────
    if resume_context:
        system_instruction = (
            "You are a personalized AI Career Advisor. You have analyzed the user's resume "
            "and have detailed knowledge of their profile. You MUST answer ONLY based on the "
            "resume context provided below. Do NOT give generic advice — every answer must be "
            "specific to THIS user's skills, gaps, and predicted career role.\n\n"
            "RULES:\n"
            "- Always reference the user's actual skills, gaps, and predicted role in your answers.\n"
            "- If asked something completely unrelated to career/professional growth, politely redirect "
            "by saying you're a career advisor specialized for their resume profile.\n"
            "- Be encouraging but realistic about their current skill level.\n"
            "- Provide specific, actionable next steps they can take immediately.\n"
            "- Keep responses to 3-4 paragraphs max. Use bullet points where helpful.\n"
            "- Do not use markdown headers (no # or ##).\n"
            "- When suggesting skills to learn, prioritize from their essential missing skills list.\n\n"
            f"═══ USER'S RESUME PROFILE ═══\n{resume_context}\n═══ END PROFILE ═══"
        )
    else:
        system_instruction = (
            "You are an AI Career Advisor for tech professionals. "
            "The user has NOT uploaded a resume yet, so you don't have their profile context. "
            "Provide helpful general career advice, but remind them that uploading their resume "
            "will give them personalized, specific guidance based on their actual skills and gaps. "
            "Keep responses to 3-4 paragraphs max. Use bullet points where helpful. "
            "Do not use markdown headers."
        )

    user_prompt = question

    # ── Try Gemini API first ──────────────────────────────────────────────
    gemini_key = settings.GEMINI_API_KEY.strip().strip('"').strip("'")
    if gemini_key:
        try:
            import httpx

            gemini_payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": user_prompt}]}
                ],
                "systemInstruction": {
                    "parts": [{"text": system_instruction}]
                },
                "generationConfig": {
                    "temperature": 0.4,
                    "maxOutputTokens": 800,
                }
            }

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=gemini_payload)
                response.raise_for_status()
                data = response.json()

                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = parts[0].get("text", "").strip() if parts else ""
                    if content:
                        logger.info("Gemini career advice generated (context-aware=%s)", bool(resume_context))
                        return {
                            "answer": content,
                            "source": "ai",
                            "model": "gemini-2.0-flash",
                            "context_aware": bool(resume_context),
                        }

        except Exception as e:
            logger.error("Gemini API call failed: %s", e)

    # ── Try OpenRouter as second option ───────────────────────────────────
    if settings.OPENROUTER_API_KEY:
        try:
            import httpx

            payload_llm = {
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 600,
            }
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "AI Career Advisor",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload_llm,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                if content:
                    return {
                        "answer": content,
                        "source": "ai",
                        "model": settings.OPENROUTER_MODEL,
                        "context_aware": bool(resume_context),
                    }
        except Exception as e:
            logger.error("OpenRouter LLM call failed: %s", e)

    # ── Fallback to rule-based ────────────────────────────────────────────
    logger.info("Using fallback career advice (no API key configured or API failed)")
    return {
        "answer": _get_fallback(question),
        "source": "fallback",
        "model": None,
        "context_aware": False,
    }


@router.get(
    "/prompts",
    summary="Get suggested career questions",
    description="Returns personalized prompts if resume_id is available, otherwise generic prompts.",
)
async def get_suggested_prompts(resume_id: Optional[str] = None):
    """Return suggested career questions — personalized if resume context exists."""
    if resume_id:
        resumes = get_resumes_collection()
        resume_doc = await resumes.find_one({"_id": resume_id})
        if resume_doc:
            recs = get_recommendations_collection()
            rec_doc = await recs.find_one({"resume_id": resume_id})
            personalized = _build_personalized_prompts(resume_doc, rec_doc)
            if personalized:
                return {"prompts": personalized, "personalized": True}

    return {"prompts": DEFAULT_PROMPTS, "personalized": False}

