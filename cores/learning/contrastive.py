"""Contrastive learning — learn from success vs failure patterns."""

from __future__ import annotations

import json
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from pathlib import Path
from threading import Lock


@dataclass(slots=True)
class ContrastivePair:
    """A positive/negative pair for contrastive learning."""

    positive: dict
    negative: dict
    label: float  # 1.0 for positive, 0.0 for negative
    metadata: dict = field(default_factory=dict)


class ContrastiveLearner:
    """
    Learns to distinguish successful from failed engagement patterns.
    Uses a simple linear probe on top of embeddings.
    """

    def __init__(self, embedding_dim: int = 384, lr: float = 0.01):
        self.embedding_dim = embedding_dim
        self.lr = lr
        self.weights = np.random.randn(embedding_dim) * 0.01
        self.bias = 0.0
        self._lock = Lock()
        self._training_history = []

    def add_training_pair(self, positive: dict, negative: dict) -> None:
        """Add a positive/negative pair for training."""
        from cores.learning import embed_engagement

        pos_emb = np.array(embed_engagement(positive))
        neg_emb = np.array(embed_engagement(negative))

        self._training_history.append(
            {
                "positive": pos_emb,
                "negative": neg_emb,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def train_step(self, batch_size: int = 32) -> dict:
        """Run one contrastive training step."""
        if len(self._training_history) < 2:
            return {"loss": 0.0, "pairs": 0}

        with self._lock:
            batch = self._training_history[-batch_size:]

            total_loss = 0.0
            correct = 0

            for pair in batch:
                pos_emb = pair["positive"]
                neg_emb = pair["negative"]

                # Positive should score high, negative low
                pos_score = np.dot(self.weights, pos_emb) + self.bias
                neg_score = np.dot(self.weights, neg_emb) + self.bias

                # Contrastive loss: want pos_score > neg_score + margin
                margin = 1.0
                loss = max(0, margin - pos_score + neg_score)

                if pos_score > neg_score:
                    correct += 1

                total_loss += loss

                # Gradient update
                if loss > 0:
                    grad = self.lr * (neg_emb - pos_emb)
                    self.weights -= grad
                    self.bias -= self.lr * (-1)

            return {
                "loss": total_loss / max(len(batch), 1),
                "accuracy": correct / len(batch),
                "pairs": len(batch),
            }

    def score_engagement(self, engagement_data: dict) -> float:
        """Score an engagement - higher means more likely to succeed."""
        from cores.learning import embed_engagement

        emb = np.array(embed_engagement(engagement_data))
        score = np.dot(self.weights, emb) + self.bias
        # Sigmoid to [0, 1]
        return 1.0 / (1.0 + np.exp(-score))

    def get_model_state(self) -> dict:
        return {
            "weights_norm": float(np.linalg.norm(self.weights)),
            "bias": float(self.bias),
            "training_pairs": len(self._training_history),
        }


# Global learner instance
_contrastive_learner = ContrastiveLearner()


def add_success_failure_pair(success_data: dict, failure_data: dict) -> None:
    """Add a success/failure pair for contrastive learning."""
    _contrastive_learner.add_training_pair(success_data, failure_data)


def train_contrastive(batch_size: int = 32) -> dict:
    """Run one training step."""
    return _contrastive_learner.train_step(batch_size)


def score_engagement_likelihood(engagement_data: dict) -> float:
    """Score how likely an engagement is to succeed (0-1)."""
    return _contrastive_learner.score_engagement(engagement_data)


def get_contrastive_model_state() -> dict:
    return _contrastive_learner.get_model_state()
