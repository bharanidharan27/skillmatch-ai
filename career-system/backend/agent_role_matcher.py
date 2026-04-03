"""
agent_role_matcher.py – Agent 3: Role Matching.

Takes normalised skill profiles and job descriptions and computes
candidate-job alignment using IDF-weighted skill overlap, skill-score
awareness, and cluster-aware matching.

Improvements over the naïve set-overlap baseline:
  1. IDF weighting – rare/discriminative skills count more than ubiquitous ones
  2. Skill-score awareness – uses Agent 1/2 confidence scores so frequently-
     mentioned resume skills contribute more
  3. Category bonus – if the candidate's ground-truth resume category matches
     the JD category, a bonus rewards domain alignment
  4. Cluster affinity bonus – if the candidate's cluster matches the JD's
     dominant cluster, another small bonus is applied
"""

from __future__ import annotations

import json
import logging
import math
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from config import PARAMS, RESULTS_DIR

logger = logging.getLogger(__name__)


class RoleMatcher:
    """Agent 3: Matches candidates to job descriptions.

    Scoring (per candidate–JD pair)
    --------------------------------
    For each skill s in the JD's required/preferred set:
      idf(s) = log(N / (1 + df(s)))          # N = number of training resumes
      w(s)   = idf(s) * skill_score(s)       # 0 if candidate lacks the skill

    required_score  = Σ w(s) for s in required  / Σ idf(s) for s in required
    preferred_score = Σ w(s) for s in preferred / Σ idf(s) for s in preferred
    base_score      = 0.70 * required_score + 0.30 * preferred_score

    Bonuses:
      +0.08 category_bonus   (resume category matches JD category)
      +0.05 cluster_bonus    (resume cluster matches JD's dominant cluster)
    """

    def __init__(
        self,
        job_descriptions: Optional[List[Dict]] = None,
        cluster_profiles: Optional[Dict] = None,
        labels: Optional[np.ndarray] = None,
        training_resumes: Optional[List[Dict]] = None,
    ) -> None:
        self.job_descriptions = job_descriptions or []
        self.cluster_profiles = cluster_profiles  # cluster_id -> profile dict
        self.labels = labels  # cluster label per training resume (may be None)

        # Build IDF from training resumes
        self._idf: Dict[str, float] = {}
        if training_resumes:
            self._build_idf(training_resumes)

        # Pre-compute JD cluster mapping if profiles available
        self._jd_cluster_map: Dict[str, int] = {}
        if self.cluster_profiles:
            self._map_jd_to_clusters()

    # ── Public ───────────────────────────────────────────────────────────

    def match(
        self,
        candidate: Dict,
        top_k: int = PARAMS.top_k_matches,
    ) -> List[Dict]:
        """Rank all job descriptions for a single candidate."""
        cand_skills = set(candidate.get("normalized_skills", []))
        cand_scores = candidate.get("skill_scores", {})
        cand_category = candidate.get("category", "")
        results: List[Dict] = []

        for jd in self.job_descriptions:
            req = set(jd.get("required_skills", []))
            pref = set(jd.get("preferred_skills", []))

            req_match = cand_skills & req
            pref_match = cand_skills & pref

            # IDF-weighted scoring
            req_score = self._idf_weighted_score(req_match, req, cand_scores)
            pref_score = self._idf_weighted_score(pref_match, pref, cand_scores)

            score = 0.70 * req_score + 0.30 * pref_score

            # Category bonus: resume category matches JD category
            jd_cat = jd.get("category", "")
            if cand_category and jd_cat:
                from config import CATEGORY_SHORT
                short = CATEGORY_SHORT.get(cand_category, cand_category)
                if (
                    short.lower() in jd_cat.lower()
                    or jd_cat.lower() in short.lower()
                    or cand_category.lower() in jd_cat.lower()
                    or jd_cat.lower() in cand_category.lower()
                ):
                    score += 0.08

            # Cluster bonus
            jd_cluster = self._jd_cluster_map.get(jd["id"])
            if jd_cluster is not None and self.labels is not None:
                rid = candidate.get("resume_id", -1)
                if 0 <= rid < len(self.labels) and self.labels[rid] == jd_cluster:
                    score += 0.05

            results.append({
                "jd_id": jd["id"],
                "title": jd["title"],
                "company": jd.get("company", ""),
                "category": jd.get("category", ""),
                "score": round(score, 4),
                "matched_required": sorted(req_match),
                "matched_preferred": sorted(pref_match),
                "missing_required": sorted(req - cand_skills),
            })

        results.sort(key=lambda r: -r["score"])
        return results[:top_k]

    def match_batch(
        self,
        candidates: List[Dict],
        top_k: int = PARAMS.top_k_matches,
    ) -> List[List[Dict]]:
        """Match a batch of candidates."""
        return [self.match(c, top_k) for c in candidates]

    # ── Private ──────────────────────────────────────────────────────────

    def _build_idf(self, resumes: List[Dict]) -> None:
        """Build IDF weights from the training corpus."""
        n = len(resumes)
        df: Counter = Counter()
        for r in resumes:
            unique_skills = set(r.get("normalized_skills", []))
            for s in unique_skills:
                df[s] += 1

        self._idf = {s: math.log(n / (1 + count)) for s, count in df.items()}
        logger.info(f"Built IDF index over {n} resumes, {len(self._idf)} skills")

    def _idf_weighted_score(
        self,
        matched: set,
        jd_skills: set,
        cand_scores: Dict[str, float],
    ) -> float:
        """Compute IDF-weighted overlap score.

        Numerator   = Σ idf(s) * score_factor(s) for matched skills
        Denominator = Σ idf(s) for all JD skills
        Falls back to simple fraction when IDF is unavailable.
        """
        if not jd_skills:
            return 0.0

        if not self._idf:
            # Fallback to simple set overlap
            return len(matched) / len(jd_skills)

        default_idf = math.log(max(len(self._idf), 2))  # for unseen skills
        denominator = sum(self._idf.get(s, default_idf) for s in jd_skills)
        if denominator == 0:
            return 0.0

        numerator = 0.0
        for s in matched:
            idf = self._idf.get(s, default_idf)
            # Use skill score (capped to avoid outlier domination)
            ss = min(cand_scores.get(s, 1.0), 3.0)
            # Normalise skill score: treat 1.0 as baseline, range [0.5, 1.5]
            score_factor = 0.5 + 0.5 * min(ss, 2.0)
            numerator += idf * score_factor

        return numerator / denominator

    def _map_jd_to_clusters(self) -> None:
        """Map each JD to the cluster whose dominant category matches."""
        if not self.cluster_profiles:
            return
        # Build cluster -> dominant category
        cluster_cat: Dict[int, str] = {}
        for cid, prof in self.cluster_profiles.items():
            cid = int(cid)
            cat_dist = prof.get("category_distribution", {})
            if cat_dist:
                cluster_cat[cid] = max(cat_dist, key=cat_dist.get)

        # Reverse: category -> cluster_id
        cat_to_cluster = {v: k for k, v in cluster_cat.items()}

        for jd in self.job_descriptions:
            jd_cat = jd.get("category", "")
            # Try exact match first, then partial
            if jd_cat in cat_to_cluster:
                self._jd_cluster_map[jd["id"]] = cat_to_cluster[jd_cat]
            else:
                for cat, cid in cat_to_cluster.items():
                    if jd_cat.lower() in cat.lower() or cat.lower() in jd_cat.lower():
                        self._jd_cluster_map[jd["id"]] = cid
                        break


def save_matching_results(results: List[Dict]) -> Path:
    """Save matching results to disk."""
    path = RESULTS_DIR / "matching_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved matching results ({len(results)} candidates) to {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("agent_role_matcher.py – use via pipeline.py")
