"""
evaluation.py – Evaluation metrics for the multi-agent pipeline.

Metrics:
  - Precision@K (K=1,3,5,10) for ranking quality
  - Kendall Tau / Spearman correlation between multi-agent and baseline rankings
  - Silhouette Score (already computed in clustering, summarised here)
  - Gap-score validation: improvement from adding top-recommended vs random skills
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.stats import kendalltau, spearmanr

from config import PARAMS, RESULTS_DIR

logger = logging.getLogger(__name__)


# ── Precision@K ─────────────────────────────────────────────────────────────


def precision_at_k(
    ranked_list: List[Dict],
    relevant_category: str,
    k: int,
) -> float:
    """Compute Precision@K: fraction of top-K results whose category matches.

    Args:
        ranked_list: Sorted list of match dicts (must have ``category`` key).
        relevant_category: The ground-truth category for the candidate.
        k: Cut-off.

    Returns:
        Precision@K as a float in [0, 1].
    """
    top_k = ranked_list[:k]
    if not top_k:
        return 0.0
    hits = sum(
        1 for item in top_k
        if _category_match(item.get("category", ""), relevant_category)
    )
    return hits / k


def _category_match(jd_category: str, resume_category: str) -> bool:
    """Fuzzy category matching between JD and resume categories."""
    from config import CATEGORY_SHORT
    short = CATEGORY_SHORT.get(resume_category, resume_category)
    return (
        short.lower() in jd_category.lower()
        or jd_category.lower() in short.lower()
        or resume_category.lower() in jd_category.lower()
        or jd_category.lower() in resume_category.lower()
    )


def compute_precision_at_k(
    agent_results: List[List[Dict]],
    candidate_categories: List[str],
    k_values: List[int] = PARAMS.precision_k_values,
) -> Dict[str, float]:
    """Compute average Precision@K across all candidates.

    Returns:
        Dict of ``"P@1"``, ``"P@3"``, etc.
    """
    metrics: Dict[str, List[float]] = {f"P@{k}": [] for k in k_values}

    for ranked, cat in zip(agent_results, candidate_categories):
        for k in k_values:
            p = precision_at_k(ranked, cat, k)
            metrics[f"P@{k}"].append(p)

    return {key: round(float(np.mean(vals)), 4) for key, vals in metrics.items()}


# ── Ranking Correlation ─────────────────────────────────────────────────────


def ranking_correlation(
    agent_results: List[List[Dict]],
    baseline_results: List[List[Dict]],
) -> Dict[str, float]:
    """Compute Kendall Tau and Spearman rank correlation between agent and baseline.

    For each candidate, build a score vector over JDs and correlate.

    Returns:
        Dict with ``kendall_tau``, ``spearman_rho``, and their p-values.
    """
    taus: List[float] = []
    rhos: List[float] = []

    for agent_r, base_r in zip(agent_results, baseline_results):
        # Build jd_id -> rank mappings
        agent_ids = [r["jd_id"] for r in agent_r]
        base_ids = [r["jd_id"] for r in base_r]

        # Common JDs
        common = set(agent_ids) & set(base_ids)
        if len(common) < 3:
            continue

        agent_rank = {jid: i for i, jid in enumerate(agent_ids) if jid in common}
        base_rank = {jid: i for i, jid in enumerate(base_ids) if jid in common}

        common_sorted = sorted(common)
        a_ranks = [agent_rank[jid] for jid in common_sorted]
        b_ranks = [base_rank[jid] for jid in common_sorted]

        tau, _ = kendalltau(a_ranks, b_ranks)
        rho, _ = spearmanr(a_ranks, b_ranks)

        if not np.isnan(tau):
            taus.append(tau)
        if not np.isnan(rho):
            rhos.append(rho)

    return {
        "kendall_tau_mean": round(float(np.mean(taus)) if taus else 0.0, 4),
        "spearman_rho_mean": round(float(np.mean(rhos)) if rhos else 0.0, 4),
        "n_compared": len(taus),
    }


# ── Gap-score validation ───────────────────────────────────────────────────


def gap_score_validation(
    gap_results: List[Dict],
    n_trials: int = 50,
    seed: int = 42,
) -> Dict[str, float]:
    """Compare coverage improvement from adding top-recommended skills vs random skills.

    For each candidate, simulate:
      A) Adding top-N recommended skills → new coverage
      B) Adding N random skills (from all possible) → new coverage
    Report average improvement for both.
    """
    rng = random.Random(seed)

    all_skills: set = set()
    for g in gap_results:
        for rec in g.get("recommendations", []):
            all_skills.add(rec["skill"])
    all_skills_list = sorted(all_skills)

    improvements_top: List[float] = []
    improvements_rand: List[float] = []

    for g in gap_results:
        baseline_coverage = g.get("coverage", 0.0)
        recs = g.get("recommendations", [])
        n_add = min(3, len(recs))  # add top-3
        if n_add == 0:
            continue

        # Top-N recommended
        top_skills = {r["skill"] for r in recs[:n_add]}
        n_total = g["n_present"] + g["n_missing"]
        new_present = g["n_present"] + len(top_skills)
        new_coverage_top = new_present / max(n_total, 1)
        improvements_top.append(new_coverage_top - baseline_coverage)

        # Random N skills
        rand_improvements = []
        for _ in range(n_trials):
            rand_skills = set(rng.sample(all_skills_list, min(n_add, len(all_skills_list))))
            missing_set = {r["skill"] for r in recs}
            rand_useful = rand_skills & missing_set
            new_present_r = g["n_present"] + len(rand_useful)
            new_coverage_r = new_present_r / max(n_total, 1)
            rand_improvements.append(new_coverage_r - baseline_coverage)
        improvements_rand.append(float(np.mean(rand_improvements)))

    return {
        "avg_improvement_top_recommended": round(float(np.mean(improvements_top)) if improvements_top else 0.0, 4),
        "avg_improvement_random": round(float(np.mean(improvements_rand)) if improvements_rand else 0.0, 4),
        "n_candidates": len(improvements_top),
    }


# ── Full evaluation ─────────────────────────────────────────────────────────


def run_evaluation(
    agent_results: List[List[Dict]],
    baseline_results: List[List[Dict]],
    candidate_categories: List[str],
    kmeans_silhouette: float,
    hierarchical_silhouette: Optional[float],
    gap_results: List[Dict],
) -> Dict[str, Any]:
    """Run all evaluation metrics and return a consolidated results dict."""

    precision = compute_precision_at_k(agent_results, candidate_categories)
    correlation = ranking_correlation(agent_results, baseline_results)
    gap_val = gap_score_validation(gap_results)

    baseline_precision = compute_precision_at_k(baseline_results, candidate_categories)

    results = {
        "multi_agent_precision": precision,
        "baseline_precision": baseline_precision,
        "ranking_correlation": correlation,
        "clustering": {
            "kmeans_silhouette": kmeans_silhouette,
            "hierarchical_silhouette": hierarchical_silhouette,
        },
        "gap_validation": gap_val,
    }

    return results


def save_evaluation(results: Dict) -> Path:
    """Persist evaluation results to JSON."""
    path = RESULTS_DIR / "evaluation.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved evaluation results to {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("evaluation.py – use via pipeline.py")
