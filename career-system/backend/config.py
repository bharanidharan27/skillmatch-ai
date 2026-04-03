"""
config.py – Central configuration for the Intelligent Multi-Agent Career Page System.

All paths, hyperparameters, and constants are defined here so every other module
can import them from a single source of truth.
"""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List

# ── Paths ────────────────────────────────────────────────────────────────────

BASE_DIR: Path = Path(__file__).resolve().parent
PROJECT_DIR: Path = BASE_DIR.parent
DATASET_PATH: Path = PROJECT_DIR / "resume_dataset.csv"
SKILLS_DICT_PATH: Path = BASE_DIR / "skills_dictionary.json"
JOB_DESC_PATH: Path = BASE_DIR / "job_descriptions.json"
RESULTS_DIR: Path = BASE_DIR / "results"

# Ensure results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Dataset columns ─────────────────────────────────────────────────────────

COLUMN_CATEGORY: str = "category"
COLUMN_JOB_TITLE: str = "job_title"
COLUMN_TEXT: str = "Text"

# ── Category labels (ground-truth) ──────────────────────────────────────────

CATEGORIES: List[str] = [
    "Java Developers/Architects Resumes",
    "Web Developer Resumes",
    "SQL Developers Resumes",
    "Business Analyst (BA) Resumes",
    "Network and Systems Administrators Resumes",
    "Datawarehousing, ETL, Informatica Resumes",
    "Business Intelligence, Business Object Resumes",
    "Project Manager Resumes",
    "Recruiter Resumes",
]

# Short labels for display / job-description mapping
CATEGORY_SHORT: Dict[str, str] = {
    "Java Developers/Architects Resumes": "Java Developer",
    "Web Developer Resumes": "Web Developer",
    "SQL Developers Resumes": "SQL Developer",
    "Business Analyst (BA) Resumes": "Business Analyst",
    "Network and Systems Administrators Resumes": "Network/Systems Admin",
    "Datawarehousing, ETL, Informatica Resumes": "ETL Developer",
    "Business Intelligence, Business Object Resumes": "BI Developer",
    "Project Manager Resumes": "Project Manager",
    "Recruiter Resumes": "Recruiter",
}

# ── Hyperparameters ─────────────────────────────────────────────────────────


@dataclass
class HyperParams:
    """Central store for all tuneable hyperparameters."""

    # Train / test split
    train_ratio: float = 0.70
    test_ratio: float = 0.30
    random_state: int = 42

    # Clustering
    num_clusters: int = 9          # matches 9 categories
    max_k_search: int = 15         # elbow-method upper bound
    linkage_method: str = "ward"   # for agglomerative clustering

    # Association-rule mining
    min_support: float = 0.15
    min_confidence: float = 0.50
    min_lift: float = 1.2
    max_itemset_len: int = 3

    # Skill scoring weights (by resume section)
    section_weights: Dict[str, float] = field(default_factory=lambda: {
        "skills": 1.0,
        "experience": 0.8,
        "projects": 0.7,
        "education": 0.5,
        "other": 0.4,
    })

    # Role-matching parameters
    top_k_matches: int = 10        # return top-K matching roles

    # Evaluation
    precision_k_values: List[int] = field(default_factory=lambda: [1, 3, 5, 10])

    # TF-IDF baseline
    tfidf_max_features: int = 5000

    # Processing
    batch_size: int = 500          # batch size for vectorised processing


PARAMS = HyperParams()
