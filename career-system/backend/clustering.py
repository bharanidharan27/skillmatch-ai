"""
clustering.py – Skill-vector clustering of resumes.

Responsibilities
  - Encode normalised skill profiles as sparse vectors (frequency-weighted)
  - K-Means with elbow method for optimal *k*
  - Agglomerative (Hierarchical) clustering with dendrogram support
  - Silhouette Score evaluation
  - Output: cluster assignments, centroids, per-cluster skill profiles
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize as sk_normalize

from config import PARAMS, RESULTS_DIR

logger = logging.getLogger(__name__)


# ── Vectorisation ───────────────────────────────────────────────────────────


def build_skill_vocabulary(normalized_resumes: List[Dict]) -> List[str]:
    """Build a sorted vocabulary of all canonical skills seen across resumes."""
    vocab: set = set()
    for r in normalized_resumes:
        vocab.update(r.get("skill_scores", {}).keys())
    return sorted(vocab)


def vectorize_resumes(
    normalized_resumes: List[Dict],
    vocabulary: List[str],
) -> np.ndarray:
    """Encode each resume as a dense vector indexed by *vocabulary*.

    Values are the skill scores (frequency × section weight).
    """
    vocab_idx = {s: i for i, s in enumerate(vocabulary)}
    n = len(normalized_resumes)
    d = len(vocabulary)
    X = np.zeros((n, d), dtype=np.float32)
    for i, r in enumerate(normalized_resumes):
        for skill, score in r.get("skill_scores", {}).items():
            j = vocab_idx.get(skill)
            if j is not None:
                X[i, j] = score
    # L2 normalise so cosine ≈ dot product
    X = sk_normalize(X, norm="l2")
    return X


# ── K-Means with Elbow Method ──────────────────────────────────────────────


def elbow_method(
    X: np.ndarray,
    max_k: int = 15,
    random_state: int = 42,
) -> Tuple[List[int], List[float], List[float]]:
    """Run K-Means for k=2..max_k and return inertias + silhouette scores.

    Returns:
        (k_values, inertias, silhouettes)
    """
    ks: List[int] = list(range(2, max_k + 1))
    inertias: List[float] = []
    silhouettes: List[float] = []

    for k in ks:
        km = KMeans(n_clusters=k, random_state=random_state, n_init=10, max_iter=300)
        labels = km.fit_predict(X)
        inertias.append(float(km.inertia_))
        sil = float(silhouette_score(X, labels)) if k < len(X) else 0.0
        silhouettes.append(sil)
        logger.info(f"  k={k:2d}  inertia={km.inertia_:.1f}  silhouette={sil:.4f}")

    return ks, inertias, silhouettes


def run_kmeans(
    X: np.ndarray,
    n_clusters: int = 9,
    random_state: int = 42,
) -> Tuple[np.ndarray, np.ndarray, float]:
    """Fit K-Means and return (labels, centroids, silhouette_score)."""
    km = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10, max_iter=300)
    labels = km.fit_predict(X)
    sil = float(silhouette_score(X, labels))
    return labels, km.cluster_centers_, sil


# ── Hierarchical Clustering ────────────────────────────────────────────────


def run_hierarchical(
    X: np.ndarray,
    n_clusters: int = 9,
    linkage_method: str = "ward",
) -> Tuple[np.ndarray, float, np.ndarray]:
    """Agglomerative clustering with scipy linkage for dendrogram data.

    Returns:
        (labels, silhouette_score, linkage_matrix)
    """
    # scipy linkage for dendrogram (full linkage matrix)
    Z = linkage(X, method=linkage_method)
    labels_hier = fcluster(Z, t=n_clusters, criterion="maxclust") - 1  # 0-based

    sil = float(silhouette_score(X, labels_hier))
    return labels_hier, sil, Z


# ── Cluster profiles ───────────────────────────────────────────────────────


def cluster_skill_profiles(
    labels: np.ndarray,
    normalized_resumes: List[Dict],
    vocabulary: List[str],
    top_n: int = 20,
) -> Dict[int, Dict]:
    """For each cluster, aggregate skill frequencies and list top-N skills.

    Returns:
        Dict of cluster_id -> {size, top_skills: [(skill, freq)], category_distribution: {...}}
    """
    from collections import Counter

    n_clusters = int(labels.max()) + 1
    profiles: Dict[int, Dict] = {}

    for c in range(n_clusters):
        mask = labels == c
        idxs = np.where(mask)[0]
        cluster_resumes = [normalized_resumes[i] for i in idxs]

        # Aggregate skill counts
        skill_counter: Counter = Counter()
        cat_counter: Counter = Counter()
        for r in cluster_resumes:
            for skill, score in r.get("skill_scores", {}).items():
                skill_counter[skill] += score
            cat_counter[r.get("category", "Unknown")] += 1

        top_skills = skill_counter.most_common(top_n)
        total = len(cluster_resumes)

        profiles[c] = {
            "size": total,
            "top_skills": [(s, round(float(sc), 2)) for s, sc in top_skills],
            "category_distribution": dict(cat_counter),
        }

    return profiles


# ── Persistence ─────────────────────────────────────────────────────────────


def save_clustering_results(
    labels: np.ndarray,
    centroids: Optional[np.ndarray],
    sil_score: float,
    profiles: Dict[int, Dict],
    vocabulary: List[str],
    elbow_data: Optional[Dict] = None,
    hier_sil: Optional[float] = None,
) -> Path:
    """Save all clustering artefacts to ``results/clustering.json``."""
    out = {
        "n_clusters": int(labels.max()) + 1,
        "kmeans_silhouette": sil_score,
        "hierarchical_silhouette": hier_sil,
        "labels": labels.tolist(),
        "vocabulary_size": len(vocabulary),
        "cluster_profiles": {str(k): v for k, v in profiles.items()},
    }
    if elbow_data:
        out["elbow"] = elbow_data
    if centroids is not None:
        out["centroids"] = centroids.tolist()

    path = RESULTS_DIR / "clustering.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=2)
    logger.info(f"Saved clustering results to {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("clustering.py – use via pipeline.py")
