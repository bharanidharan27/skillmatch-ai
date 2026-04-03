"""
pipeline.py – Main orchestration script for the Intelligent Multi-Agent Career Page System.

Runs the entire pipeline end-to-end:
  1.  Load and preprocess data
  2.  Run Agent 1 (Resume Parser) on all resumes
  3.  Run Agent 2 (Skill Normaliser)
  4.  Split into train/test (70/30)
  5.  Run clustering on the training set
  6.  Run association-rule mining per cluster
  7.  Generate / load job descriptions
  8.  Run Agent 3 (Role Matcher) on the test set
  9.  Compute gap scores
  10. Run baseline (TF-IDF)
  11. Run evaluation
  12. Save all results to results/

Usage:
    python pipeline.py
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import numpy as np

# Ensure the backend directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (
    COLUMN_CATEGORY,
    COLUMN_JOB_TITLE,
    COLUMN_TEXT,
    PARAMS,
    RESULTS_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


def main() -> None:
    t0 = time.time()

    # ── 1. Load & preprocess ────────────────────────────────────────────
    logger.info("Step 1/12: Loading dataset …")
    from preprocessing import load_dataset, preprocess_dataset

    df = load_dataset()
    logger.info(f"  Loaded {len(df)} resumes across {df[COLUMN_CATEGORY].nunique()} categories")

    logger.info("Step 1/12: Preprocessing resumes …")
    preprocessed = preprocess_dataset(df)
    logger.info(f"  Preprocessed {len(preprocessed)} resumes")

    # ── 2. Agent 1: Resume Parser ───────────────────────────────────────
    logger.info("Step 2/12: Running Agent 1 (Resume Parser) …")
    from agent_resume_parser import ResumeParser
    from skill_dictionary import SkillLookup, save_dictionary

    save_dictionary()  # ensure JSON on disk
    skill_lookup = SkillLookup()
    parser = ResumeParser(skill_lookup)

    parsed_resumes = parser.parse_batch(preprocessed)
    avg_skills = np.mean([len(p["skills"]) for p in parsed_resumes])
    logger.info(f"  Parsed {len(parsed_resumes)} resumes (avg {avg_skills:.1f} skills/resume)")

    # ── 3. Agent 2: Skill Normaliser ────────────────────────────────────
    logger.info("Step 3/12: Running Agent 2 (Skill Normaliser) …")
    from agent_skill_normalizer import SkillNormalizer

    normalizer = SkillNormalizer(skill_lookup)
    normalized = normalizer.normalize_batch(parsed_resumes)
    logger.info(f"  Normalised {len(normalized)} resumes")

    # ── 4. Train / Test split ───────────────────────────────────────────
    logger.info("Step 4/12: Splitting train/test …")
    from sklearn.model_selection import train_test_split

    indices = list(range(len(normalized)))
    categories = [n["category"] for n in normalized]

    train_idx, test_idx = train_test_split(
        indices,
        test_size=PARAMS.test_ratio,
        random_state=PARAMS.random_state,
        stratify=categories,
    )

    train_data = [normalized[i] for i in train_idx]
    test_data = [normalized[i] for i in test_idx]
    logger.info(f"  Train: {len(train_data)}, Test: {len(test_data)}")

    # ── 5. Clustering ───────────────────────────────────────────────────
    logger.info("Step 5/12: Clustering (training set) …")
    from clustering import (
        build_skill_vocabulary,
        vectorize_resumes,
        elbow_method,
        run_kmeans,
        run_hierarchical,
        cluster_skill_profiles,
        save_clustering_results,
    )

    vocab = build_skill_vocabulary(train_data)
    logger.info(f"  Vocabulary: {len(vocab)} unique skills")

    X_train = vectorize_resumes(train_data, vocab)
    logger.info(f"  Feature matrix: {X_train.shape}")

    logger.info("  Running elbow method …")
    ks, inertias, sils = elbow_method(X_train, max_k=PARAMS.max_k_search, random_state=PARAMS.random_state)
    elbow_data = {"k_values": ks, "inertias": inertias, "silhouettes": sils}

    logger.info(f"  Running K-Means (k={PARAMS.num_clusters}) …")
    km_labels, centroids, km_sil = run_kmeans(X_train, PARAMS.num_clusters, PARAMS.random_state)
    logger.info(f"  K-Means silhouette: {km_sil:.4f}")

    logger.info("  Running Hierarchical clustering …")
    hier_labels, hier_sil, linkage_matrix = run_hierarchical(
        X_train, PARAMS.num_clusters, PARAMS.linkage_method
    )
    logger.info(f"  Hierarchical silhouette: {hier_sil:.4f}")

    # Use K-Means labels as primary
    profiles = cluster_skill_profiles(km_labels, train_data, vocab)
    save_clustering_results(km_labels, centroids, km_sil, profiles, vocab, elbow_data, hier_sil)

    # ── 6. Association Rules ────────────────────────────────────────────
    logger.info("Step 6/12: Mining association rules per cluster …")
    from association_rules import mine_all_clusters, save_association_rules

    rules_per_cluster = mine_all_clusters(
        train_data, km_labels,
        min_support=PARAMS.min_support,
        min_confidence=PARAMS.min_confidence,
    )
    save_association_rules(rules_per_cluster)
    total_rules = sum(len(v.get("rules", [])) for v in rules_per_cluster.values())
    logger.info(f"  Total rules mined: {total_rules}")

    # ── 7. Job Descriptions ─────────────────────────────────────────────
    logger.info("Step 7/12: Loading/generating job descriptions …")
    from job_descriptions import load_job_descriptions, save_job_descriptions

    save_job_descriptions()
    jds = load_job_descriptions()
    logger.info(f"  {len(jds)} job descriptions")

    # ── 8. Agent 3: Role Matcher ────────────────────────────────────────
    logger.info("Step 8/12: Running Agent 3 (Role Matcher) on test set …")
    from agent_role_matcher import RoleMatcher, save_matching_results

    matcher = RoleMatcher(
        job_descriptions=jds,
        cluster_profiles={str(k): v for k, v in profiles.items()},
        labels=km_labels,
        training_resumes=train_data,
    )

    agent_results = matcher.match_batch(test_data, top_k=PARAMS.top_k_matches)
    save_matching_results([
        {"resume_id": test_data[i]["resume_id"], "category": test_data[i]["category"], "matches": agent_results[i]}
        for i in range(len(test_data))
    ])
    logger.info(f"  Matched {len(test_data)} candidates")

    # ── 9. Gap Scores ───────────────────────────────────────────────────
    logger.info("Step 9/12: Computing gap scores …")
    from gap_scoring import compute_gaps_batch, save_gap_results

    gap_results = compute_gaps_batch(
        test_data, jds, km_labels, train_data, rules_per_cluster, profiles
    )
    save_gap_results(gap_results)
    avg_gap = np.mean([g["gap_score"] for g in gap_results])
    logger.info(f"  Average gap score: {avg_gap:.4f}")

    # ── 10. Baseline (TF-IDF) ──────────────────────────────────────────
    logger.info("Step 10/12: Running TF-IDF baseline …")
    from baseline import TFIDFBaseline, save_baseline_results

    baseline = TFIDFBaseline()
    baseline.fit_jds(jds)
    test_texts = [preprocessed[i]["raw_text"] for i in test_idx]
    baseline_results = baseline.rank_candidates(test_texts, top_k=PARAMS.top_k_matches)
    save_baseline_results(baseline_results)
    logger.info(f"  Baseline ranked {len(baseline_results)} candidates")

    # ── 11. Evaluation ──────────────────────────────────────────────────
    logger.info("Step 11/12: Running evaluation …")
    from evaluation import run_evaluation, save_evaluation

    test_categories = [d["category"] for d in test_data]
    eval_results = run_evaluation(
        agent_results=agent_results,
        baseline_results=baseline_results,
        candidate_categories=test_categories,
        kmeans_silhouette=km_sil,
        hierarchical_silhouette=hier_sil,
        gap_results=gap_results,
    )
    save_evaluation(eval_results)
    logger.info(f"  Evaluation complete")
    for key, val in eval_results.items():
        logger.info(f"    {key}: {val}")

    # ── 12. Save summary ────────────────────────────────────────────────
    logger.info("Step 12/12: Saving pipeline summary …")
    elapsed = time.time() - t0
    summary = {
        "total_resumes": len(df),
        "train_size": len(train_data),
        "test_size": len(test_data),
        "vocabulary_size": len(vocab),
        "n_clusters": PARAMS.num_clusters,
        "kmeans_silhouette": km_sil,
        "hierarchical_silhouette": hier_sil,
        "total_association_rules": total_rules,
        "n_job_descriptions": len(jds),
        "avg_gap_score": round(avg_gap, 4),
        "evaluation": eval_results,
        "elapsed_seconds": round(elapsed, 1),
    }
    summary_path = RESULTS_DIR / "pipeline_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Pipeline complete in {elapsed:.1f}s.  Results in {RESULTS_DIR}")


if __name__ == "__main__":
    main()
