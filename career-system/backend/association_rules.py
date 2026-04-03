"""
association_rules.py – Per-cluster association-rule mining.

For each cluster produced by clustering.py, applies Apriori (via mlxtend) to
discover frequent skill combinations with support, confidence, and lift.
Identifies "must-have" skill sets per role cluster.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules as ar_func
from mlxtend.preprocessing import TransactionEncoder

from config import PARAMS, RESULTS_DIR

logger = logging.getLogger(__name__)


def _build_transactions(
    resumes: List[Dict],
) -> List[List[str]]:
    """Convert normalised resumes into a list of skill-set transactions."""
    return [r.get("normalized_skills", []) for r in resumes]


def mine_rules_for_cluster(
    resumes: List[Dict],
    cluster_id: int,
    min_support: float = PARAMS.min_support,
    min_confidence: float = PARAMS.min_confidence,
    min_lift: float = PARAMS.min_lift,
    max_len: int = PARAMS.max_itemset_len,
) -> Dict[str, Any]:
    """Mine association rules for a single cluster.

    Args:
        resumes: Normalised resume dicts belonging to this cluster.
        cluster_id: Identifier for the cluster.
        min_support: Minimum support threshold.
        min_confidence: Minimum confidence threshold.
        min_lift: Minimum lift threshold.
        max_len: Maximum itemset length.

    Returns:
        Dict with ``cluster_id``, ``n_resumes``, ``frequent_itemsets``, ``rules``.
    """
    transactions = _build_transactions(resumes)

    if len(transactions) < 5:
        logger.warning(f"Cluster {cluster_id}: only {len(transactions)} resumes – skipping rules.")
        return {
            "cluster_id": cluster_id,
            "n_resumes": len(transactions),
            "frequent_itemsets": [],
            "rules": [],
        }

    te = TransactionEncoder()
    te_ary = te.fit_transform(transactions)
    df = pd.DataFrame(te_ary, columns=te.columns_)

    # Frequent itemsets
    try:
        freq = apriori(df, min_support=min_support, use_colnames=True, max_len=max_len)
    except Exception as exc:
        logger.warning(f"Cluster {cluster_id}: apriori failed – {exc}")
        return {
            "cluster_id": cluster_id,
            "n_resumes": len(transactions),
            "frequent_itemsets": [],
            "rules": [],
        }

    if freq.empty:
        return {
            "cluster_id": cluster_id,
            "n_resumes": len(transactions),
            "frequent_itemsets": [],
            "rules": [],
        }

    # Association rules – need full freq table (including singletons) to compute metrics
    try:
        has_multi = freq["itemsets"].apply(len).max() >= 2 if not freq.empty else False
        if has_multi:
            rules_df = ar_func(
                freq,
                num_itemsets=len(transactions),
                metric="confidence",
                min_threshold=min_confidence,
            )
            rules_df = rules_df[rules_df["lift"] >= min_lift]
        else:
            rules_df = pd.DataFrame()
    except Exception as exc:
        logger.warning(f"Cluster {cluster_id}: association rules failed – {exc}")
        rules_df = pd.DataFrame()

    # Serialise
    # Only keep multi-item itemsets for output (cap at 200 for storage)
    freq_sorted = freq.sort_values("support", ascending=False)
    fi_list = [
        {
            "itemset": sorted(list(row["itemsets"])),
            "support": round(float(row["support"]), 4),
        }
        for _, row in freq_sorted.head(200).iterrows()
    ]

    rules_list: List[Dict] = []
    if not rules_df.empty:
        rules_df_sorted = rules_df.sort_values("lift", ascending=False).head(300)
        for _, row in rules_df_sorted.iterrows():
            rules_list.append({
                "antecedents": sorted(list(row["antecedents"])),
                "consequents": sorted(list(row["consequents"])),
                "support": round(float(row["support"]), 4),
                "confidence": round(float(row["confidence"]), 4),
                "lift": round(float(row["lift"]), 4),
            })
        rules_list.sort(key=lambda r: -r["lift"])

    logger.info(
        f"Cluster {cluster_id}: {len(fi_list)} frequent itemsets, {len(rules_list)} rules"
    )

    return {
        "cluster_id": cluster_id,
        "n_resumes": len(transactions),
        "frequent_itemsets": fi_list[:100],  # cap for storage
        "rules": rules_list[:200],
    }


def mine_all_clusters(
    normalized_resumes: List[Dict],
    labels: np.ndarray,
    min_support: float = PARAMS.min_support,
    min_confidence: float = PARAMS.min_confidence,
) -> Dict[int, Dict]:
    """Mine rules for every cluster.

    Returns:
        Dict of cluster_id -> rule results.
    """
    n_clusters = int(labels.max()) + 1
    all_rules: Dict[int, Dict] = {}

    for c in range(n_clusters):
        idxs = np.where(labels == c)[0]
        cluster_resumes = [normalized_resumes[i] for i in idxs]
        all_rules[c] = mine_rules_for_cluster(
            cluster_resumes, c, min_support=min_support, min_confidence=min_confidence
        )

    return all_rules


def save_association_rules(rules: Dict[int, Dict]) -> Path:
    """Persist association rules to ``results/association_rules.json``."""
    path = RESULTS_DIR / "association_rules.json"
    serialisable = {str(k): v for k, v in rules.items()}
    with open(path, "w") as f:
        json.dump(serialisable, f, indent=2)
    logger.info(f"Saved association rules to {path}")
    return path


def load_association_rules() -> Dict[int, Dict]:
    """Load association rules from disk."""
    path = RESULTS_DIR / "association_rules.json"
    with open(path, "r") as f:
        data = json.load(f)
    return {int(k): v for k, v in data.items()}


# ── Helpers for downstream modules ──────────────────────────────────────────


def get_must_have_skills(rules: Dict, top_n: int = 10) -> List[str]:
    """Return the most frequently appearing skills in consequents (must-haves)."""
    from collections import Counter
    counter: Counter = Counter()
    for rule in rules.get("rules", []):
        for s in rule["consequents"]:
            counter[s] += rule["lift"]
    return [s for s, _ in counter.most_common(top_n)]


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("association_rules.py – use via pipeline.py")
