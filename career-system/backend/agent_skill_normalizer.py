"""
agent_skill_normalizer.py – Agent 2: Skill Normaliser.

Takes parsed resume output from Agent 1 and:
  1. Normalises all skills to canonical names via the skill dictionary
  2. Deduplicates (aggregating scores for aliases that map to the same canonical)
  3. Attaches category metadata to each skill
"""

from __future__ import annotations

from typing import Dict, List, Optional

from skill_dictionary import SkillLookup, load_dictionary


class SkillNormalizer:
    """Agent 2: Normalises and deduplicates skills from parsed resumes."""

    def __init__(self, skill_lookup: Optional[SkillLookup] = None) -> None:
        self.skill_lookup = skill_lookup or SkillLookup()

    def normalize(self, parsed_resume: Dict) -> Dict:
        """Normalise a single parsed resume.

        Args:
            parsed_resume: Output of ``ResumeParser.parse()``.

        Returns:
            Dict with:
              - ``normalized_skills``: list of canonical skill names
              - ``skill_scores``: canonical_name -> aggregated score
              - ``skill_categories``: canonical_name -> category string
              plus original metadata fields.
        """
        raw_scores: Dict[str, float] = parsed_resume.get("scored_skills", {})

        canonical_scores: Dict[str, float] = {}
        canonical_cats: Dict[str, str] = {}

        for skill_name, score in raw_scores.items():
            canonical = self.skill_lookup.resolve(skill_name)
            if canonical is None:
                canonical = skill_name  # keep as-is if not in dictionary
            canonical_scores[canonical] = canonical_scores.get(canonical, 0.0) + score
            if canonical not in canonical_cats:
                cat = self.skill_lookup.get_category(canonical)
                canonical_cats[canonical] = cat or "Unknown"

        return {
            "resume_id": parsed_resume.get("resume_id", -1),
            "category": parsed_resume.get("category", ""),
            "job_title": parsed_resume.get("job_title", ""),
            "years_experience": parsed_resume.get("years_experience"),
            "education_level": parsed_resume.get("education_level", "Unknown"),
            "job_titles_mentioned": parsed_resume.get("job_titles_mentioned", []),
            "projects": parsed_resume.get("projects", []),
            "normalized_skills": sorted(canonical_scores.keys()),
            "skill_scores": canonical_scores,
            "skill_categories": canonical_cats,
        }

    def normalize_batch(self, parsed_resumes: List[Dict]) -> List[Dict]:
        """Normalise a list of parsed resumes."""
        return [self.normalize(p) for p in parsed_resumes]


# ── CLI helper ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from preprocessing import load_dataset, preprocess_single
    from agent_resume_parser import ResumeParser
    from config import COLUMN_TEXT, COLUMN_CATEGORY, COLUMN_JOB_TITLE

    df = load_dataset()
    row = df.iloc[0]
    pre = preprocess_single(row[COLUMN_TEXT], row[COLUMN_CATEGORY], row[COLUMN_JOB_TITLE], 0)

    parser = ResumeParser()
    parsed = parser.parse(pre)
    normalizer = SkillNormalizer()
    normed = normalizer.normalize(parsed)

    print(f"Normalized skills ({len(normed['normalized_skills'])}):")
    for sk in sorted(normed["skill_scores"], key=lambda s: -normed["skill_scores"][s])[:15]:
        print(f"  {sk:25s} score={normed['skill_scores'][sk]:.2f}  cat={normed['skill_categories'].get(sk, '?')}")
