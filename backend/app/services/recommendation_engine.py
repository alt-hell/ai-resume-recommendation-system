"""
recommendation_engine.py
------------------------
Core inference engine for the resume analyzer.

Responsibilities:
  1. Load trained ML artifacts (model, vectorizer, label encoder)
  2. Predict best-fit job role with confidence scores for all roles
  3. Calculate skill gap — what canonical skills the user is missing
     for their predicted (or requested) target role
  4. Rank user skills by importance to the predicted role
     using XGBoost feature importances
  5. Return a structured RecommendationResult ready for the API layer

No LLM is used here. All inference is pure ML (XGBoost + sklearn).

Pipeline position:
  normalization → [THIS FILE] → API (recommend.py)
"""

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import os
import asyncio
import json
import httpx
from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer
from xgboost import XGBClassifier

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths — mirrors what train_model.py writes
# ---------------------------------------------------------------------------

_MODELS_DIR    = Path(__file__).parent.parent / "models"
_MODEL_PATH    = _MODELS_DIR / "model.pkl"
_VEC_PATH      = _MODELS_DIR / "vectorizer.pkl"
_LABEL_PATH    = _MODELS_DIR / "label_encoder.pkl"


# ---------------------------------------------------------------------------
# Role skill definitions — must stay in sync with train_model.py
# Used for skill gap calculation (what skills define each role)
# ---------------------------------------------------------------------------

ROLE_SKILL_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "Backend Developer": {
        "essential": ["Python", "REST APIs", "SQL", "Git", "PostgreSQL"],
        "recommended": ["Django", "FastAPI", "Flask", "Docker", "Redis",
                        "MongoDB", "Linux", "CI/CD", "Microservices"],
    },
    "Frontend Developer": {
        "essential": ["JavaScript", "React", "Git"],
        "recommended": ["TypeScript", "Node.js", "REST APIs", "Vue.js",
                        "Next.js", "Jest", "GraphQL"],
    },
    "Full Stack Developer": {
        "essential": ["JavaScript", "React", "Node.js", "SQL", "Git"],
        "recommended": ["TypeScript", "Python", "PostgreSQL", "MongoDB",
                        "REST APIs", "Docker", "Next.js"],
    },
    "Data Scientist": {
        "essential": ["Python", "Machine Learning", "Pandas", "NumPy",
                      "Scikit-learn", "SQL"],
        "recommended": ["Deep Learning", "TensorFlow", "PyTorch", "Tableau",
                        "NLP", "XGBoost", "R"],
    },
    "Machine Learning Engineer": {
        "essential": ["Python", "Machine Learning", "TensorFlow", "PyTorch",
                      "Scikit-learn", "Docker"],
        "recommended": ["Deep Learning", "Kubernetes", "REST APIs", "NumPy",
                        "Pandas", "AWS", "XGBoost", "Hugging Face"],
    },
    "Data Engineer": {
        "essential": ["Python", "SQL", "Apache Spark", "Apache Kafka", "Airflow"],
        "recommended": ["Hadoop", "AWS", "Google Cloud", "dbt",
                        "PostgreSQL", "Docker", "Linux"],
    },
    "DevOps Engineer": {
        "essential": ["Docker", "Kubernetes", "Linux", "CI/CD", "Git", "Terraform"],
        "recommended": ["AWS", "Ansible", "Jenkins", "GitHub Actions",
                        "Nginx", "Python"]
    },
    "Cloud Engineer": {
        "essential": ["AWS", "Terraform", "Docker", "Linux", "CI/CD"],
        "recommended": ["Kubernetes", "Google Cloud", "Microsoft Azure",
                        "Python", "Ansible", "Nginx"]
    },
    "Mobile Developer": {
        "essential": ["Flutter", "Dart", "Git", "REST APIs"],
        "recommended": ["React Native", "JavaScript", "Android Development",
                        "iOS Development", "Firebase"],
    },
    "Android Developer": {
        "essential": ["Android Development", "Java", "Kotlin", "Git"],
        "recommended": ["REST APIs", "Firebase", "SQLite", "CI/CD"],
    },
    "iOS Developer": {
        "essential": ["iOS Development", "Swift", "Git"],
        "recommended": ["REST APIs", "Firebase", "SQLite", "CI/CD"],
    },
    "Database Administrator": {
        "essential": ["SQL", "PostgreSQL", "MySQL", "Linux", "Git"],
        "recommended": ["Oracle Database", "Microsoft SQL Server", "MongoDB",
                        "Redis", "Elasticsearch", "Bash"],
    },
    "Security Engineer": {
        "essential": ["Linux", "Python", "Bash", "Git", "CI/CD"],
        "recommended": ["AWS", "Docker", "Kubernetes", "Terraform", "Nginx"],
    },
    "QA Engineer": {
        "essential": ["Selenium", "Unit Testing", "Git", "Pytest", "Jest"],
        "recommended": ["Python", "JavaScript", "REST APIs", "CI/CD", "Agile"],
    },
    "Tech Lead": {
        "essential": ["Leadership", "Agile", "Git", "Problem Solving", "Communication"],
        "recommended": ["Python", "Java", "REST APIs", "Docker",
                        "Microservices", "CI/CD", "SQL"],
    },
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RoleScore:
    """Confidence score for a single role prediction."""
    role: str
    confidence: float          # 0.0 – 1.0
    rank: int                  # 1 = top prediction

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "confidence": round(self.confidence, 4),
            "rank": self.rank,
        }


@dataclass
class SkillGap:
    """Missing skills for a target role, split by priority."""
    target_role: str
    essential_missing: list[str]    # Must-have skills user lacks
    recommended_missing: list[str]  # Good-to-have skills user lacks
    match_score: float              # % of required skills already present

    def to_dict(self) -> dict:
        return {
            "target_role": self.target_role,
            "essential_missing": self.essential_missing,
            "recommended_missing": self.recommended_missing,
            "match_score": round(self.match_score, 4),
            "total_missing": len(self.essential_missing) + len(self.recommended_missing),
        }


@dataclass
class RecommendationResult:
    """
    Full recommendation output returned by the engine.

    Attributes:
        predicted_role:   Top predicted job role.
        confidence:       Confidence score for predicted_role (0–1).
        all_role_scores:  Ranked list of scores for all 15 roles.
        skill_gap:        Gap analysis for the predicted role.
        top_skills:       User's skills ranked by importance to predicted role.
        user_skills:      The normalized skills that were provided as input.
    """
    predicted_role: str
    confidence: float
    all_role_scores: list[RoleScore] = field(default_factory=list)
    skill_gap: Optional[SkillGap] = None
    top_skills: list[str] = field(default_factory=list)
    user_skills: list[str] = field(default_factory=list)
    
    domain_fit_percentage: float = 0.0
    advanced_insights: str = ""
    project_skills: list[str] = field(default_factory=list)
    course_recommendation: Optional[dict] = None
    interview_prep: list[str] = field(default_factory=list)
    action_verb_feedback: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "predicted_role": self.predicted_role,
            "confidence": round(self.confidence, 4),
            "all_role_scores": [s.to_dict() for s in self.all_role_scores],
            "skill_gap": self.skill_gap.to_dict() if self.skill_gap else None,
            "top_skills": self.top_skills,
            "user_skills": self.user_skills,
            "domain_fit_percentage": round(self.domain_fit_percentage, 2),
            "advanced_insights": self.advanced_insights,
            "project_skills": self.project_skills,
            "course_recommendation": self.course_recommendation,
            "interview_prep": self.interview_prep,
            "action_verb_feedback": self.action_verb_feedback,
        }


# ---------------------------------------------------------------------------
# Artifact loader — lazy, cached, thread-safe via lru_cache
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_artifacts() -> tuple[XGBClassifier, MultiLabelBinarizer, LabelEncoder]:
    """
    Load model artifacts from disk exactly once per process lifetime.

    lru_cache ensures:
      - First call: loads from disk (~50–100ms)
      - Subsequent calls: returns cached tuple instantly

    Raises:
        FileNotFoundError if artifacts not found (run train_model.py first).
    """
    for path in [_MODEL_PATH, _VEC_PATH, _LABEL_PATH]:
        if not path.exists():
            raise FileNotFoundError(
                f"Model artifact missing: {path}\n"
                "Run: python scripts/train_model.py"
            )

    model         = joblib.load(_MODEL_PATH)
    vectorizer    = joblib.load(_VEC_PATH)
    label_encoder = joblib.load(_LABEL_PATH)

    logger.info(
        "Model artifacts loaded — %d roles, %d features",
        len(label_encoder.classes_),
        len(vectorizer.classes_),
    )
    return model, vectorizer, label_encoder


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def recommend(
    normalized_skills: list[str],
    target_role: Optional[str] = None,
    projects_text: Optional[str] = None
) -> RecommendationResult:
    """
    Generate a full recommendation from a list of canonical skill names.

    Args:
        normalized_skills: Output of normalization.normalize_skills().normalized
        target_role:       Optional override for skill gap analysis.
                           If None, the predicted role is used.
        projects_text:     Optional raw text from the projects section to boost fit.

    Returns:
        RecommendationResult with role prediction, confidence, skill gap,
        and ranked skills.

    Raises:
        ValueError: If normalized_skills is empty.
        FileNotFoundError: If model artifacts have not been trained yet.
    """
    if not normalized_skills:
        raise ValueError(
            "Cannot generate recommendation: no skills provided. "
            "Ensure the resume contains a recognizable skills section."
        )

    model, vectorizer, label_encoder = _load_artifacts()

    # Step 1: Vectorize input skills
    X = _vectorize(normalized_skills, vectorizer)

    # Step 2: Predict role probabilities
    role_scores = _predict_roles(X, model, label_encoder)

    # Step 3: Determine target role for gap analysis
    predicted_role = role_scores[0].role
    gap_role = target_role if (target_role and target_role in ROLE_SKILL_REQUIREMENTS) \
               else predicted_role

    # Step 4: Skill gap analysis
    skill_gap = _calculate_skill_gap(normalized_skills, gap_role)

    # Step 5: Rank user skills by feature importance
    top_skills = _rank_user_skills(normalized_skills, predicted_role, model, vectorizer)

    # Step 6: Advanced Domain Fit & Project Evaluation
    project_skills = _extract_project_skills(normalized_skills, projects_text)
    domain_fit = _calculate_domain_fit(role_scores[0].confidence, skill_gap, project_skills)
    advanced_insights = await _generate_advanced_insights(domain_fit, predicted_role, project_skills, skill_gap.essential_missing, normalized_skills)
    course_rec = _get_course_recommendation(predicted_role)
    interview_prep = _generate_interview_prep(skill_gap.essential_missing)
    action_req = _check_action_verbs(projects_text)

    return RecommendationResult(
        predicted_role=predicted_role,
        confidence=role_scores[0].confidence,
        all_role_scores=role_scores,
        skill_gap=skill_gap,
        top_skills=top_skills,
        user_skills=normalized_skills,
        domain_fit_percentage=domain_fit,
        advanced_insights=advanced_insights,
        project_skills=project_skills,
        course_recommendation=course_rec,
        interview_prep=interview_prep,
        action_verb_feedback=action_req,
    )


def predict_role(normalized_skills: list[str]) -> tuple[str, float]:
    """
    Lightweight prediction — returns only (role, confidence).
    Useful for batch processing or quick checks.

    Args:
        normalized_skills: List of canonical skill names.

    Returns:
        (predicted_role, confidence) tuple.
    """
    model, vectorizer, label_encoder = _load_artifacts()
    X = _vectorize(normalized_skills, vectorizer)
    scores = _predict_roles(X, model, label_encoder)
    return scores[0].role, scores[0].confidence


def get_skill_gap(
    normalized_skills: list[str],
    target_role: str,
) -> SkillGap:
    """
    Calculate skill gap for a specific target role.

    Args:
        normalized_skills: User's canonical skills.
        target_role:       Role to compare against.

    Returns:
        SkillGap with essential_missing and recommended_missing.

    Raises:
        ValueError: If target_role is not a known role.
    """
    if target_role not in ROLE_SKILL_REQUIREMENTS:
        raise ValueError(
            f"Unknown role: '{target_role}'. "
            f"Valid roles: {sorted(ROLE_SKILL_REQUIREMENTS.keys())}"
        )
    return _calculate_skill_gap(normalized_skills, target_role)


def get_all_roles() -> list[str]:
    """Return all supported job roles sorted alphabetically."""
    return sorted(ROLE_SKILL_REQUIREMENTS.keys())


def get_role_requirements(role: str) -> dict[str, list[str]]:
    """
    Return the essential and recommended skill requirements for a role.

    Args:
        role: A valid job role name.

    Returns:
        Dict with 'essential' and 'recommended' skill lists.

    Raises:
        ValueError: If role is not known.
    """
    if role not in ROLE_SKILL_REQUIREMENTS:
        raise ValueError(f"Unknown role: '{role}'")
    return ROLE_SKILL_REQUIREMENTS[role]


# ---------------------------------------------------------------------------
# Internal — vectorization
# ---------------------------------------------------------------------------

def _vectorize(skills: list[str], vectorizer: MultiLabelBinarizer) -> np.ndarray:
    """
    Convert a list of canonical skills to a feature vector.

    Skills not in the vectorizer vocabulary are silently ignored
    (they were not seen during training — this is expected for
    unknown skills that slipped through normalization).
    """
    # MultiLabelBinarizer expects an iterable of iterables
    known_skills = [s for s in skills if s in vectorizer.classes_]
    if len(known_skills) < len(skills):
        unknown = set(skills) - set(known_skills)
        logger.debug("Skills not in vectorizer vocabulary: %s", unknown)

    X = vectorizer.transform([known_skills])
    return X.astype(np.float32)


# ---------------------------------------------------------------------------
# Internal — role prediction
# ---------------------------------------------------------------------------

def _predict_roles(
    X: np.ndarray,
    model: XGBClassifier,
    label_encoder: LabelEncoder,
) -> list[RoleScore]:
    """
    Run inference and return all roles ranked by confidence.

    Uses predict_proba (softprob objective) so we get a probability
    distribution across all 15 roles, not just a hard prediction.

    Returns:
        List of RoleScore sorted by confidence descending (rank 1 = best).
    """
    proba = model.predict_proba(X)[0]  # shape: (n_classes,)

    scores: list[RoleScore] = []
    for idx, prob in enumerate(proba):
        role = label_encoder.inverse_transform([idx])[0]
        scores.append(RoleScore(role=role, confidence=float(prob), rank=0))

    # Sort by confidence descending and assign ranks
    scores.sort(key=lambda s: s.confidence, reverse=True)
    for rank, score in enumerate(scores, start=1):
        score.rank = rank

    logger.debug(
        "Top 3 predictions: %s",
        [(s.role, f"{s.confidence:.2%}") for s in scores[:3]]
    )
    return scores


# ---------------------------------------------------------------------------
# Internal — skill gap analysis
# ---------------------------------------------------------------------------

def _calculate_skill_gap(
    user_skills: list[str],
    target_role: str,
) -> SkillGap:
    """
    Compare user skills against role requirements to find gaps.

    Calculates:
      - essential_missing: required skills the user doesn't have
      - recommended_missing: good-to-have skills the user doesn't have
      - match_score: fraction of all required skills already present

    Match score formula:
      essential skills count double (they carry more weight).
      match_score = (present_essential×2 + present_recommended) /
                    (total_essential×2 + total_recommended)
    """
    requirements = ROLE_SKILL_REQUIREMENTS.get(target_role, {})
    essential    = requirements.get("essential", [])
    recommended  = requirements.get("recommended", [])

    user_set = {s.lower() for s in user_skills}

    essential_missing    = [s for s in essential    if s.lower() not in user_set]
    recommended_missing  = [s for s in recommended  if s.lower() not in user_set]

    # Weighted match score
    present_essential   = len(essential)    - len(essential_missing)
    present_recommended = len(recommended)  - len(recommended_missing)

    denominator = (len(essential) * 2) + len(recommended)
    if denominator == 0:
        match_score = 1.0
    else:
        numerator   = (present_essential * 2) + present_recommended
        match_score = numerator / denominator

    logger.debug(
        "Skill gap for '%s': %d essential missing, %d recommended missing, "
        "match=%.2f",
        target_role,
        len(essential_missing),
        len(recommended_missing),
        match_score,
    )

    return SkillGap(
        target_role=target_role,
        essential_missing=essential_missing,
        recommended_missing=recommended_missing,
        match_score=match_score,
    )


# ---------------------------------------------------------------------------
# Internal — skill ranking by feature importance
# ---------------------------------------------------------------------------

def _rank_user_skills(
    user_skills: list[str],
    predicted_role: str,
    model: XGBClassifier,
    vectorizer: MultiLabelBinarizer,
) -> list[str]:
    """
    Rank user's skills by their XGBoost feature importance for the
    predicted role.

    XGBoost exposes per-feature importance scores learned during training.
    We filter to only the skills the user has and sort by importance,
    giving the user insight into which of their skills matter most.

    Returns:
        User's skills sorted from most → least important to the predicted role.
        Skills not found in the model's vocabulary appear at the end.
    """
    importance_map: dict[str, float] = {}

    try:
        # feature_importances_ is a flat array aligned with vectorizer.classes_
        importances = model.feature_importances_
        for skill, importance in zip(vectorizer.classes_, importances):
            importance_map[skill] = float(importance)
    except AttributeError:
        logger.warning("Model has no feature_importances_ — returning skills as-is")
        return user_skills

    # Sort user's skills by importance (descending)
    def _importance(skill: str) -> float:
        return importance_map.get(skill, 0.0)

    ranked = sorted(user_skills, key=_importance, reverse=True)

    logger.debug(
        "Top 5 user skills by importance for '%s': %s",
        predicted_role,
        ranked[:5],
    )
    return ranked


# ---------------------------------------------------------------------------
# Internal — Advanced Feature Generation
# ---------------------------------------------------------------------------

ACTION_VERBS = {"developed", "architected", "built", "created", "designed", "implemented", "managed", "led", "optimized", "spearheaded", "engineered", "integrated", "deployed"}

def _extract_project_skills(normalized_skills: list[str], projects_text: Optional[str]) -> list[str]:
    if not projects_text:
        return []
    pt = projects_text.lower()
    found = []
    for skill in normalized_skills:
        if skill.lower() in pt:
            found.append(skill)
    return found

def _calculate_domain_fit(confidence: float, skill_gap: SkillGap, project_skills: list[str]) -> float:
    # 40% ML Confidence, 50% Skill Match, 10% Project Backing
    project_score = 0.0
    requirements = ROLE_SKILL_REQUIREMENTS.get(skill_gap.target_role, {})
    essential = requirements.get("essential", [])
    if essential:
        backed = len([s for s in project_skills if s in essential])
        project_score = min(1.0, backed / len(essential))
    else:
        project_score = 0.5
        
    fit = (confidence * 0.4) + (skill_gap.match_score * 0.5) + (project_score * 0.1)
    return min(100.0, fit * 100)

async def _generate_advanced_insights(fit: float, role: str, project_skills: list[str], missing: list[str], user_skills: list[str]) -> str:
    parts = []
    parts.append(f"You have an estimated {fit:.0f}% domain fit for the {role} role based on your skills and projects.")
    if project_skills:
        parts.append(f"We noticed you used {', '.join(project_skills[:3])} in your covered projects, which strengthens your profile!")
    else:
        parts.append("Adding dedicated projects highlighting your technical skills can significantly boost your credibility.")
        
    fallback_middle = " ".join(parts)
    fallback_end = ""
    
    if missing:
        fallback_end = f"However, you have to focus on mastering these core skills to increase your chances of getting a job in this domain: {', '.join(missing[:4])}."
    else:
        fallback_end = "Your skill profile perfectly matches the core requirements for this role. Great job!"

    # OpenRouter free LLM for advanced career advice
    if settings.OPENROUTER_API_KEY and missing:
        prompt = (
            f"You are an elite Career Advisor. "
            f"The user has an estimated {fit:.0f}% domain fit for '{role}'. "
            f"They possess the following skills: {', '.join(user_skills)}. "
            f"However, they are missing these core skills: {', '.join(missing)}. "
            "Write exactly ONE concise, encouraging 2-sentence paragraph. Explain strictly conceptually which missing skills they should ACTUALLY prioritize. "
            "If they possess a parallel/alternative skill (e.g. they know TensorFlow but lack PyTorch, or React but lack Vue), point out that their existing skill highly overlaps and they don't necessarily need to panic about the missing one. "
            "Be exceedingly professional, short, and punchy. No Markdown."
        )
        try:
            payload = {
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": "You are an elite career advisor. Be concise and professional."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
            }
            headers = {
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "HTTP-Referer": "http://localhost:8000",
                "X-Title": "AI Resume Recommendation System",
            }
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if content:
                    return f"{fallback_middle} {content}"
        except Exception as e:
            logger.error(f"OpenRouter LLM call failed: {str(e)}")

    return f"{fallback_middle} {fallback_end}"

def _check_action_verbs(projects_text: Optional[str]) -> Optional[str]:
    if not projects_text:
        return None
    pt = projects_text.lower()
    found_verbs = [v for v in ACTION_VERBS if v in pt]
    if len(found_verbs) < 2:
        return "Your projects section lacks strong action verbs. Consider starting bullet points with words like 'Developed', 'Architected', or 'Optimized' to make a stronger impact."
    return None

def _get_course_recommendation(role: str) -> Optional[dict]:
    data_roles = {"Data Scientist", "Machine Learning Engineer", "Data Engineer", "Business Analyst"}
    if role in data_roles or "AI" in role or "ML" in role or "Data" in role:
        return {
            "title": "Mastering Data Science & AI",
            "provider": "TheCorrelation",
            "description": "Accelerate your career in Data and AI with comprehensive programs designed by industry experts. Click to learn more.",
            "url": "https://thecorrelation.in/courses/chartered-data-science"
        }
    return None

def _generate_interview_prep(essential_missing: list[str]) -> list[str]:
    prep = []
    for skill in essential_missing[:3]:
        prep.append(f"How would you explain the core concepts of {skill} to a non-technical stakeholder?")
        prep.append(f"Describe a scenario where you would choose to use {skill} over its alternatives.")
    return prep[:3]