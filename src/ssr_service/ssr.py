"""Semantic similarity rating implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np

from .anchors import AnchorBank, AnchorSet, load_anchor_bank
from .config import get_settings
from .embedding import embed_text, embed_texts


def _cosine_similarity(vec: np.ndarray, mat: np.ndarray) -> np.ndarray:
    vec_norm = np.linalg.norm(vec)
    if vec_norm == 0:
        return np.zeros(mat.shape[0])
    mat_norms = np.linalg.norm(mat, axis=1)
    denom = np.clip(vec_norm * mat_norms, a_min=1e-8, a_max=None)
    return (mat @ vec) / denom


@dataclass(slots=True)
class AnchorEmbeddings:
    anchor_set: AnchorSet
    embeddings: np.ndarray


class SemanticSimilarityRater:
    """Map free-text rationales to Likert pmfs using anchor similarity."""

    def __init__(self, bank: AnchorBank, epsilon: float = 1e-6) -> None:
        self.bank = bank
        self.epsilon = epsilon
        self._embedded_sets: List[AnchorEmbeddings] = self._embed_anchors(bank)
        self._ratings = list(self.bank.anchor_sets[0].anchors.keys())

    @staticmethod
    def _embed_anchors(bank: AnchorBank) -> List[AnchorEmbeddings]:
        embeddings: List[AnchorEmbeddings] = []
        for anchor_set in bank.anchor_sets:
            ordered = [text for _, text in anchor_set.sorted_items()]
            matrix = embed_texts(ordered)
            embeddings.append(
                AnchorEmbeddings(anchor_set=anchor_set, embeddings=matrix)
            )
        return embeddings

    def ratings(self) -> List[int]:
        return self._ratings

    def score_text(self, text: str) -> np.ndarray:
        """Return Likert pmf for a single text."""

        text_vec = embed_text(text)
        per_set_pmf: List[np.ndarray] = []

        for embed in self._embedded_sets:
            sims = _cosine_similarity(text_vec, embed.embeddings)
            sims = np.maximum(sims, 0.0) + self.epsilon
            pmf = sims / sims.sum()
            per_set_pmf.append(pmf)

        stacked = np.vstack(per_set_pmf)
        pmf = stacked.mean(axis=0)
        return pmf / pmf.sum()

    def score_many(self, texts: Iterable[str]) -> np.ndarray:
        return np.vstack([self.score_text(text) for text in texts])


def likert_metrics(pmf: np.ndarray, ratings: Iterable[int]) -> Tuple[float, float]:
    rating_list = list(ratings)
    mean = float(np.dot(pmf, rating_list))
    top2 = float(
        sum(p for p, r in zip(pmf, rating_list) if r >= max(rating_list) - 1)
    )
    return mean, top2


def load_rater(anchor_filename: str) -> SemanticSimilarityRater:
    settings = get_settings()
    base = Path(settings.anchor_bank_path)
    path = (
        anchor_filename if anchor_filename.startswith("/") else base / anchor_filename
    )
    bank = load_anchor_bank(Path(path))
    return SemanticSimilarityRater(bank)


__all__ = ["SemanticSimilarityRater", "likert_metrics", "load_rater"]
