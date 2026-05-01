"""
career_advisor.py — POST /career-advisor
------------------------------------------
AI-powered career advisor using Google Gemini API (free tier).
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


SUGGESTED_PROMPTS = [
    "How do I transition from manual testing to DevOps?",
    "What certifications should I get for Data Science?",
    "How to switch from backend development to ML engineering?",
    "What skills do I need for a cloud engineer role?",
    "How can I move from non-tech to data analytics?",
    "What is the career scope in GenAI and LLMs?",
    "How to build a strong portfolio for frontend development?",
    "What are the highest-paying tech roles in 2025?",
]

FALLBACK_RESPONSES = {
    "data": "Data Science and Analytics are among the most in-demand fields today. Start with Python, SQL, and statistics fundamentals. Platforms like Kaggle offer great hands-on practice. Focus on building projects that demonstrate your analytical thinking.",
    "devops": "DevOps engineers bridge development and operations. Key skills include Docker, Kubernetes, CI/CD pipelines, and cloud platforms (AWS/GCP/Azure). Start with Linux fundamentals and version control, then progress to containerization.",
    "frontend": "Modern frontend development revolves around React, TypeScript, and responsive design. Build a portfolio with 3-5 projects showcasing different skills. Learn about web performance, accessibility, and testing.",
    "backend": "Backend development requires strong fundamentals in a language (Python/Java/Node.js), databases (SQL + NoSQL), REST APIs, and system design. Focus on building scalable, well-tested applications.",
    "ml": "Machine Learning engineering combines ML theory with production engineering. Master Python, scikit-learn, TensorFlow/PyTorch, and MLOps tools. Deploy models using Docker and cloud services.",
    "career": "To advance your tech career: 1) Build a strong GitHub portfolio, 2) Contribute to open source, 3) Network on LinkedIn, 4) Get relevant certifications, 5) Practice system design interviews.",
    "default": "Focus on building practical skills through projects. The tech industry values demonstrated ability over credentials. Start with fundamentals, build projects, and continuously learn. Consider contributing to open-source projects to gain visibility.",
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


@router.post(
    "",
    summary="Ask TheCorrelation AI Career Advisor a question",
    description=(
        "Uses Google Gemini API (free tier) to provide personalized career advice. "
        "Falls back to rule-based responses if API is unavailable. "
        "Optionally provide a resume_id for context-aware responses."
    ),
)
async def ask_career_advisor(payload: CareerQuestion):
    """Generate AI-powered career advice."""
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    # Load user context if resume_id provided
    user_context = ""
    if payload.resume_id:
        resumes = get_resumes_collection()
        resume_doc = await resumes.find_one({"_id": payload.resume_id})
        if resume_doc:
            skills = resume_doc.get("normalized_skills", [])
            if skills:
                user_context = f"The user has the following skills: {', '.join(skills)}. "

            recs = get_recommendations_collection()
            rec_doc = await recs.find_one({"resume_id": payload.resume_id})
            if rec_doc:
                role = rec_doc.get("predicted_role", "")
                if role:
                    user_context += f"Their predicted best-fit role is: {role}. "
                gaps = rec_doc.get("skill_gap", [])
                if isinstance(gaps, list):
                    gap_names = [g.get("skill", "") for g in gaps[:5] if isinstance(g, dict) and g.get("is_core")]
                    if gap_names:
                        user_context += f"They are missing these core skills: {', '.join(gap_names)}. "

    # ── Try Gemini API first ──────────────────────────────────────────────
    gemini_key = settings.GEMINI_API_KEY.strip().strip('"').strip("'")
    if gemini_key:
        try:
            import httpx

            system_instruction = (
                "You are an elite AI Career Advisor for tech professionals. "
                "You provide specific, actionable career guidance. "
                "Be encouraging but realistic. Keep responses to 3-4 paragraphs max. "
                "Use bullet points where helpful. Do not use markdown headers. "
                "Focus on practical next steps the user can take immediately."
            )

            user_prompt = f"{user_context}User question: {question}"

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

                # Extract text from Gemini response
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    content = parts[0].get("text", "").strip() if parts else ""
                    if content:
                        logger.info("Gemini career advice generated successfully")
                        return {
                            "answer": content,
                            "source": "ai",
                            "model": "gemini-2.0-flash",
                        }

        except Exception as e:
            logger.error("Gemini API call failed: %s", e)

    # ── Try OpenRouter as second option ───────────────────────────────────
    if settings.OPENROUTER_API_KEY:
        try:
            import httpx
            system_prompt = (
                "You are an elite AI Career Advisor for tech professionals. "
                "You provide specific, actionable career guidance. "
                "Be encouraging but realistic. Keep responses to 3-4 paragraphs max. "
                "Use bullet points where helpful. Do not use markdown headers. "
                "Focus on practical next steps the user can take immediately."
            )

            user_prompt = f"{user_context}User question: {question}"

            payload_llm = {
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
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
                    }
        except Exception as e:
            logger.error("OpenRouter LLM call failed: %s", e)

    # ── Fallback to rule-based ────────────────────────────────────────────
    logger.info("Using fallback career advice (no API key configured or API failed)")
    return {
        "answer": _get_fallback(question),
        "source": "fallback",
        "model": None,
    }


@router.get(
    "/prompts",
    summary="Get suggested career questions",
)
async def get_suggested_prompts():
    """Return a list of suggested career questions."""
    return {"prompts": SUGGESTED_PROMPTS}
