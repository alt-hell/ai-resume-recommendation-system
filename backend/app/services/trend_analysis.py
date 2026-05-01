"""
trend_analysis.py
-----------------
Analyzes skill demand trends from the job dataset.

Data sources (checked in order):
  1. data/processed/job_skills.json  — pre-processed job→skills mapping
  2. data/raw/*.csv                  — raw CSV files with a 'skills' column
  3. Synthetic baseline              — hardcoded demand scores (always works)

Output: ranked list of skills with demand scores and trend labels.
"""

import json
import logging
from collections import Counter
from pathlib import Path

from app.core.constants import JOB_ROLES, ROLE_REQUIRED_SKILLS
from app.services.normalization import SKILL_CATEGORIES

logger = logging.getLogger(__name__)

# Paths relative to the project root
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # 4 levels up from services/
_PROCESSED_FILE = _PROJECT_ROOT / "data" / "processed" / "job_skills.json"
_RAW_DIR = _PROJECT_ROOT / "data" / "raw"


# ─────────────────────────────────────────────────────────────────────────────
# Data classes
# ─────────────────────────────────────────────────────────────────────────────

class SkillTrendData:
    """Demand metrics for a single skill."""

    def __init__(self, skill: str, frequency: int, total: int):
        self.skill = skill
        self.category = SKILL_CATEGORIES.get(skill, "Other")
        self.frequency = frequency
        self.demand_score = round(frequency / total, 4) if total > 0 else 0.0
        self.trend = self._classify_trend()

    def _classify_trend(self) -> str:
        # Based on demand_score thresholds (calibrated against baseline)
        if self.demand_score >= 0.15:
            return "rising"
        elif self.demand_score >= 0.05:
            return "stable"
        else:
            return "declining"

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "category": self.category,
            "frequency": self.frequency,
            "demand_score": self.demand_score,
            "trend": self.trend,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_skill_trends(top_n: int = 30) -> dict:
    """
    Compute and return skill demand trends.

    Args:
        top_n: Number of top skills to include in the ranked list.

    Returns:
        {
          "total_jobs_analyzed": int,
          "top_skills": [SkillTrendData.to_dict(), ...],
          "by_category": {category: [SkillTrendData.to_dict(), ...]}
        }
    """
    skill_counts, total_jobs = _load_skill_counts()

    total = sum(skill_counts.values())
    if total == 0:
        logger.warning("No skill data loaded — returning empty trends.")
        return {"total_jobs_analyzed": 0, "top_skills": [], "by_category": {}}

    # Build SkillTrendData objects
    trends = [
        SkillTrendData(skill, count, total)
        for skill, count in skill_counts.most_common(top_n)
    ]

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for t in trends:
        by_category.setdefault(t.category, []).append(t.to_dict())

    return {
        "total_jobs_analyzed": total_jobs,
        "top_skills": [t.to_dict() for t in trends],
        "by_category": by_category,
    }


def get_trending_skills_for_role(role: str, top_n: int = 10) -> list[str]:
    """
    Return the most in-demand skills specifically for a given role.
    Used by the career path engine to suggest what to learn next.

    Args:
        role: A job role name (from constants.JOB_ROLES).
        top_n: Max skills to return.

    Returns:
        List of canonical skill names, ranked by demand.
    """
    reqs = ROLE_REQUIRED_SKILLS.get(role, {})
    all_skills = reqs.get("core", []) + reqs.get("bonus", [])

    skill_counts, _ = _load_skill_counts()

    # Rank by how frequently they appear in our job data
    ranked = sorted(
        all_skills,
        key=lambda s: skill_counts.get(s, 0),
        reverse=True,
    )
    return ranked[:top_n]


# ─────────────────────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_skill_counts() -> tuple[Counter, int]:
    """
    Load skill frequency data from disk or generate synthetic baseline.

    Returns:
        (Counter of {skill: count}, total_jobs_analyzed)
    """
    # 1. Try pre-processed JSON
    if _PROCESSED_FILE.exists():
        try:
            return _load_from_json(_PROCESSED_FILE)
        except Exception as exc:
            logger.warning("Failed to load processed file: %s", exc)

    # 2. Try raw CSVs
    csv_files = list(_RAW_DIR.glob("*.csv")) if _RAW_DIR.exists() else []
    if csv_files:
        try:
            return _load_from_csvs(csv_files)
        except Exception as exc:
            logger.warning("Failed to load raw CSVs: %s", exc)

    # 3. Synthetic baseline
    logger.info("No job data found — using synthetic skill demand baseline.")
    return _synthetic_baseline()


def _load_from_json(path: Path) -> tuple[Counter, int]:
    """Load pre-processed job_skills.json."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    counter: Counter = Counter()
    
    if isinstance(data, list):
        for item in data:
            skills = item.get("skills", [])
            if isinstance(skills, list):
                for s in skills:
                    counter[str(s)] += 1
    elif isinstance(data, dict):
        for skills in data.values():
            if isinstance(skills, list):
                for s in skills:
                    counter[str(s)] += 1

    logger.info("Loaded %d job entries from %s", len(data), path)
    return counter, len(data)


def _load_from_csvs(csv_files: list[Path]) -> tuple[Counter, int]:
    """Load raw CSV files. Expects a 'skills' column (comma-separated values)."""
    import pandas as pd  # imported lazily to avoid import cost

    counter: Counter = Counter()
    total_rows = 0

    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            if "skills" not in df.columns:
                logger.warning("CSV %s has no 'skills' column — skipping.", csv_file)
                continue

            for cell in df["skills"].dropna():
                skills = [s.strip() for s in str(cell).split(",") if s.strip()]
                for s in skills:
                    counter[s] += 1
            total_rows += len(df)
            logger.info("Loaded %d rows from %s", len(df), csv_file)
        except Exception as exc:
            logger.warning("Error reading %s: %s", csv_file, exc)

    return counter, total_rows


def _synthetic_baseline() -> tuple[Counter, int]:
    """
    Generate a realistic synthetic skill demand baseline.
    Built from the ROLE_REQUIRED_SKILLS registry, weighted by role popularity.

    Role weights approximate real-world job posting volumes.
    """
    role_weights = {
        "Data Scientist":            120,
        "Data Analyst":              200,
        "Machine Learning Engineer": 80,
        "Data Engineer":             90,
        "Backend Developer":         300,
        "Frontend Developer":        250,
        "Full Stack Developer":      280,
        "DevOps Engineer":           150,
        "Android Developer":         100,
        "iOS Developer":             70,
        "Cloud Engineer":            130,
        "Cybersecurity Analyst":     60,
        "Database Administrator":    50,
        "QA Engineer":               80,
    }

    counter: Counter = Counter()
    total = 0

    for role, weight in role_weights.items():
        reqs = ROLE_REQUIRED_SKILLS.get(role, {})
        for skill in reqs.get("core", []):
            counter[skill] += weight
        for skill in reqs.get("bonus", []):
            counter[skill] += weight // 2
        total += weight

    return counter, total
