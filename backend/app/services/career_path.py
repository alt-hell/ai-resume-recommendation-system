"""
career_path.py
--------------
Generates a personalized career progression roadmap.

Given a candidate's current predicted role and skill set, produces
an ordered sequence of next roles with the skills needed at each step
and a rough time estimate.

Logic:
  1. Look up the career progression chain for the predicted role.
  2. For each next role, compute the incremental skills to add.
  3. Estimate transition time based on skill delta size.
  4. Return a clean CareerPathResult object.
"""

import logging

from app.core.constants import (
    CAREER_PATHS,
    ROLE_DESCRIPTIONS,
    ROLE_SALARY_RANGES,
)
from app.services.recommendation_engine import ROLE_SKILL_REQUIREMENTS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

class CareerStep:
    """One step in the career progression roadmap."""

    def __init__(
        self,
        role: str,
        description: str,
        skills_to_add: list[str],
        estimated_months: int,
        salary_range: dict,
    ):
        self.role = role
        self.description = description
        self.skills_to_add = skills_to_add
        self.estimated_months = estimated_months
        self.salary_range = salary_range

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "description": self.description,
            "skills_to_add": self.skills_to_add,
            "estimated_months": self.estimated_months,
            "salary_range_inr": self.salary_range,
        }


class CareerPathResult:
    """Full career roadmap for a candidate."""

    def __init__(
        self,
        current_role: str,
        candidate_skills: list[str],
        progression: list[CareerStep],
        summary: str,
    ):
        self.current_role = current_role
        self.candidate_skills = candidate_skills
        self.progression = progression
        self.summary = summary

    def to_dict(self) -> dict:
        return {
            "current_role": self.current_role,
            "progression": [step.to_dict() for step in self.progression],
            "summary": self.summary,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_career_path(
    current_role: str,
    candidate_skills: list[str],
    max_steps: int = 3,
) -> CareerPathResult:
    """
    Build a career progression roadmap from the current role.

    Args:
        current_role:     Predicted role from the recommendation engine.
        candidate_skills: Normalized skills the candidate currently has.
        max_steps:        How many future roles to map (default 3).

    Returns:
        CareerPathResult with ordered CareerStep list.
    """
    next_roles = CAREER_PATHS.get(current_role, [])

    if not next_roles:
        logger.info(
            "No career path defined for '%s' — returning generic progression.",
            current_role,
        )
        return _generic_path(current_role, candidate_skills)

    skill_set = {s.lower() for s in candidate_skills}
    steps: list[CareerStep] = []

    # Accumulate skills as we progress through roles
    # (skills acquired in step N are available in step N+1)
    accumulated_skills = set(skill_set)

    for next_role in next_roles[:max_steps]:
        step = _build_step(next_role, accumulated_skills)
        steps.append(step)

        # Add the new role's core skills to accumulated set for the next step
        new_skills = ROLE_SKILL_REQUIREMENTS.get(next_role, {}).get("essential", [])
        accumulated_skills.update(s.lower() for s in new_skills)

    summary = _build_summary(current_role, steps)

    return CareerPathResult(
        current_role=current_role,
        candidate_skills=candidate_skills,
        progression=steps,
        summary=summary,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _build_step(role: str, candidate_skill_set: set[str]) -> CareerStep:
    """
    Compute the incremental skills needed to transition to `role`.

    Args:
        role:               Target role.
        candidate_skill_set: Lowercased skills the candidate currently has
                            (including those gained from previous steps).

    Returns:
        CareerStep with delta skills and time estimate.
    """
    reqs = ROLE_SKILL_REQUIREMENTS.get(role, {"essential": [], "recommended": []})
    core = reqs.get("essential", [])
    bonus = reqs.get("recommended", [])
    all_required = core + bonus

    # Skills to add = required skills NOT yet in candidate's set
    skills_to_add = [
        s for s in all_required
        if s.lower() not in candidate_skill_set
    ]

    # Time estimate: each missing core = 2 months, bonus = 1 month
    core_missing = sum(1 for s in core if s.lower() not in candidate_skill_set)
    bonus_missing = sum(1 for s in bonus if s.lower() not in candidate_skill_set)
    months = max(3, core_missing * 2 + bonus_missing * 1)
    months = min(months, 24)  # cap at 2 years

    return CareerStep(
        role=role,
        description=ROLE_DESCRIPTIONS.get(role, ""),
        skills_to_add=skills_to_add[:8],  # show top 8 most impactful
        estimated_months=months,
        salary_range=ROLE_SALARY_RANGES.get(role, {"min": 0, "max": 0}),
    )


def _generic_path(current_role: str, candidate_skills: list[str]) -> CareerPathResult:
    """
    Fallback for roles without a defined progression chain.
    Suggests becoming a senior version or specializing further.
    """
    steps = [
        CareerStep(
            role=f"Senior {current_role}",
            description=(
                f"Advance to a senior {current_role} position by deepening "
                "expertise, leading projects, and mentoring junior team members."
            ),
            skills_to_add=["System Design", "Mentoring", "Architecture", "Leadership"],
            estimated_months=12,
            salary_range={"min": 0, "max": 0},
        )
    ]
    return CareerPathResult(
        current_role=current_role,
        candidate_skills=candidate_skills,
        progression=steps,
        summary=(
            f"As a {current_role}, focus on deepening your expertise and "
            "taking on leadership responsibilities to advance your career."
        ),
    )


def _build_summary(current_role: str, steps: list[CareerStep]) -> str:
    """Generate a concise narrative summary of the progression."""
    if not steps:
        return f"Continue building expertise as a {current_role}."

    total_months = sum(s.estimated_months for s in steps)
    role_names = " → ".join(s.role for s in steps)

    return (
        f"Starting as a {current_role}, your ideal progression is: {role_names}. "
        f"This roadmap spans approximately {total_months} months of focused learning "
        f"and practical experience."
    )
