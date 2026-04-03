"""
baseline.py – TF-IDF + cosine similarity baseline for resume–job matching.

Provides a simple but effective baseline to compare the multi-agent pipeline
against.  Uses raw resume text and JD description text.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config import PARAMS, RESULTS_DIR

logger = logging.getLogger(__name__)


class TFIDFBaseline:
    """TF-IDF + cosine similarity baseline matcher."""

    def __init__(self, max_features: int = PARAMS.tfidf_max_features) -> None:
        self.vectorizer = TfidfVectorizer(
            max_features=max_features,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self._jd_matrix = None
        self._jd_ids: List[str] = []
        self._jd_titles: List[str] = []
        self._jd_categories: List[str] = []

    def fit_jds(self, job_descriptions: List[Dict]) -> None:
        """Fit the vectoriser on job description texts.

        Each JD is converted to a "document" by concatenating title +
        description + required_skills + preferred_skills.
        """
        docs: List[str] = []
        self._jd_ids = []
        self._jd_titles = []
        self._jd_categories = []

        for jd in job_descriptions:
            text_parts = [
                jd.get("title", ""),
                jd.get("description", ""),
                " ".join(jd.get("required_skills", [])),
                " ".join(jd.get("preferred_skills", [])),
            ]
            docs.append(" ".join(text_parts))
            self._jd_ids.append(jd.get("id", ""))
            self._jd_titles.append(jd.get("title", ""))
            self._jd_categories.append(jd.get("category", ""))

        # Fit on JDs and transform
        self._jd_matrix = self.vectorizer.fit_transform(docs)
        logger.info(f"Baseline: fitted TF-IDF on {len(docs)} JDs, vocab={len(self.vectorizer.vocabulary_)}")

    def rank_candidates(
        self,
        resume_texts: List[str],
        top_k: int = PARAMS.top_k_matches,
    ) -> List[List[Dict]]:
        """For each resume, rank all JDs by cosine similarity.

        Args:
            resume_texts: Raw resume texts.
            top_k: Number of top JD matches per resume.

        Returns:
            List (per resume) of ranked JD dicts with ``jd_id``, ``title``, ``score``.
        """
        if self._jd_matrix is None:
            raise RuntimeError("Call fit_jds() first.")

        resume_matrix = self.vectorizer.transform(resume_texts)
        sim = cosine_similarity(resume_matrix, self._jd_matrix)  # (n_resumes, n_jds)

        all_results: List[List[Dict]] = []
        for i in range(sim.shape[0]):
            scores = sim[i]
            ranked = np.argsort(-scores)[:top_k]
            result = [
                {
                    "jd_id": self._jd_ids[j],
                    "title": self._jd_titles[j],
                    "category": self._jd_categories[j],
                    "score": round(float(scores[j]), 4),
                }
                for j in ranked
            ]
            all_results.append(result)

        return all_results


def save_baseline_results(results: List[List[Dict]]) -> Path:
    """Persist baseline ranking results."""
    path = RESULTS_DIR / "baseline_results.json"
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved baseline results ({len(results)} candidates) to {path}")
    return path


# ── CLI ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("baseline.py – use via pipeline.py")
