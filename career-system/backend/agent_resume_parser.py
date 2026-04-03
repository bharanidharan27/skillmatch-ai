"""
agent_resume_parser.py – Agent 1: Resume Parser.

Uses spaCy (en_core_web_sm) + rule-based extraction to parse structured
information from preprocessed resumes:
  - Skills (via dictionary matching)
  - Years of experience (regex patterns)
  - Education level
  - Job titles mentioned
  - Tools / technologies

Skills are scored by frequency, recency (later sections weighted higher),
and section-based weights.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

import spacy

from config import PARAMS
from skill_dictionary import SkillLookup, load_dictionary

# ── Lazy spaCy loading ──────────────────────────────────────────────────────

_NLP: Optional[spacy.language.Language] = None


def _get_nlp() -> spacy.language.Language:
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm", disable=["ner", "textcat"])
    return _NLP


# ── Regex patterns ──────────────────────────────────────────────────────────

_YEARS_EXP_RE = re.compile(
    r"(\d{1,2})\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:\w+\s+){0,3}(?:experience|exp)",
    re.IGNORECASE,
)

# Match date ranges like "2020-Present", "Jan 2017 - Dec 2020", "2015 – 2019"
# Captures optional month groups plus the year groups
_DATE_RANGE_RE = re.compile(
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?)?\s*"
    r"(20\d{2}|19\d{2})"
    r"\s*[\-–—to]+\s*"
    r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?)?\s*"
    r"(20\d{2}|19\d{2}|[Pp]resent|[Cc]urrent|[Nn]ow)",
    re.IGNORECASE,
)

# Month name to number
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_EDUCATION_LEVELS = [
    (re.compile(r"\b(?:ph\.?d|doctorate|doctor of philosophy)\b", re.I), "PhD"),
    (re.compile(r"\b(?:master'?s?|m\.?s\.?|m\.?tech|mba|m\.?b\.?a)\b", re.I), "Masters"),
    (re.compile(r"\b(?:bachelor'?s?|b\.?s\.?|b\.?tech|b\.?e\.?|b\.?a\.?|b\.?sc)\b", re.I), "Bachelors"),
    (re.compile(r"\b(?:associate'?s?|a\.?s\.?|a\.?a\.?|diploma)\b", re.I), "Associates"),
    (re.compile(r"\b(?:high\s+school|ged)\b", re.I), "High School"),
]

_JOB_TITLE_RE = re.compile(
    r"\b((?:senior|sr\.?|junior|jr\.?|lead|principal|staff|chief|head|director|manager|vp|"
    r"associate|intern|consultant)\s+)?"
    r"(software\s+(?:engineer(?:ing)?|developer|architect)|web\s+(?:developer|development\s+intern)|"
    r"java\s+(?:developer|architect)|"
    r"full[\s-]?stack\s+(?:developer|engineer)|front[\s-]?end\s+(?:developer|engineer)|"
    r"back[\s-]?end\s+(?:developer|engineer)|"
    r"data\s+(?:engineer|scientist|analyst)|devops\s+engineer|"
    r"network\s+(?:engineer|administrator)|systems?\s+administrator|"
    r"database\s+administrator|dba|business\s+analyst|project\s+manager|"
    r"scrum\s+master|product\s+manager|qa\s+(?:engineer|analyst)|"
    r"test\s+(?:engineer|analyst)|etl\s+developer|bi\s+(?:developer|analyst)|"
    r"recruiter|talent\s+acquisition|ios\s+developer|android\s+developer|"
    r"cloud\s+(?:engineer|architect)|solutions?\s+architect|"
    r"technical\s+(?:lead|architect|writer|recruiter)|ui/ux\s+designer|"
    r"security\s+(?:engineer|analyst)|machine\s+learning\s+engineer|"
    r"data\s+warehouse\s+(?:developer|architect)|"
    r"(?:software|web|it|hardware)\s+(?:engineering|development|support)\s+(?:intern|co-?op)|"
    r"website\s+(?:manager|administrator|developer)|"
    r"(?:it|help\s*desk)\s+(?:support|technician|specialist|administrator))\b",
    re.IGNORECASE,
)


# ── Core parser ─────────────────────────────────────────────────────────────


class ResumeParser:
    """Agent 1: Parses structured information from a preprocessed resume."""

    def __init__(self, skill_lookup: Optional[SkillLookup] = None) -> None:
        self.skill_lookup = skill_lookup or SkillLookup()
        self.section_weights = PARAMS.section_weights

    # ── Public ───────────────────────────────────────────────────────────

    def parse(self, preprocessed: Dict) -> Dict:
        """Parse a single preprocessed resume dict.

        Args:
            preprocessed: Output of ``preprocessing.preprocess_single``.

        Returns:
            Dict with ``skills``, ``years_experience``, ``education_level``,
            ``job_titles``, ``scored_skills``, and original metadata.
        """
        sections: Dict[str, str] = preprocessed.get("sections", {})
        raw = preprocessed.get("raw_text", "")

        # 1. Skill extraction with section-aware scoring
        scored_skills = self._extract_skills_scored(sections, raw)

        # 2. Years of experience — prefer experience/work sections to avoid
        #    counting education date ranges (e.g. "2017-2021" for a degree).
        exp_text = sections.get("experience", "") or sections.get("work", "") or ""
        years_exp = self._extract_years_experience(exp_text, raw) if exp_text else self._extract_years_experience(raw)

        # 3. Education level
        edu_level = self._extract_education_level(raw)

        # 4. Job titles
        job_titles = self._extract_job_titles(raw)

        return {
            "resume_id": preprocessed.get("resume_id", -1),
            "category": preprocessed.get("category", ""),
            "job_title": preprocessed.get("job_title", ""),
            "skills": sorted(scored_skills.keys()),
            "scored_skills": scored_skills,
            "years_experience": years_exp,
            "education_level": edu_level,
            "job_titles_mentioned": job_titles,
        }

    def parse_batch(self, preprocessed_list: List[Dict]) -> List[Dict]:
        """Parse a batch of preprocessed resumes."""
        return [self.parse(p) for p in preprocessed_list]

    # ── Private helpers ──────────────────────────────────────────────────

    def _extract_skills_scored(
        self, sections: Dict[str, str], raw_text: str
    ) -> Dict[str, float]:
        """Extract skills from each section, applying section weights.

        Score = sum over sections of (frequency_in_section * section_weight).
        """
        skill_scores: Dict[str, float] = {}

        for sec_name, sec_text in sections.items():
            weight = self.section_weights.get(sec_name, self.section_weights.get("other", 0.4))
            hits = self.skill_lookup.extract_from_text(sec_text)
            for skill, count in hits.items():
                skill_scores[skill] = skill_scores.get(skill, 0.0) + count * weight

        # If no sections were identified, fall back to raw text with default weight
        if not skill_scores:
            hits = self.skill_lookup.extract_from_text(raw_text)
            for skill, count in hits.items():
                skill_scores[skill] = count * 0.6

        return skill_scores

    @staticmethod
    def _extract_years_experience(text: str, full_text: str = "") -> Optional[int]:
        """Extract years of experience from explicit mentions or date ranges.

        Args:
            text: The text to search (ideally the experience section only).
            full_text: Full resume text used as a broader fallback for explicit mentions.
        """
        # Try explicit mentions first: "5 years of experience" — search full text too
        for t in (text, full_text):
            matches = _YEARS_EXP_RE.findall(t)
            if matches:
                return max(int(m) for m in matches)

        # Fall back to computing from date ranges using month-level precision
        import datetime
        now = datetime.datetime.now()
        total_months = 0
        for start_month_str, start_year_str, end_month_str, end_year_str in _DATE_RANGE_RE.findall(text):
            try:
                start_year = int(start_year_str)
                start_month = 1  # default to January
                if start_month_str:
                    prefix = start_month_str[:3].lower().rstrip('.')
                    start_month = _MONTH_MAP.get(prefix, 1)

                if end_year_str.lower() in ("present", "current", "now"):
                    end_year = now.year
                    end_month = now.month
                else:
                    end_year = int(end_year_str)
                    end_month = 12  # default to December
                    if end_month_str:
                        prefix = end_month_str[:3].lower().rstrip('.')
                        end_month = _MONTH_MAP.get(prefix, 12)

                months = (end_year - start_year) * 12 + (end_month - start_month)
                if 0 < months <= 480:  # sanity: up to 40 years
                    total_months += months
            except ValueError:
                continue

        if total_months > 0:
            # Round up: 3 months -> 1 year, 14 months -> 2 years
            import math
            return max(1, math.ceil(total_months / 12))
        return None

    @staticmethod
    def _extract_education_level(text: str) -> str:
        """Return the highest education level detected."""
        for pat, level in _EDUCATION_LEVELS:
            if pat.search(text):
                return level
        return "Unknown"

    @staticmethod
    def _extract_job_titles(text: str) -> List[str]:
        """Extract unique job titles from the text."""
        titles = set()
        for m in _JOB_TITLE_RE.finditer(text):
            title = m.group(0).strip()
            titles.add(title.title())
        return sorted(titles)


# ── CLI helper ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from preprocessing import load_dataset, preprocess_single
    from config import COLUMN_TEXT, COLUMN_CATEGORY, COLUMN_JOB_TITLE

    df = load_dataset()
    row = df.iloc[0]
    pre = preprocess_single(row[COLUMN_TEXT], row[COLUMN_CATEGORY], row[COLUMN_JOB_TITLE], 0)
    parser = ResumeParser()
    result = parser.parse(pre)
    print(f"Skills ({len(result['skills'])}): {result['skills'][:15]}")
    print(f"Years exp: {result['years_experience']}")
    print(f"Education: {result['education_level']}")
    print(f"Job titles: {result['job_titles_mentioned'][:5]}")
    print(f"Top scored skills:")
    for sk, sc in sorted(result["scored_skills"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {sk}: {sc:.2f}")
