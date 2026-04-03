"""
gap_scoring.py – Weighted Skill Gap Score computation.

For each candidate–role pair:
  1. Identify missing skills (required by the JD but absent from the resume).
  2. Weight each missing skill by:
       cluster_frequency  (how common the skill is in the cluster)
     × association_rule_lift (average lift of rules involving the skill)
  3. Gap Severity Score = Σ weighted missing skill scores
  4. Generate prioritised upskilling recommendations sorted by gap severity.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import PARAMS, RESULTS_DIR

logger = logging.getLogger(__name__)


# ── Build helper indices ────────────────────────────────────────────────────


def _skill_cluster_frequency(
    normalized_resumes: List[Dict],
    labels: np.ndarray,
) -> Dict[int, Dict[str, float]]:
    """Compute per-cluster skill frequency (fraction of resumes that contain each skill).

    Returns:
        Dict[cluster_id -> Dict[skill -> frequency_0_to_1]]
    """
    n_clusters = int(labels.max()) + 1
    cluster_counts: Dict[int, Dict[str, int]] = {c: defaultdict(int) for c in range(n_clusters)}
    cluster_sizes: Dict[int, int] = defaultdict(int)

    for i, r in enumerate(normalized_resumes):
        c = int(labels[i])
        cluster_sizes[c] += 1
        for skill in r.get("normalized_skills", []):
            cluster_counts[c][skill] += 1

    freq: Dict[int, Dict[str, float]] = {}
    for c in range(n_clusters):
        sz = max(cluster_sizes[c], 1)
        freq[c] = {sk: cnt / sz for sk, cnt in cluster_counts[c].items()}

    return freq


def _skill_lift_index(
    rules_per_cluster: Dict[int, Dict],
) -> Dict[int, Dict[str, float]]:
    """For each cluster, compute the average lift involving each skill.

    Returns:
        Dict[cluster_id -> Dict[skill -> avg_lift]]
    """
    lift_index: Dict[int, Dict[str, float]] = {}

    for cid, data in rules_per_cluster.items():
        cid = int(cid)
        skill_lifts: Dict[str, List[float]] = defaultdict(list)
        for rule in data.get("rules", []):
            lift = rule.get("lift", 1.0)
            for s in rule.get("antecedents", []) + rule.get("consequents", []):
                skill_lifts[s].append(lift)

        lift_index[cid] = {
            s: sum(ls) / len(ls) for s, ls in skill_lifts.items()
        }

    return lift_index


# ── Gap scoring ─────────────────────────────────────────────────────────────


def compute_gap(
    candidate: Dict,
    jd: Dict,
    cluster_id: int,
    cluster_freq: Dict[str, float],
    lift_idx: Dict[str, float],
) -> Dict[str, Any]:
    """Compute the skill gap for one (candidate, JD) pair.

    Returns:
        Dict with ``gap_score``, ``missing_skills``, ``recommendations``.
    """
    cand_skills = set(candidate.get("normalized_skills", []))
    req_skills = set(jd.get("required_skills", []))
    pref_skills = set(jd.get("preferred_skills", []))
    all_jd_skills = req_skills | pref_skills

    missing = all_jd_skills - cand_skills
    present = all_jd_skills & cand_skills

    # Weight each missing skill
    weighted_missing: List[Tuple[str, float]] = []
    for skill in missing:
        freq_w = cluster_freq.get(skill, 0.01)   # default low if unseen
        lift_w = lift_idx.get(skill, 1.0)
        is_required = 3.0 if skill in req_skills else 1.0
        weight = freq_w * lift_w * is_required
        weighted_missing.append((skill, round(weight, 4)))

    weighted_missing.sort(key=lambda x: -x[1])

    gap_score = sum(w for _, w in weighted_missing)

    recommendations = [
        {
            "skill": skill,
            "priority_score": weight,
            "is_required": skill in req_skills,
            "cluster_frequency": round(cluster_freq.get(skill, 0.0), 4),
        }
        for skill, weight in weighted_missing
    ]

    return {
        "resume_id": candidate.get("resume_id", -1),
        "jd_id": jd.get("id", ""),
        "jd_title": jd.get("title", ""),
        "cluster_id": cluster_id,
        "gap_score": round(gap_score, 4),
        "n_missing": len(missing),
        "n_present": len(present),
        "coverage": round(len(present) / max(len(all_jd_skills), 1), 4),
        "recommendations": recommendations,
    }


def compute_gaps_batch(
    candidates: List[Dict],
    jds: List[Dict],
    labels: np.ndarray,
    normalized_train: List[Dict],
    rules_per_cluster: Dict[int, Dict],
    cluster_profiles: Dict[int, Dict],
) -> List[Dict]:
    """Compute gap scores for all test candidates against their best-matching JD.

    For each candidate, we pick the JD whose category best matches the
    candidate's ground-truth category, then compute the gap.

    Returns:
        List of gap result dicts.
    """
    # Pre-compute indices
    freq_index = _skill_cluster_frequency(normalized_train, labels)
    lift_index = _skill_lift_index(rules_per_cluster)

    # Map JD category -> list of JDs
    cat_jds: Dict[str, List[Dict]] = defaultdict(list)
    for jd in jds:
        cat_jds[jd.get("category", "")].append(jd)

    # Map resume category -> JD category (fuzzy)
    from config import CATEGORY_SHORT
    cat_map: Dict[str, str] = {}
    for long_cat, short_cat in CATEGORY_SHORT.items():
        for jd_cat in cat_jds:
            if short_cat.lower() in jd_cat.lower() or jd_cat.lower() in short_cat.lower():
                cat_map[long_cat] = jd_cat
                break

    # Assign each candidate to a cluster (use the closest cluster centroid concept:
    # we'll just pick the most common cluster for their category from training)
    cat_cluster: Dict[str, int] = {}
    if cluster_profiles:
        for cid_str, prof in cluster_profiles.items():
            cid = int(cid_str)
            cat_dist = prof.get("category_distribution", {})
            if cat_dist:
                dom_cat = max(cat_dist, key=cat_dist.get)
                if dom_cat not in cat_cluster:
                    cat_cluster[dom_cat] = cid

    results: List[Dict] = []
    for cand in candidates:
        cand_cat = cand.get("category", "")
        jd_cat = cat_map.get(cand_cat, "")
        target_jds = cat_jds.get(jd_cat, jds[:1])  # fallback to first JD
        jd = target_jds[0]  # pick first matching JD

        cid = cat_cluster.get(cand_cat, 0)
        cf = freq_index.get(cid, {})
        li = lift_index.get(cid, {})

        gap = compute_gap(cand, jd, cid, cf, li)
        results.append(gap)

    return results


def save_gap_results(results: List[Dict]) -> Path:
    """Persist gap analysis results."""
    path = RESULTS_DIR / "gap_scores.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved {len(results)} gap results to {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("gap_scoring.py – use via pipeline.py")
