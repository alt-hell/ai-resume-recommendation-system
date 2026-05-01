"""
text_cleaner.py
---------------
Normalizes raw resume text extracted by resume_parser.py.

Responsibilities:
- Remove noise: URLs, emails, phone numbers, special Unicode chars
- Normalize whitespace (tabs → spaces, multiple spaces → single)
- Preserve section headers (critical for skill_extractor.py)
- Detect and tag section boundaries
- Produce a CleanedResume object consumed by skill_extractor.py

Design note:
    We deliberately do NOT lowercase everything here.
    Section headers need their original casing for pattern matching
    (e.g., "SKILLS", "Skills", "Technical Skills" all valid).
    Case normalization happens only where explicitly needed.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

from app.services.resume_parser import ParsedResume

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data contract returned by text_cleaner
# ---------------------------------------------------------------------------

@dataclass
class CleanedResume:
    """Output of the text-cleaning stage. Consumed by skill_extractor.py."""
    full_text: str                        # Complete cleaned text
    sections: dict[str, str]             # { "SKILLS": "Python, Java...", ... }
    section_order: list[str]             # Preserved order of detected sections
    original_line_count: int             # For diagnostics
    cleaned_line_count: int
    detected_section_headers: list[str]  # Raw headers found in the resume


# ---------------------------------------------------------------------------
# Known section header patterns (order matters — more specific first)
# ---------------------------------------------------------------------------

# Each entry is a compiled regex that matches a section heading line.
# Groups are not used — we just test for a match.
SECTION_HEADER_PATTERNS: list[re.Pattern] = [
    re.compile(r"^(TECHNICAL\s+SKILLS?|Technical\s+Skills?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(CORE\s+COMPETENCIES|Core\s+Competencies)[\s:]*$", re.MULTILINE),
    re.compile(r"^(KEY\s+SKILLS?|Key\s+Skills?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(PROFESSIONAL\s+SKILLS?|Professional\s+Skills?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(SKILLS?\s+&\s+EXPERTISE|Skills?\s+&\s+Expertise)[\s:]*$", re.MULTILINE),
    re.compile(r"^(SKILLS?\s+SUMMARY|Skills?\s+Summary)[\s:]*$", re.MULTILINE),
    re.compile(r"^(SKILLS?|Skills?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(WORK\s+EXPERIENCE|Work\s+Experience|PROFESSIONAL\s+EXPERIENCE|Professional\s+Experience)[\s:]*$", re.MULTILINE),
    re.compile(r"^(EXPERIENCE|Experience)[\s:]*$", re.MULTILINE),
    re.compile(r"^(EDUCATION|Education)[\s:]*$", re.MULTILINE),
    re.compile(r"^(CERTIFICATIONS?|Certifications?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(PROJECTS?|Projects?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(SUMMARY|Summary|PROFESSIONAL\s+SUMMARY|Professional\s+Summary)[\s:]*$", re.MULTILINE),
    re.compile(r"^(OBJECTIVE|Objective|CAREER\s+OBJECTIVE|Career\s+Objective)[\s:]*$", re.MULTILINE),
    re.compile(r"^(AWARDS?|Awards?|ACHIEVEMENTS?|Achievements?|HONORS?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(PUBLICATIONS?|Publications?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(LANGUAGES?|Languages?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(INTERESTS?|Interests?|HOBBIES|Hobbies)[\s:]*$", re.MULTILINE),
    re.compile(r"^(REFERENCES?|References?)[\s:]*$", re.MULTILINE),
    re.compile(r"^(CONTACT|Contact|PERSONAL\s+INFORMATION|Personal\s+Information)[\s:]*$", re.MULTILINE),
]

# Canonical names mapped from detected headers (for dict keys)
HEADER_CANONICAL_MAP: dict[str, str] = {
    # Skills variants → SKILLS
    "TECHNICAL SKILLS": "SKILLS",
    "TECHNICAL SKILL": "SKILLS",
    "CORE COMPETENCIES": "SKILLS",
    "KEY SKILLS": "SKILLS",
    "KEY SKILL": "SKILLS",
    "PROFESSIONAL SKILLS": "SKILLS",
    "PROFESSIONAL SKILL": "SKILLS",
    "SKILLS & EXPERTISE": "SKILLS",
    "SKILL & EXPERTISE": "SKILLS",
    "SKILLS SUMMARY": "SKILLS",
    "SKILL SUMMARY": "SKILLS",
    "SKILL": "SKILLS",
    # Experience variants → EXPERIENCE
    "WORK EXPERIENCE": "EXPERIENCE",
    "PROFESSIONAL EXPERIENCE": "EXPERIENCE",
    # Summary variants → SUMMARY
    "PROFESSIONAL SUMMARY": "SUMMARY",
    "CAREER OBJECTIVE": "OBJECTIVE",
}


# ---------------------------------------------------------------------------
# Noise patterns (to remove from text)
# ---------------------------------------------------------------------------

_RE_URL = re.compile(
    r"https?://\S+|www\.\S+|ftp://\S+",
    re.IGNORECASE,
)
_RE_EMAIL = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Z|a-z]{2,7}\b"
)
_RE_PHONE = re.compile(
    r"(\+?\d[\d\s\-().]{7,}\d)"
)
_RE_LINKEDIN = re.compile(
    r"linkedin\.com/\S*",
    re.IGNORECASE,
)
_RE_GITHUB = re.compile(
    r"github\.com/\S*",
    re.IGNORECASE,
)
# Lines that are purely decorative (dashes, equals, underscores, pipes)
_RE_DECORATIVE_LINE = re.compile(
    r"^[\-=_|*•#~\s]{3,}$"
)
# Excessive punctuation / special chars (keep periods, commas, colons, slashes)
_RE_JUNK_CHARS = re.compile(
    r"[^\w\s,.:;/&()\-+#@$%'\"!\?\n]"
)
# Multiple consecutive blank lines → one blank line
_RE_MULTI_BLANK = re.compile(r"\n{3,}")
# Multiple spaces → single space
_RE_MULTI_SPACE = re.compile(r"[ \t]+")


# ---------------------------------------------------------------------------
# Main cleaner class
# ---------------------------------------------------------------------------

class TextCleaner:
    """
    Cleans raw resume text and splits it into labelled sections.

    Usage:
        cleaner = TextCleaner()
        cleaned = cleaner.clean(parsed_resume)
    """

    def __init__(
        self,
        remove_urls: bool = True,
        remove_emails: bool = True,
        remove_phones: bool = False,   # Keep phones — sometimes in skills context
        remove_social_links: bool = True,
    ):
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_phones = remove_phones
        self.remove_social_links = remove_social_links

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clean(self, parsed: ParsedResume) -> CleanedResume:
        """
        Full cleaning pipeline.

        Steps:
            1. Unicode normalization
            2. Remove noise (URLs, emails, social links)
            3. Normalize whitespace
            4. Remove decorative lines
            5. Detect and extract sections

        Args:
            parsed: ParsedResume from resume_parser.py

        Returns:
            CleanedResume with full_text and sections dict.
        """
        raw = parsed.raw_text
        original_line_count = raw.count("\n")

        # Step 1: Normalize Unicode (curly quotes, em-dashes, non-breaking spaces, etc.)
        text = self._normalize_unicode(raw)

        # Step 2: Remove noise
        text = self._remove_noise(text)

        # Step 3: Clean whitespace (preserve newlines for section detection)
        text = self._clean_whitespace(text)

        # Step 4: Remove decorative separator lines
        text = self._remove_decorative_lines(text)

        # Step 5: Collapse excessive blank lines
        text = _RE_MULTI_BLANK.sub("\n\n", text).strip()

        cleaned_line_count = text.count("\n")

        # Step 6: Detect and split into sections
        sections, section_order, detected_headers = self._split_sections(text)

        logger.debug(
            "Cleaned resume: %d → %d lines | Sections found: %s",
            original_line_count,
            cleaned_line_count,
            section_order,
        )

        return CleanedResume(
            full_text=text,
            sections=sections,
            section_order=section_order,
            original_line_count=original_line_count,
            cleaned_line_count=cleaned_line_count,
            detected_section_headers=detected_headers,
        )

    def clean_snippet(self, text: str) -> str:
        """
        Lightweight cleaning for a short text snippet (skill line, etc.).
        Does NOT do section detection — just noise removal + whitespace.
        """
        text = self._normalize_unicode(text)
        text = self._remove_noise(text)
        text = self._clean_whitespace(text)
        return text.strip()

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_unicode(text: str) -> str:
        """
        Convert to NFC form and replace common Unicode substitutes:
        - Non-breaking spaces → regular space
        - Em/en dashes → hyphen (avoids "Python–Java" being treated as one token)
        - Curly quotes → straight quotes
        - Bullet variants → "-"
        """
        # NFC normalization first
        text = unicodedata.normalize("NFC", text)

        replacements = {
            "\u00a0": " ",   # non-breaking space
            "\u2013": "-",   # en dash
            "\u2014": "-",   # em dash
            "\u2018": "'",   # left single quotation
            "\u2019": "'",   # right single quotation
            "\u201c": '"',   # left double quotation
            "\u201d": '"',   # right double quotation
            "\u2022": "-",   # bullet •
            "\u25cf": "-",   # black circle ●
            "\u25aa": "-",   # small black square ▪
            "\u2023": "-",   # triangular bullet ‣
            "\u25e6": "-",   # white bullet ◦
            "\u2043": "-",   # hyphen bullet ⁃
            "\ufeff": "",    # BOM
            "\u200b": "",    # zero-width space
            "\t": " ",       # tab → space (will be collapsed later)
        }

        for src, dst in replacements.items():
            text = text.replace(src, dst)

        return text

    def _remove_noise(self, text: str) -> str:
        """Remove URLs, emails, phone numbers, and social profile links."""
        if self.remove_social_links:
            text = _RE_LINKEDIN.sub("", text)
            text = _RE_GITHUB.sub("", text)
        if self.remove_urls:
            text = _RE_URL.sub("", text)
        if self.remove_emails:
            text = _RE_EMAIL.sub("", text)
        if self.remove_phones:
            text = _RE_PHONE.sub("", text)
        return text

    @staticmethod
    def _clean_whitespace(text: str) -> str:
        """
        Normalize spaces within lines, preserve newlines.
        We split on newlines, clean each line, then rejoin.
        """
        cleaned_lines = []
        for line in text.split("\n"):
            # Collapse multiple spaces/tabs within a line
            line = _RE_MULTI_SPACE.sub(" ", line).strip()
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    @staticmethod
    def _remove_decorative_lines(text: str) -> str:
        """
        Remove lines that are purely decorative (e.g., "----------", "=====").
        These appear in many resume templates as section dividers.
        """
        lines = text.split("\n")
        filtered = [
            line for line in lines
            if not _RE_DECORATIVE_LINE.match(line)
        ]
        return "\n".join(filtered)

    def _split_sections(
        self, text: str
    ) -> tuple[dict[str, str], list[str], list[str]]:
        """
        Detect section headers and split the cleaned text into labelled chunks.

        Strategy:
            1. Scan every line to check if it matches a section header pattern.
            2. Use positions to slice the text between consecutive headers.
            3. Canonicalize header names for consistent downstream usage.

        Returns:
            sections       : { "SKILLS": "Python, Java...", "EXPERIENCE": "...", ... }
            section_order  : ["SUMMARY", "SKILLS", "EXPERIENCE", ...]
            detected_headers: raw header strings found in text
        """
        lines = text.split("\n")
        header_positions: list[tuple[int, str]] = []  # (line_index, raw_header)

        for idx, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            if self._is_section_header(stripped):
                header_positions.append((idx, stripped))

        # If no headers detected, return the whole text under "UNKNOWN"
        if not header_positions:
            logger.warning("No section headers detected in resume text.")
            return {"UNKNOWN": text}, ["UNKNOWN"], []

        sections: dict[str, str] = {}
        section_order: list[str] = []
        detected_headers: list[str] = []

        # Text before the first header → "HEADER_INFO" (name, contact)
        if header_positions[0][0] > 0:
            pre_header_text = "\n".join(lines[: header_positions[0][0]]).strip()
            if pre_header_text:
                sections["HEADER_INFO"] = pre_header_text
                section_order.append("HEADER_INFO")

        # Slice between consecutive headers
        for i, (start_line, raw_header) in enumerate(header_positions):
            end_line = (
                header_positions[i + 1][0]
                if i + 1 < len(header_positions)
                else len(lines)
            )

            # Content is everything between this header and the next
            content_lines = lines[start_line + 1 : end_line]
            content = "\n".join(content_lines).strip()

            # Canonicalize the header name
            canonical = self._canonicalize_header(raw_header)

            detected_headers.append(raw_header)

            # Handle duplicate sections (e.g., multiple "Skills" blocks)
            if canonical in sections:
                sections[canonical] += "\n" + content
            else:
                sections[canonical] = content
                section_order.append(canonical)

        return sections, section_order, detected_headers

    # ------------------------------------------------------------------
    # Header detection helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_section_header(line: str) -> bool:
        """
        Return True if this line looks like a resume section header.

        Criteria:
        - Matches one of our known patterns, OR
        - Is short (≤ 5 words), ALL-CAPS, with no sentence punctuation

        The second criterion catches custom/unusual headers like
        "AWARDS & RECOGNITION" that may not be in our pattern list.
        """
        # Check known patterns
        for pattern in SECTION_HEADER_PATTERNS:
            if pattern.match(line.strip()):
                return True

        # Heuristic: short all-caps line without terminal punctuation
        stripped = line.strip().rstrip(":").strip()
        words = stripped.split()
        if (
            1 <= len(words) <= 5
            and stripped == stripped.upper()
            and not any(ch in stripped for ch in [".", "!", "?"])
            and len(stripped) >= 4   # avoid matching "A", "AI", etc.
        ):
            return True

        return False

    @staticmethod
    def _canonicalize_header(raw: str) -> str:
        """
        Normalize a raw header string to a canonical uppercase key.
        E.g., "Technical Skills:" → "SKILLS"
        """
        normalized = raw.strip().rstrip(":").strip().upper()
        return HEADER_CANONICAL_MAP.get(normalized, normalized)


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------

def clean_resume_text(
    parsed: ParsedResume,
    remove_phones: bool = False,
) -> CleanedResume:
    """
    Clean and structure a ParsedResume.

    This is the **only function** the rest of the application should call.

    Args:
        parsed        : Output from resume_parser.parse_resume()
        remove_phones : Whether to strip phone numbers (default False)

    Returns:
        CleanedResume with full_text and sections dict.

    Example:
        >>> parsed = parse_resume("resume.pdf")
        >>> cleaned = clean_resume_text(parsed)
        >>> print(cleaned.sections.get("SKILLS", "No skills section found"))
    """
    cleaner = TextCleaner(remove_phones=remove_phones)
    return cleaner.clean(parsed)


def clean_raw_text(text: str) -> str:
    """
    Utility: clean a plain string (no ParsedResume needed).
    Used for quick cleaning of individual fields or snippets.

    Example:
        >>> clean_raw_text("  Python,  Java •  React  ")
        "Python, Java - React"
    """
    # Wrap in a minimal ParsedResume for consistent processing
    dummy = ParsedResume(
        raw_text=text,
        pages=[text],
        file_type="txt",
        page_count=1,
    )
    cleaner = TextCleaner()
    return cleaner.clean(dummy).full_text


# ---------------------------------------------------------------------------
# Public helpers consumed by skill_extractor.py
# ---------------------------------------------------------------------------

def is_likely_heading(line: str) -> bool:
    """
    Return True if the line looks like a section heading.

    Criteria (any one sufficient):
      - Line matches a known SECTION_HEADER_PATTERN
      - Short (≤ 5 words), ALL-CAPS or Title Case, no terminal punctuation

    Used by skill_extractor._find_section_end() to detect section boundaries.
    """
    stripped = line.strip()
    if not stripped:
        return False

    # Known pattern match
    for pattern in SECTION_HEADER_PATTERNS:
        if pattern.match(stripped):
            return True

    # Heuristic: short all-caps line without sentence punctuation
    words = stripped.split()
    if (
        1 <= len(words) <= 5
        and stripped == stripped.upper()
        and not any(ch in stripped for ch in [".", "!", "?"])
        and len(stripped) >= 4
    ):
        return True

    return False


def normalize_skill_text(raw: str) -> str:
    """
    Lightly normalize a raw skill token string.

    Steps:
      1. Strip surrounding whitespace and common punctuation
      2. Collapse internal whitespace
      3. Remove leading bullet / dash characters
      4. Strip wrapping parentheses/brackets

    Returns the cleaned string, or '' if the result is empty.

    Used by skill_extractor._filter_and_clean_tokens().
    """
    if not raw:
        return ""

    # Strip surrounding whitespace
    text = raw.strip()

    # Remove leading bullet/dash/asterisk characters, including 'o '
    text = re.sub(r"^[\-•●▪▸►◦⁃\*oO]\s+", "", text)
    text = re.sub(r"^[\-•●▪▸►◦⁃\*]+\s*", "", text)

    # Remove leading numbering like "1. ", "1) ", "(1) "
    text = re.sub(r"^\(?\d+[.)]+\s*", "", text)

    # Remove categorical prefixes like "Programming Skills - ", "Tools: "
    # Safe match: requires spaces around dash/colon or end of word followed by colon
    text = re.sub(r"^[A-Za-z0-9\s/]+\s+[\-:\u2013\u2014]\s+", "", text)
    text = re.sub(r"^[A-Za-z0-9\s/]+:\s*", "", text)

    # Remove wrapping parentheses/brackets if the entire token is wrapped
    text = re.sub(r"^\((.+)\)$", r"\1", text)
    text = re.sub(r"^\[(.+)\]$", r"\1", text)

    # Remove trailing punctuation
    text = text.rstrip(".,;:•●-")

    # Collapse internal whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


# Separators used by split_skill_tokens to tokenize skill section content
_SKILL_SEPARATORS = re.compile(
    r"[,;\n\t]|"           # comma, semicolon, newline, tab
    r"\s*\|\s*|"           # pipe with optional surrounding spaces
    r"\s+(?:and|&)\s+|"    # split on ' and ', ' & '
    r"\s{2,}|"             # 2+ spaces (common in formatted skill lists)
    r"•|●|▪|▸|►|◦|⁃|\*|"  # bullet variants
    r"(?:^|\n)\s*[-–]\s+"  # lines starting with dashes like "- Python"
)

# Pattern to detect if a token contains parenthetical sub-skills
# e.g. "Natural Language Processing (text preprocessing, text)"
_RE_PAREN_SUBSKILLS = re.compile(r"^(.+?)\s*\(([^)]+)\)\s*$")

# Pattern to detect "using" or "with" clauses that contain sub-skills
# e.g. "Large Language Models (LLMs) using LangChain"
_RE_USING_CLAUSE = re.compile(
    r"^(.+?)\s+(?:using|with|via|through|including)\s+(.+)$",
    re.IGNORECASE,
)

# Slash separator (split on slash, but logic below preserves CI/CD)
_RE_SLASH_SPLIT = re.compile(r"\s*/\s*")


def split_skill_tokens(section_content: str) -> list[str]:
    """
    Split raw skills section content into individual skill token strings.

    Handles the wide variety of formats found in real resumes:
      - Comma-separated:  "Python, Java, SQL"
      - Pipe-separated:   "Python | Java | SQL"
      - Semicolon-sep:    "Python; Java; SQL"
      - Bullet points:    "• Python\n• Java\n• SQL"
      - Dash-prefixed:    "- Python\n- Java\n- SQL"
      - Line-per-skill:   "Python\nJava\nSQL"
      - Mixed:            "Python, Java\n• Docker | Kubernetes"
      - Parenthetical:    "NLP (text preprocessing, text)" → NLP, text preprocessing
      - Using clauses:    "LLMs using LangChain" → LLMs, LangChain
      - Slash-separated:  "Python/Java/SQL" → Python, Java, SQL
                          but "CI/CD" stays as "CI/CD"

    Returns a list of raw (uncleaned) token strings.
    Cleaning is done separately by _filter_and_clean_tokens().

    Used by skill_extractor._extract_from_section().
    """
    if not section_content or not section_content.strip():
        return []

    # Primary split: commas, pipes, semicolons, bullets, newlines, etc.
    tokens = _SKILL_SEPARATORS.split(section_content)
    tokens = [t.strip() for t in tokens if t and t.strip()]

    # Secondary: expand parenthetical sub-skills and using-clauses
    expanded = []
    for token in tokens:
        if not token:
            continue

        # Handle "NLP (text preprocessing, text)" → ["NLP", "text preprocessing", "text"]
        paren_match = _RE_PAREN_SUBSKILLS.match(token)
        if paren_match:
            main_skill = paren_match.group(1).strip()
            sub_content = paren_match.group(2).strip()
            # Add the main skill
            if main_skill:
                expanded.append(main_skill)
            # Split sub-content on commas, pipes, semicolons
            sub_parts = re.split(r"[,;|]", sub_content)
            for sp in sub_parts:
                sp = sp.strip()
                if sp and len(sp) >= 2:
                    expanded.append(sp)
            continue

        # Handle "LLMs using LangChain" → ["LLMs", "LangChain"]
        using_match = _RE_USING_CLAUSE.match(token)
        if using_match:
            main_part = using_match.group(1).strip()
            tool_part = using_match.group(2).strip()
            if main_part:
                expanded.append(main_part)
            # Tool part may itself be comma-separated
            tool_parts = re.split(r"[,;|]", tool_part)
            for tp in tool_parts:
                tp = tp.strip()
                if tp and len(tp) >= 2:
                    expanded.append(tp)
            continue

        # Handle slash-separated skills: "Python/Java/SQL" → split
        # but preserve compound terms like "CI/CD", "UI/UX", "TCP/IP", "PL/SQL"
        if "/" in token:
            slash_parts = _RE_SLASH_SPLIT.split(token)
            # Only split if both sides are not short acronyms
            if len(slash_parts) > 1 and all(len(p.strip()) > 2 for p in slash_parts):
                expanded.extend([p.strip() for p in slash_parts if p.strip()])
                continue

        expanded.append(token)

    return expanded
