"""
test_skill_extraction.py
------------------------
Unit tests for Phase 2:
  - skill_extractor.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.utils.text_cleaner import clean_raw_text
from app.services.skill_extractor import (
    SkillExtractionResult,
    detect_skills_section,
    extract_skills,
)


RESUME_COMMA = (
    "John Doe\njohn@email.com\n\n"
    "Technical Skills\nPython, FastAPI, MongoDB, Docker, Machine Learning\n\n"
    "Experience\nEngineer at Acme Corp"
)

def test_detects_technical_skills_header():
    result = extract_skills(clean_raw_text(RESUME_COMMA))
    assert result.source == "section"
    # Canonical header is "SKILLS"
    assert result.section_header.upper() in ["SKILLS", "TECHNICAL SKILLS"]

def test_extracts_comma_separated_skills():
    result = extract_skills(clean_raw_text(RESUME_COMMA))
    assert "Python" in result.skills
    assert "FastAPI" in result.skills
    assert "Machine Learning" in result.skills

def test_extract_invalid_text():
    result = extract_skills("")
    assert result.skill_count == 0
    assert result.skills == []
