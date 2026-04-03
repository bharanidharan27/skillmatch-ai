"""
preprocessing.py – Load, normalise, and segment the resume dataset.

Responsibilities
  - Load CSV with pandas
  - Normalise text (UTF-8, whitespace, lowercase for matching)
  - Section segmentation via regex (Experience, Education, Skills, Projects, etc.)
  - Bullet-point extraction for each section
  - Output: list of structured dicts (one per resume)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config import COLUMN_CATEGORY, COLUMN_JOB_TITLE, COLUMN_TEXT, DATASET_PATH

# ── Section header patterns ─────────────────────────────────────────────────

# Order matters: more specific patterns first
_SECTION_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("experience", re.compile(
        r"(?i)\b(professional\s+experience|work\s+experience|experience|employment\s+history|career\s+history|"
        r"relevant\s+experience)\b"
    )),
    ("education", re.compile(
        r"(?i)\b(education|academic\s+background|educational\s+qualifications|academic\s+qualifications|"
        r"degrees?|certifications?\s+(?:and|&)\s+education)\b"
    )),
    ("skills", re.compile(
        r"(?i)\b(technical\s+skills|skills|core\s+competencies|competencies|technologies|"
        r"areas?\s+of\s+expertise|technical\s+proficiency|technical\s+summary|skill\s+set|"
        r"tools?\s+(?:and|&)\s+technologies)\b"
    )),
    ("projects", re.compile(
        r"(?i)\b(projects?|key\s+projects|selected\s+projects|academic\s+projects?|"
        r"personal\s+projects?)\b"
    )),
    ("certifications", re.compile(
        r"(?i)\b(certifications?|licenses?\s+(?:and|&)\s+certifications?|professional\s+certifications?)\b"
    )),
    ("summary", re.compile(
        r"(?i)\b(professional\s+summary|summary|objective|profile|career\s+objective|professional\s+profile|about\s+me)\b"
    )),
]

# Bullet / list-item splitter
_BULLET_RE = re.compile(r"(?:^|\n)\s*(?:[-•●▪◦*]|\d+[.)]\s|[a-zA-Z][.)]\s)")


# ── Public API ──────────────────────────────────────────────────────────────


def load_dataset(path: Optional[str] = None) -> pd.DataFrame:
    """Load the resume CSV into a DataFrame.

    Args:
        path: Optional override for the CSV path.

    Returns:
        DataFrame with columns ``category``, ``job_title``, ``Text``.
    """
    path = path or str(DATASET_PATH)
    df = pd.read_csv(path, encoding="utf-8")
    # Drop any fully-empty rows
    df.dropna(subset=[COLUMN_TEXT], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def normalize_text(text: str) -> str:
    """Normalise raw resume text.

    Steps:
      1. Unicode NFC normalisation
      2. Replace non-breaking spaces and fancy whitespace
      3. Collapse multiple spaces / newlines
      4. Strip leading / trailing whitespace
    """
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\xa0\u200b\u200c\u200d\ufeff]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def segment_sections(text: str) -> Dict[str, str]:
    """Split resume text into named sections.

    Returns:
        Dict mapping section names (e.g. ``"skills"``, ``"experience"``) to
        their text content.  An ``"other"`` key captures anything before the
        first recognised header.
    """
    # Collect (position, section_name) for every header match.
    # Only accept matches that look like actual section headers:
    #   - At the very start of the text, OR
    #   - At the start of a line (preceded by newline), OR
    #   - Preceded only by whitespace on the line.
    # This prevents mid-sentence words like "...hands on experience in..."
    # from creating false section boundaries.
    markers: List[Tuple[int, str]] = []
    for name, pat in _SECTION_PATTERNS:
        for m in pat.finditer(text):
            start = m.start()
            # Check what precedes the match on the same line
            line_start = text.rfind("\n", 0, start)
            prefix = text[line_start + 1 : start] if line_start >= 0 else text[:start]
            # Accept only if the match is at line start (possibly with whitespace/bullets)
            if re.match(r'^[\s\-•●▪◦*]*$', prefix):
                markers.append((start, name))

    if not markers:
        return {"other": text}

    markers.sort(key=lambda x: x[0])

    sections: Dict[str, str] = {}
    # Text before the first header
    if markers[0][0] > 0:
        sections["other"] = text[: markers[0][0]].strip()

    for i, (pos, name) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        chunk = text[pos:end].strip()
        # Remove the header line itself
        chunk = re.sub(r"^.*?\n", "", chunk, count=1).strip()
        if name in sections:
            sections[name] += "\n" + chunk
        else:
            sections[name] = chunk

    return sections


def extract_bullets(text: str) -> List[str]:
    """Extract individual bullet / list items from a block of text."""
    parts = _BULLET_RE.split(text)
    bullets = [p.strip() for p in parts if p and p.strip()]
    # If no bullets found, split on sentence-like boundaries
    if len(bullets) <= 1:
        bullets = [s.strip() for s in re.split(r"[.;]\s+", text) if s.strip()]
    return bullets


def preprocess_single(
    text: str,
    category: str = "",
    job_title: str = "",
    resume_id: int = -1,
) -> Dict:
    """Full preprocessing pipeline for one resume.

    Returns a structured dict with:
      - ``resume_id``, ``category``, ``job_title``
      - ``raw_text`` (normalised)
      - ``sections``: dict of section_name -> text
      - ``bullets``: dict of section_name -> list of bullet strings
    """
    norm = normalize_text(text)
    sections = segment_sections(norm)
    bullets = {sec: extract_bullets(content) for sec, content in sections.items()}

    return {
        "resume_id": resume_id,
        "category": category,
        "job_title": job_title,
        "raw_text": norm,
        "sections": sections,
        "bullets": bullets,
    }


def preprocess_dataset(df: pd.DataFrame) -> List[Dict]:
    """Run preprocessing on the entire DataFrame.

    Args:
        df: DataFrame with ``category``, ``job_title``, ``Text`` columns.

    Returns:
        List of structured resume dicts.
    """
    results: List[Dict] = []
    for idx, row in df.iterrows():
        results.append(
            preprocess_single(
                text=str(row[COLUMN_TEXT]),
                category=str(row[COLUMN_CATEGORY]),
                job_title=str(row[COLUMN_JOB_TITLE]),
                resume_id=int(idx),
            )
        )
    return results


# ── CLI helper ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    df = load_dataset()
    print(f"Loaded {len(df)} resumes")
    sample = preprocess_single(df.iloc[0][COLUMN_TEXT], df.iloc[0][COLUMN_CATEGORY], df.iloc[0][COLUMN_JOB_TITLE], 0)
    print(f"Sections found: {list(sample['sections'].keys())}")
    for sec, buls in sample["bullets"].items():
        print(f"  {sec}: {len(buls)} bullets")
