"""
skill_extractor.py
------------------
Extracts skills from cleaned resume text using a FOUR-strategy pipeline
(NO LLM — fully offline, advanced heuristic extraction):

  Strategy 1 — Section-based parsing (PRIMARY, fastest)
    Detects the skills section using a comprehensive header dictionary,
    then splits the content into individual skill tokens.

  Strategy 2 — Full-document keyword matching (HIGH PRECISION)
    Scans ENTIRE resume text against 760+ known skills from SKILL_REGISTRY
    using word-boundary regex. Catches skills in Experience, Projects, etc.

  Strategy 3 — Contextual pattern extraction
    Regex patterns like "proficient in X", "experience with X", "built using X"
    to capture skills from natural language descriptions.

  Strategy 4 — spaCy NER (SUPPLEMENT, filtered)
    Runs NER only if previous strategies found < MIN combined skills.
    Heavy filtering to remove noise (emails, names, addresses).

The strategies are composed in extract_skills(), which merges and deduplicates.

Pipeline:
  resume_parser  →  text_cleaner  →  [THIS FILE]  →  normalization.py
"""

import logging
import re
import asyncio
import threading
from dataclasses import dataclass, field
from typing import Optional

from app.utils.text_cleaner import (
    is_likely_heading,
    normalize_skill_text,
    split_skill_tokens,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MIN_SECTION_SKILLS = 3
MIN_SKILL_LENGTH = 2
MAX_SKILL_LENGTH = 50

# Minimum combined skills from strategies 1-3 before we invoke NER
MIN_SKILLS_BEFORE_NER = 5

# ---------------------------------------------------------------------------
# Skills section header dictionary
# ---------------------------------------------------------------------------

SKILL_SECTION_HEADERS: dict[str, str] = {
    "skills": "Skills",
    "skill set": "Skill Set",
    "skillset": "Skillset",
    "key skills": "Key Skills",
    "core skills": "Core Skills",
    "relevant skills": "Relevant Skills",
    "professional skills": "Professional Skills",
    "summary of skills": "Summary of Skills",
    "skills summary": "Skills Summary",
    "skills & expertise": "Skills & Expertise",
    "skills and expertise": "Skills and Expertise",
    "skills & abilities": "Skills & Abilities",
    "skills and abilities": "Skills and Abilities",
    "technical skills": "Technical Skills",
    "technical expertise": "Technical Expertise",
    "technical competencies": "Technical Competencies",
    "technology skills": "Technology Skills",
    "technologies": "Technologies",
    "tech stack": "Tech Stack",
    "tools & technologies": "Tools & Technologies",
    "tools and technologies": "Tools and Technologies",
    "tools & frameworks": "Tools & Frameworks",
    "tools and frameworks": "Tools and Frameworks",
    "programming languages": "Programming Languages",
    "languages & frameworks": "Languages & Frameworks",
    "languages and frameworks": "Languages and Frameworks",
    "software skills": "Software Skills",
    "software & tools": "Software & Tools",
    "software and tools": "Software and Tools",
    "it skills": "IT Skills",
    "computer skills": "Computer Skills",
    "core competencies": "Core Competencies",
    "competencies": "Competencies",
    "key competencies": "Key Competencies",
    "areas of expertise": "Areas of Expertise",
    "expertise": "Expertise",
    "proficiencies": "Proficiencies",
    "qualifications": "Qualifications",
    "key qualifications": "Key Qualifications",
    "frameworks & libraries": "Frameworks & Libraries",
    "frameworks and libraries": "Frameworks and Libraries",
    "databases": "Databases",
    "cloud & devops": "Cloud & DevOps",
    "cloud and devops": "Cloud and DevOps",
    "devops skills": "DevOps Skills",
}

NON_SKILL_SECTION_HEADERS: set[str] = {
    "experience", "work experience", "professional experience",
    "employment history", "career history", "employment",
    "education", "academic background", "academic qualifications",
    "certifications", "certificates", "awards", "honors", "honours",
    "projects", "personal projects", "portfolio",
    "publications", "research", "volunteer", "volunteering",
    "languages", "interests", "hobbies", "references",
    "objective", "summary", "professional summary", "profile",
    "about me", "contact", "contact information", "personal information",
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SkillExtractionResult:
    skills: list[str] = field(default_factory=list)
    source: str = "none"
    section_header: Optional[str] = None
    confidence: float = 0.0

    @property
    def skill_count(self) -> int:
        return len(self.skills)

    def to_dict(self) -> dict:
        return {
            "skills": self.skills,
            "source": self.source,
            "section_header": self.section_header,
            "confidence": self.confidence,
            "skill_count": self.skill_count,
        }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_skills(cleaned_text: str) -> SkillExtractionResult:
    """
    Main entry point. Extracts skills from cleaned resume text.

    Pipeline (NO LLM — fully offline, optimized for speed):
      Strategy 1: Section-based parsing (fastest, highest precision)
      Strategy 2: Full-document keyword matching (high precision)
      Strategy 3: Contextual pattern extraction (medium precision)
      Strategy 4: spaCy NER (only if <5 skills found, filtered heavily)
      → All merged and deduplicated
    """
    if not cleaned_text or not cleaned_text.strip():
        logger.warning("extract_skills called with empty text")
        return SkillExtractionResult()

    # Offload the heavy, synchronous CPU-bound parsing to a background thread
    return await asyncio.to_thread(_extract_skills_sync, cleaned_text)


def _extract_skills_sync(cleaned_text: str) -> SkillExtractionResult:
    all_skills: list[str] = []
    source_parts: list[str] = []
    section_header = None
    best_confidence = 0.0

    # ── Strategy 1: Section-based parsing (FASTEST) ────────────────────────
    section_result = _extract_from_section(cleaned_text)
    if section_result.skills:
        all_skills.extend(section_result.skills)
        source_parts.append("section")
        section_header = section_result.section_header
        best_confidence = max(best_confidence, section_result.confidence)
        logger.info("Strategy 1 (Section): %d skills from '%s'",
                     len(section_result.skills), section_result.section_header)

    # ── Strategy 2: Full-document keyword matching (HIGH PRECISION) ────────
    keyword_result = _extract_from_keywords(cleaned_text)
    if keyword_result.skills:
        all_skills.extend(keyword_result.skills)
        source_parts.append("keyword")
        best_confidence = max(best_confidence, keyword_result.confidence)
        logger.info("Strategy 2 (Keyword): %d skills", len(keyword_result.skills))

    # ── Strategy 3: Contextual pattern extraction ──────────────────────────
    contextual_result = _extract_from_context(cleaned_text)
    if contextual_result.skills:
        all_skills.extend(contextual_result.skills)
        source_parts.append("contextual")
        best_confidence = max(best_confidence, contextual_result.confidence)
        logger.info("Strategy 3 (Contextual): %d skills", len(contextual_result.skills))

    # ── Strategy 4: spaCy NER (ONLY if few skills found so far) ───────────
    current_unique = len(set(s.lower() for s in all_skills))
    if current_unique < MIN_SKILLS_BEFORE_NER:
        ner_result = _extract_from_ner(cleaned_text)
        if ner_result.skills:
            all_skills.extend(ner_result.skills)
            source_parts.append("ner")
            best_confidence = max(best_confidence, ner_result.confidence)
            logger.info("Strategy 4 (NER): %d skills", len(ner_result.skills))

    # ── Merge and deduplicate ──────────────────────────────────────────────
    merged = _deduplicate(all_skills)

    if not merged:
        logger.warning("All strategies yielded 0 skills")
        return SkillExtractionResult()

    source = "+".join(source_parts) if len(source_parts) > 1 else (source_parts[0] if source_parts else "none")

    if len(source_parts) >= 3:
        best_confidence = min(1.0, best_confidence + 0.15)
    elif len(source_parts) >= 2:
        best_confidence = min(1.0, best_confidence + 0.1)

    logger.info("Final: %d unique skills from [%s] (confidence=%.2f)",
                len(merged), source, best_confidence)

    return SkillExtractionResult(
        skills=merged,
        source=source,
        section_header=section_header,
        confidence=best_confidence,
    )


def preload_models():
    """
    Pre-loads heavy models (spaCy) and compiles large regex patterns.
    Call this at application startup so the first user request doesn't hang.
    """
    logger.info("Pre-loading models for skill extraction...")
    _build_keyword_registry()
    _load_spacy_model()
    logger.info("Skill extraction models pre-loaded successfully.")


# ---------------------------------------------------------------------------
# Strategy 1: Section-based extraction
# ---------------------------------------------------------------------------

def _extract_from_section(text: str) -> SkillExtractionResult:
    lines = text.split("\n")
    location = _find_skills_section_lines(lines)

    if location is None:
        return SkillExtractionResult(source="section", confidence=0.0)

    start_idx, end_idx, header = location
    section_lines = lines[start_idx + 1 : end_idx]
    section_content = "\n".join(section_lines)

    raw_tokens = split_skill_tokens(section_content)
    skills = _filter_and_clean_tokens(raw_tokens)

    confidence = 1.0 if len(skills) >= MIN_SECTION_SKILLS else 0.6

    return SkillExtractionResult(
        skills=skills,
        source="section",
        section_header=header,
        confidence=confidence,
    )


def _find_skills_section_lines(lines: list[str]) -> Optional[tuple[int, int, str]]:
    header_idx: Optional[int] = None
    matched_header: Optional[str] = None

    for i, line in enumerate(lines):
        normalized = _normalize_header(line)

        if normalized in SKILL_SECTION_HEADERS:
            header_idx = i
            matched_header = line.strip()
            break

        if _is_partial_skills_header(normalized):
            header_idx = i
            matched_header = line.strip()
            break

    if header_idx is None:
        return None

    end_idx = _find_section_end(lines, header_idx + 1)
    return header_idx, end_idx, matched_header


def _find_section_end(lines: list[str], start_idx: int) -> int:
    consecutive_empty = 0

    for i in range(start_idx, len(lines)):
        line = lines[i].strip()

        if not line:
            consecutive_empty += 1
            if consecutive_empty > 3:
                return i
            continue

        consecutive_empty = 0
        normalized = _normalize_header(line)

        if normalized in NON_SKILL_SECTION_HEADERS:
            return i

        if normalized in SKILL_SECTION_HEADERS and i > start_idx:
            return i

        if is_likely_heading(line) and _looks_like_section_boundary(line, normalized):
            return i

    return len(lines)


def _looks_like_section_boundary(line: str, normalized: str) -> bool:
    boundary_keywords = {
        "experience", "employment", "education", "project",
        "certification", "award", "publication", "volunteer",
        "reference", "objective", "summary", "profile", "contact",
        "interest", "hobby", "language", "achievement",
    }
    words = set(normalized.split())
    return bool(words & boundary_keywords)


# ---------------------------------------------------------------------------
# Strategy 2: Full-document keyword matching (HIGH PRECISION)
# ---------------------------------------------------------------------------

_keyword_registry: Optional[dict[str, str]] = None
_keyword_pattern: Optional[re.Pattern] = None


def _build_keyword_registry() -> dict[str, str]:
    global _keyword_registry, _keyword_pattern
    if _keyword_registry is not None:
        return _keyword_registry

    try:
        from app.services.normalization import SKILL_REGISTRY
        registry: dict[str, str] = {}
        for canonical, aliases in SKILL_REGISTRY.items():
            registry[canonical.lower()] = canonical
            for alias in aliases:
                if len(alias) >= 2:          # skip single-char here; handled separately
                    registry[alias.lower()] = canonical

        # Build ONE compiled alternation regex — fastest multi-keyword search
        # Sort longest-first so longer aliases match before substrings
        sorted_aliases = sorted(registry.keys(), key=len, reverse=True)
        escaped = [re.escape(a) for a in sorted_aliases]
        pattern_str = r'(?i)(?:^|(?<=[\s,;|(]))(' + '|'.join(escaped) + r')(?=[\s,;|)/\.\-:]|$)'
        _keyword_pattern = re.compile(pattern_str)

        _keyword_registry = registry
        logger.info(
            "Keyword registry: %d aliases, single-regex compiled",
            len(registry),
        )
        return registry
    except ImportError:
        logger.error("Could not import SKILL_REGISTRY")
        _keyword_registry = {}
        return {}


def _extract_from_keywords(text: str) -> SkillExtractionResult:
    """
    Scan the ENTIRE resume text for known skill keywords using a single
    pre-compiled alternation regex — O(text_length) instead of O(n_aliases).
    """
    registry = _build_keyword_registry()
    if not registry or _keyword_pattern is None:
        return SkillExtractionResult(source="keyword", confidence=0.0)

    found_canonicals: set[str] = set()
    for match in _keyword_pattern.finditer(text):
        alias = match.group(1).lower()
        canonical = registry.get(alias)
        if canonical:
            found_canonicals.add(canonical)

    # Handle single-char skills (R, C) separately with strict context
    for alias, canonical in registry.items():
        if len(alias) == 1 and alias in {"r", "c"}:
            pattern = r'(?:^|[\s,;|(/])' + re.escape(alias.upper()) + r'(?:[\s,;|)/.]|$)'
            if re.search(pattern, text):
                found_canonicals.add(canonical)

    skills = sorted(found_canonicals)
    return SkillExtractionResult(
        skills=skills,
        source="keyword",
        confidence=0.85 if len(skills) >= 5 else 0.6 if skills else 0.0,
    )


# ---------------------------------------------------------------------------
# Strategy 3: Contextual pattern extraction
# ---------------------------------------------------------------------------

_CONTEXT_PATTERNS = [
    re.compile(r'(?:proficient|experienced|skilled|expertise|competent|adept)\s+(?:in|with|at)\s+([^.;\n]{3,80})', re.IGNORECASE),
    re.compile(r'(?:worked|working|work)\s+(?:with|on|in)\s+([^.;\n]{3,60})', re.IGNORECASE),
    re.compile(r'(?:built|developed|created|designed|implemented|deployed|architected)\s+(?:using|with|in|on)\s+([^.;\n]{3,60})', re.IGNORECASE),
    re.compile(r'(?:hands-on|practical|extensive|strong)\s+(?:experience|knowledge|background)\s+(?:with|in|of)\s+([^.;\n]{3,60})', re.IGNORECASE),
    re.compile(r'(?:tools|technologies|tech\s*stack|stack|platforms?)\s*[:]\s*([^.;\n]{3,100})', re.IGNORECASE),
    re.compile(r'(?:familiar|familiarity)\s+with\s+([^.;\n]{3,60})', re.IGNORECASE),
    re.compile(r'(?:knowledge|understanding)\s+of\s+([^.;\n]{3,60})', re.IGNORECASE),
]


def _extract_from_context(text: str) -> SkillExtractionResult:
    all_tokens: list[str] = []

    for pattern in _CONTEXT_PATTERNS:
        for match in pattern.finditer(text):
            captured = match.group(1).strip()
            tokens = split_skill_tokens(captured)
            all_tokens.extend(tokens)

    skills = _filter_and_clean_tokens(all_tokens)

    return SkillExtractionResult(
        skills=skills,
        source="contextual",
        confidence=0.65 if len(skills) >= 3 else 0.4 if skills else 0.0,
    )


# ---------------------------------------------------------------------------
# Strategy 4: spaCy NER (ONLY runs as fallback, heavily filtered)
# ---------------------------------------------------------------------------

import threading
_spacy_nlp = None
_spacy_lock = threading.Lock()


def _load_spacy_model():
    global _spacy_nlp
    if _spacy_nlp is not None:
        return _spacy_nlp

    with _spacy_lock:
        if _spacy_nlp is not None:
            return _spacy_nlp

        try:
            import spacy
            try:
                _spacy_nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded spaCy model: en_core_web_sm")
            except OSError:
                logger.warning("en_core_web_sm not found — NER skipped")
                _spacy_nlp = spacy.blank("en")
            return _spacy_nlp
        except ImportError:
            logger.error("spaCy not installed")
            return None


def _extract_from_ner(text: str) -> SkillExtractionResult:
    """
    spaCy NER — ONLY runs when other strategies found few skills.
    Extracts ORG and PRODUCT entities only (most likely to be tools/platforms).
    Heavily filtered to remove noise.
    """
    nlp = _load_spacy_model()
    if nlp is None:
        return SkillExtractionResult(source="ner", confidence=0.0)

    # Truncate for speed — 5000 chars is enough for NER
    truncated = text[:5000]
    doc = nlp(truncated)

    candidates: list[str] = []

    # Only ORG and PRODUCT entities — these are most likely tools/platforms
    for ent in doc.ents:
        if ent.label_ in ("ORG", "PRODUCT"):
            ent_text = ent.text.strip()
            if MIN_SKILL_LENGTH <= len(ent_text) <= MAX_SKILL_LENGTH:
                # Only add if it looks like a tech skill (not a person/company name)
                if not _is_ner_noise(ent_text):
                    candidates.append(ent_text)

    skills = _filter_and_clean_tokens(candidates)

    return SkillExtractionResult(
        skills=skills,
        source="ner",
        confidence=0.4 if skills else 0.0,
    )


# ---------------------------------------------------------------------------
# AGGRESSIVE noise filtering
# ---------------------------------------------------------------------------

# Compile patterns once for speed
_RE_EMAIL = re.compile(r'^[\w.+-]+@[\w-]+\.\w+$')
_RE_URL = re.compile(r'^(https?://|www\.)', re.IGNORECASE)
_RE_PHONE = re.compile(r'^[\d\s\-+().]{7,}$')
_RE_DATE = re.compile(r'^\d{4}([-–]\d{4})?$')
_RE_DATE2 = re.compile(r'^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{4}', re.IGNORECASE)
_RE_PURE_NUMBER = re.compile(r'^\d+\.?\d*$')
_RE_LOCATION = re.compile(r'^[A-Z][a-z]+,\s*[A-Z]', re.IGNORECASE)  # "Bangalore, India"
_RE_NAME_LIKE = re.compile(r'^[A-Z][a-z]+ [A-Z][a-z]+$')  # "John Smith"

# Words that are NEVER skills
_NOISE_TOKENS: set[str] = {
    # Personal / articles
    "i", "me", "my", "we", "our", "the", "a", "an", "to", "of", "in", "for",
    "on", "at", "by", "is", "it", "as", "be", "am", "are", "was", "were",
    # Resume filler
    "etc", "and", "or", "with", "using", "via", "including", "such",
    "strong", "good", "excellent", "proficient", "knowledge",
    "experience", "ability", "understanding", "familiar", "familiarity",
    "working knowledge", "hands-on", "exposure", "well versed",
    # Generic descriptors
    "various", "multiple", "several", "many", "other", "others",
    "tools", "technologies", "skills", "skill", "area", "areas",
    "environment", "environments", "solution", "solutions",
    "system", "systems", "platform", "platforms", "service", "services",
    "application", "applications", "language", "languages",
    "software", "hardware", "elective", "electives", "framework",
    "frameworks", "database", "databases", "methodology", "methodologies",
    # Time
    "year", "years", "month", "months", "present", "current", "day", "days",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
    # Common verbs
    "developed", "built", "created", "designed", "implemented",
    "managed", "utilized", "leveraged", "worked", "working",
    "responsible", "responsible for", "collaborated", "assisted",
    # Resume structure words
    "team", "project", "projects", "company", "organization",
    "department", "university", "college", "school", "institute",
    "intern", "internship", "role", "position", "title",
    # Common non-skill words that leak through
    "india", "usa", "uk", "new york", "bangalore", "mumbai", "delhi",
    "hyderabad", "pune", "chennai", "remote", "onsite", "hybrid",
    "full time", "part time", "contract", "freelance",
    "mr", "mrs", "ms", "dr", "bachelor", "master", "degree",
    "cgpa", "gpa", "percentage", "result", "grade",
    "name", "email", "phone", "address", "linkedin", "github",
}


def _is_noise_token(skill: str) -> bool:
    """Aggressively filter non-skill tokens."""
    lower = skill.lower().strip()

    # Empty or too short
    if not lower or len(lower) < MIN_SKILL_LENGTH:
        return True

    # Pure numbers
    if _RE_PURE_NUMBER.match(lower):
        return True

    # In noise list
    if lower in _NOISE_TOKENS:
        return True

    # Email address
    if _RE_EMAIL.match(lower):
        return True

    # URL
    if _RE_URL.match(lower):
        return True

    # Phone number
    if _RE_PHONE.match(lower):
        return True

    # Date patterns
    if _RE_DATE.match(lower):
        return True
    if _RE_DATE2.match(lower):
        return True

    # Location patterns ("Bangalore, India")
    if _RE_LOCATION.match(skill):
        return True

    # Person name pattern ("John Smith") — two capitalized words only
    if _RE_NAME_LIKE.match(skill) and len(skill.split()) == 2:
        # But allow tech terms like "Apache Kafka", "Google Cloud"
        first_word = skill.split()[0].lower()
        tech_prefixes = {"apache", "google", "amazon", "microsoft", "react", "angular", "vue", "spring", "ruby"}
        if first_word not in tech_prefixes:
            return True

    # Single character (except known valid: R, C)
    if len(lower) == 1 and lower not in {"r", "c"}:
        return True

    # Too many words — likely a sentence fragment
    if len(lower.split()) > 4:
        return True

    # Contains @ — email fragment
    if "@" in lower:
        return True

    # Starts with digit and contains spaces — likely a date or ID
    if lower[0].isdigit() and " " in lower:
        return True

    return False


def _is_ner_noise(text: str) -> bool:
    """Additional noise filter specifically for NER entities."""
    lower = text.lower()

    # Common company/org names that are NOT tech skills
    non_skill_orgs = {
        "google", "microsoft", "amazon", "apple", "facebook", "meta",
        "netflix", "uber", "airbnb", "twitter", "linkedin", "tcs",
        "infosys", "wipro", "cognizant", "accenture", "ibm",
    }
    if lower in non_skill_orgs:
        return True

    # If it's a general noise token
    if _is_noise_token(text):
        return True

    return False


# ---------------------------------------------------------------------------
# Token filtering and deduplication
# ---------------------------------------------------------------------------

def _filter_and_clean_tokens(raw_tokens: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()

    for token in raw_tokens:
        skill = normalize_skill_text(token)

        if not skill:
            continue

        if len(skill) < MIN_SKILL_LENGTH or len(skill) > MAX_SKILL_LENGTH:
            continue

        if _is_noise_token(skill):
            continue

        key = skill.lower()
        if key in seen:
            continue

        seen.add(key)
        cleaned.append(skill)

    return cleaned


def _deduplicate(skills: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for skill in skills:
        key = skill.lower()
        if key not in seen:
            seen.add(key)
            result.append(skill)
    return result


# ---------------------------------------------------------------------------
# Header normalization helpers
# ---------------------------------------------------------------------------

def _normalize_header(line: str) -> str:
    normalized = line.strip().lower()
    normalized = normalized.rstrip(":.-–—")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _is_partial_skills_header(normalized: str) -> bool:
    skills_keywords = {
        "skills", "competencies", "expertise", "proficiencies",
        "technologies", "tech stack", "toolset",
    }
    words = set(normalized.split())

    if normalized in skills_keywords:
        return True

    if words & skills_keywords and len(normalized) <= 50:
        non_skill_words = {
            "experience", "education", "employment", "history",
            "project", "certification", "award"
        }
        if not (words & non_skill_words):
            return True

    return False