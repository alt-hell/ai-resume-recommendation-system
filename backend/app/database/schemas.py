"""
schemas.py
----------
Pydantic models for all API request/response contracts.

Organized into:
  - Resume intake models (upload + extraction results)
  - Recommendation models (role prediction, skill gap)
  - Career path models
  - Trend analysis models
  - Shared / base models
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Shared
# ─────────────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str


# ─────────────────────────────────────────────────────────────────────────────
# Resume Parsing / Skill Extraction
# ─────────────────────────────────────────────────────────────────────────────

class SkillExtractionResponse(BaseModel):
    """Result of the skill extraction + normalization pipeline."""
    resume_id: str = Field(..., description="MongoDB document ID for this analysis")
    filename: str
    file_type: str
    extraction_source: str = Field(
        ..., description="'section', 'ner', or 'combined'"
    )
    extraction_confidence: float
    raw_skills: list[str] = Field(..., description="Skills before normalization")
    normalized_skills: list[str] = Field(..., description="Canonical skill names")
    unknown_skills: list[str] = Field(
        default_factory=list,
        description="Skills not found in registry",
    )
    skill_categories: dict[str, str] = Field(
        default_factory=dict,
        description="canonical_skill → category",
    )
    match_rate: float = Field(..., description="Fraction of skills matched to registry")
    total_skills: int
    projects_text: Optional[str] = Field(default=None, description="Extracted text from the projects section")
    predicted_role: Optional[str] = Field(default=None, description="Fast lightweight prediction for immediate UI use")
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class UploadResponse(BaseModel):
    """Immediate response to a resume upload."""
    resume_id: str
    filename: str
    file_type: str
    size_bytes: int
    message: str = "Resume uploaded and queued for analysis."


# ─────────────────────────────────────────────────────────────────────────────
# Recommendation Engine
# ─────────────────────────────────────────────────────────────────────────────

class SkillGap(BaseModel):
    """A single missing skill with priority metadata."""
    skill: str
    category: str
    is_core: bool = Field(..., description="True = must-have, False = nice-to-have")
    learning_resource: Optional[str] = None
    youtube_url: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Full career recommendation for a resume."""
    resume_id: str
    predicted_role: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    role_description: str
    salary_range_inr: dict[str, int]

    candidate_skills: list[str]
    skill_gap: list[SkillGap]
    matched_skills: list[str]

    top_3_roles: list[dict] = Field(
        default_factory=list,
        description="[{role, confidence}] for top 3 predictions",
    )

    learning_path: list[str] = Field(
        ..., description="Ordered list of skills to learn next"
    )
    estimated_gap_weeks: int = Field(
        ..., description="Rough estimate to close core skill gap"
    )

    domain_fit_percentage: float = Field(default=0.0, description="Calculated domain fit percentage")
    advanced_insights: str = Field(default="", description="Detailed textual feedback on focusing skills and domain fit")
    project_skills: list[str] = Field(default_factory=list, description="Skills mentioned in the projects section")
    course_recommendation: Optional[dict] = Field(default=None, description="The Correlation course redirect info")
    interview_prep: list[str] = Field(default_factory=list, description="Interview questions based on missing skills")
    action_verb_feedback: Optional[str] = Field(default=None, description="Feedback on resume action verbs")

    is_general_skills_user: bool = Field(default=False, description="True if user has mostly basic/non-IT skills")
    career_exploration_suggestions: list[dict] = Field(default_factory=list, description="Career path suggestions for general skills users")

    is_no_skills_user: bool = Field(default=False, description="True if no technical skills were found")
    correlation_courses: list[dict] = Field(default_factory=list, description="TheCorrelation course suggestions for no-skill users")

    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
# Job Links
# ─────────────────────────────────────────────────────────────────────────────

class JobLinkItem(BaseModel):
    """A single job listing with apply link."""
    job_title: str
    company: str
    location: str
    apply_url: str
    platform: str
    posted_date: str = ""
    job_type: str = ""
    description_snippet: str = ""


class JobLinksResponse(BaseModel):
    """Top job application links for a resume."""
    resume_id: str
    predicted_role: str
    source: str = Field(..., description="'jsearch' or 'fallback'")
    total_found: int
    jobs: list[JobLinkItem]


# ─────────────────────────────────────────────────────────────────────────────
# Career Path (kept for backward compat)
# ─────────────────────────────────────────────────────────────────────────────

class CareerStep(BaseModel):
    """One step in a career progression."""
    role: str
    description: str
    skills_to_add: list[str]
    estimated_months: int


class CareerPathResponse(BaseModel):
    """Career roadmap from current role to future roles."""
    resume_id: str
    current_role: str
    progression: list[CareerStep]
    summary: str


# ─────────────────────────────────────────────────────────────────────────────
# Trend Analysis
# ─────────────────────────────────────────────────────────────────────────────

class SkillTrend(BaseModel):
    """Demand data for a single skill."""
    skill: str
    category: str
    frequency: int = Field(..., description="Count across job dataset")
    demand_score: float = Field(..., ge=0.0, le=1.0)
    trend: str = Field(..., description="'rising', 'stable', or 'declining'")


class TrendResponse(BaseModel):
    """Skill trend analysis result."""
    total_jobs_analyzed: int
    top_skills: list[SkillTrend]
    by_category: dict[str, list[SkillTrend]]
    generated_at: datetime = Field(default_factory=datetime.utcnow)




class ResumeDocument(BaseModel):
    """Full document stored in MongoDB 'resumes' collection."""
    filename: str
    file_type: str
    size_bytes: int
    raw_text: str
    cleaned_text: str
    raw_skills: list[str]
    normalized_skills: list[str]
    unknown_skills: list[str]
    skill_categories: dict[str, str]
    extraction_source: str
    extraction_confidence: float
    match_rate: float
    projects_text: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)


class RecommendationDocument(BaseModel):
    """Full recommendation stored in MongoDB 'recommendations' collection."""
    resume_id: str
    predicted_role: str
    confidence: float
    top_3_roles: list[dict]
    candidate_skills: list[str]
    skill_gap: list[dict]
    matched_skills: list[str]
    learning_path: list[str]
    estimated_gap_weeks: int

    domain_fit_percentage: float = 0.0
    advanced_insights: str = ""
    project_skills: list[str] = Field(default_factory=list)
    course_recommendation: Optional[dict] = None
    interview_prep: list[str] = Field(default_factory=list)
    action_verb_feedback: Optional[str] = None

    is_no_skills_user: bool = False
    correlation_courses: list[dict] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.utcnow)
