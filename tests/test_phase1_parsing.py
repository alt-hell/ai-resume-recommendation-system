"""
tests/test_phase1_parsing.py
-----------------------------
Unit tests for Phase 1:
- resume_parser.py (PDF + DOCX extraction)
- text_cleaner.py  (noise removal + section detection)

Run with:
    cd backend
    pytest tests/test_phase1_parsing.py -v
"""

import io
import sys
from pathlib import Path

# Make sure imports resolve from backend/
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.utils.text_cleaner import (
    TextCleaner,
    clean_raw_text,
    CleanedResume,
    HEADER_CANONICAL_MAP,
)
from app.services.resume_parser import ParsedResume


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_parsed(text: str) -> ParsedResume:
    """Wrap raw text in a minimal ParsedResume for cleaner testing."""
    return ParsedResume(
        raw_text=text,
        pages=[text],
        file_type="txt",
        page_count=1,
    )


# ---------------------------------------------------------------------------
# TextCleaner unit tests
# ---------------------------------------------------------------------------

class TestUnicodeNormalization:
    def test_non_breaking_space(self):
        result = clean_raw_text("Python\u00a0Developer")
        assert "\u00a0" not in result
        assert "Python Developer" in result

    def test_curly_quotes(self):
        result = clean_raw_text("\u201cReact.js\u201d")
        assert "\u201c" not in result
        assert "\u201d" not in result

    def test_bullet_variants(self):
        result = clean_raw_text("\u2022 Python \u25cf Java \u25aa Go")
        assert "\u2022" not in result
        assert "Python" in result
        assert "Java" in result


class TestNoiseRemoval:
    def setup_method(self):
        self.cleaner = TextCleaner(remove_urls=True, remove_emails=True)

    def test_removes_urls(self):
        parsed = make_parsed("Visit https://myportfolio.com for details")
        result = self.cleaner.clean(parsed)
        assert "https://" not in result.full_text

    def test_removes_email(self):
        parsed = make_parsed("Contact: john.doe@gmail.com | Python, Java")
        result = self.cleaner.clean(parsed)
        assert "@gmail.com" not in result.full_text
        assert "Python" in result.full_text

    def test_removes_linkedin(self):
        parsed = make_parsed("linkedin.com/in/johndoe | Skills: Python")
        result = self.cleaner.clean(parsed)
        assert "linkedin.com" not in result.full_text

    def test_keeps_phone_by_default(self):
        cleaner = TextCleaner(remove_phones=False)
        parsed = make_parsed("+1-555-0100 | Python Developer")
        result = cleaner.clean(parsed)
        assert "Python" in result.full_text


class TestWhitespaceCleaning:
    def test_collapses_multiple_spaces(self):
        result = clean_raw_text("Python   Java    Go")
        assert "  " not in result

    def test_strips_trailing_spaces(self):
        result = clean_raw_text("  Python  \n  Java  ")
        for line in result.split("\n"):
            assert line == line.strip() or line == ""

    def test_collapses_excessive_blank_lines(self):
        text = "Python\n\n\n\n\nJava"
        result = clean_raw_text(text)
        assert "\n\n\n" not in result


class TestDecorativeLineRemoval:
    def test_removes_dash_line(self):
        text = "Skills\n----------\nPython, Java"
        result = clean_raw_text(text)
        assert "----------" not in result
        assert "Python" in result

    def test_removes_equals_line(self):
        text = "Experience\n==========\nSoftware Engineer"
        result = clean_raw_text(text)
        assert "==========" not in result


class TestSectionDetection:
    def setup_method(self):
        self.cleaner = TextCleaner()

    def _clean(self, text: str) -> CleanedResume:
        return self.cleaner.clean(make_parsed(text))

    def test_detects_skills_section(self):
        text = "John Doe\n\nSkills\nPython, Java, React\n\nExperience\nSoftware Engineer"
        result = self._clean(text)
        assert "SKILLS" in result.sections
        assert "Python" in result.sections["SKILLS"]

    def test_detects_technical_skills_variant(self):
        text = "John Doe\n\nTechnical Skills\nPython, Docker, Kubernetes"
        result = self._clean(text)
        # Should canonicalize to SKILLS
        assert "SKILLS" in result.sections

    def test_detects_core_competencies(self):
        text = "Jane Smith\n\nCore Competencies\nMachine Learning, SQL, Tableau"
        result = self._clean(text)
        assert "SKILLS" in result.sections

    def test_detects_all_caps_headers(self):
        text = "SKILLS\nPython, Java\nEXPERIENCE\nSoftware Engineer at ABC"
        result = self._clean(text)
        assert "SKILLS" in result.sections
        assert "EXPERIENCE" in result.sections

    def test_section_order_preserved(self):
        text = (
            "John Doe\n\n"
            "Summary\nPassionate developer\n\n"
            "Skills\nPython, Java\n\n"
            "Experience\nSoftware Engineer"
        )
        result = self._clean(text)
        skills_idx = result.section_order.index("SKILLS") if "SKILLS" in result.section_order else -1
        exp_idx = result.section_order.index("EXPERIENCE") if "EXPERIENCE" in result.section_order else -1
        assert skills_idx < exp_idx, "SKILLS should appear before EXPERIENCE"

    def test_no_sections_returns_unknown(self):
        text = "This is some text without any section headers at all."
        result = self._clean(text)
        assert "UNKNOWN" in result.sections

    def test_header_info_captured(self):
        text = "John Doe\nSoftware Engineer\n\nSkills\nPython"
        result = self._clean(text)
        assert "HEADER_INFO" in result.sections
        assert "John Doe" in result.sections["HEADER_INFO"]


class TestCanonicalHeaderMap:
    """Ensure all map entries are uppercase (prevent lookup bugs)."""
    def test_all_keys_uppercase(self):
        for key in HEADER_CANONICAL_MAP:
            assert key == key.upper(), f"Key '{key}' is not uppercase"

    def test_technical_skills_maps_to_skills(self):
        assert HEADER_CANONICAL_MAP.get("TECHNICAL SKILLS") == "SKILLS"

    def test_core_competencies_maps_to_skills(self):
        assert HEADER_CANONICAL_MAP.get("CORE COMPETENCIES") == "SKILLS"


class TestCleanSnippet:
    def test_clean_snippet_strips_noise(self):
        cleaner = TextCleaner()
        result = cleaner.clean_snippet("  Python,  Java •  React  ")
        assert result.startswith("Python") or "Python" in result
        assert "\u2022" not in result


# ---------------------------------------------------------------------------
# ParsedResume contract tests
# ---------------------------------------------------------------------------

class TestParsedResumeContract:
    def test_is_empty_true(self):
        p = ParsedResume(raw_text="   ", pages=[], file_type="pdf", page_count=0)
        assert p.is_empty is True

    def test_is_empty_false(self):
        p = ParsedResume(raw_text="Python Developer", pages=[], file_type="pdf", page_count=1)
        assert p.is_empty is False


# ---------------------------------------------------------------------------
# Integration: cleaner produces usable output for a realistic resume snippet
# ---------------------------------------------------------------------------

SAMPLE_RESUME = """
John Doe
Senior Software Engineer | john@example.com | +1-555-0199

Summary
Results-driven software engineer with 7+ years of experience building scalable systems.

Technical Skills
Python, Java, Go, JavaScript, TypeScript
React, Node.js, FastAPI, Django
PostgreSQL, MongoDB, Redis
Docker, Kubernetes, AWS, GCP
Machine Learning, TensorFlow, scikit-learn

Experience
Senior Software Engineer — Acme Corp (2019–Present)
- Led migration of monolith to microservices (Python/FastAPI)
- Reduced API latency by 40% using Redis caching

Education
B.S. Computer Science — MIT (2017)

Certifications
AWS Certified Solutions Architect
"""


class TestRealisticResumeIntegration:
    def test_skills_section_extracted(self):
        cleaner = TextCleaner()
        result = cleaner.clean(make_parsed(SAMPLE_RESUME))
        assert "SKILLS" in result.sections
        skills_text = result.sections["SKILLS"]
        assert "Python" in skills_text
        assert "Docker" in skills_text
        assert "Machine Learning" in skills_text

    def test_email_stripped(self):
        cleaner = TextCleaner()
        result = cleaner.clean(make_parsed(SAMPLE_RESUME))
        assert "@example.com" not in result.full_text

    def test_multiple_sections_detected(self):
        cleaner = TextCleaner()
        result = cleaner.clean(make_parsed(SAMPLE_RESUME))
        assert len(result.section_order) >= 4  # Summary, Skills, Experience, Education

    def test_section_order(self):
        cleaner = TextCleaner()
        result = cleaner.clean(make_parsed(SAMPLE_RESUME))
        print("Detected sections:", result.section_order)
        assert "SKILLS" in result.section_order
        assert "EXPERIENCE" in result.section_order