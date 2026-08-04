"""Model distillation — train small specialized models from big model outputs."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any


@dataclass(slots=True)
class DistillationSample:
    """A single (input, teacher_output) pair for distillation."""

    id: str
    input_data: dict
    teacher_output: dict
    student_output: dict | None = None
    loss: float | None = None
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class DistilledModel:
    """A distilled model artifact."""

    id: str
    name: str
    teacher_model: str
    architecture: str  # e.g., "linear", "tiny_transformer", "decision_tree"
    parameters: dict = field(default_factory=dict)
    training_samples: int = 0
    validation_loss: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    artifacts_path: str = ""


class DistillationPipeline:
    """
    Distill knowledge from a large teacher model into a small specialized student.

    Pipeline:
    1. Collect (input, teacher_output) pairs from production
    2. Train student model to mimic teacher
    3. Validate on held-out set
    4. Deploy student for inference (faster, cheaper)
    """

    def __init__(self, storage_dir: str = ".distillation"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._samples_file = self.storage_dir / "samples.jsonl"
        self._models_dir = self.storage_dir / "models"
        self._models_dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._teacher_fn: Callable | None = None

    def set_teacher(self, teacher_fn: Callable[[dict], dict]) -> None:
        """Set the teacher model function.

        teacher_fn(input_data: dict) -> output_data: dict
        """
        self._teacher_fn = teacher_fn

    def collect_sample(self, input_data: dict, teacher_output: dict | None = None) -> str:
        """Collect a distillation sample (optionally query teacher)."""
        if teacher_output is None and self._teacher_fn:
            teacher_output = self._teacher_fn(input_data)

        sample = DistillationSample(
            id=f"sample_{uuid.uuid4().hex[:12]}",
            input_data=input_data,
            teacher_output=teacher_output or {},
        )

        with self._lock, open(self._samples_file, "a") as f:
            f.write(
                json.dumps(
                    {
                        "id": sample.id,
                        "input_data": sample.input_data,
                        "teacher_output": sample.teacher_output,
                        "student_output": sample.student_output,
                        "loss": sample.loss,
                        "metadata": sample.metadata,
                        "created_at": sample.created_at.isoformat(),
                    }
                )
                + "\n"
            )

        return sample.id

    def get_samples(self, limit: int | None = None) -> list[DistillationSample]:
        """Get collected distillation samples."""
        samples = []
        with self._lock:
            if not self._samples_file.exists():
                return []

            with open(self._samples_file) as f:
                for i, line in enumerate(f):
                    if limit and i >= limit:
                        break
                    try:
                        data = json.loads(line)
                        sample = DistillationSample(
                            id=data["id"],
                            input_data=data["input_data"],
                            teacher_output=data["teacher_output"],
                            student_output=data.get("student_output"),
                            loss=data.get("loss"),
                            metadata=data.get("metadata", {}),
                            created_at=datetime.fromisoformat(data["created_at"]),
                        )
                        samples.append(sample)
                    except Exception:
                        continue
        return samples

    def train_student(
        self,
        model_name: str,
        architecture: str = "linear",
        validation_split: float = 0.2,
        epochs: int = 100,
        learning_rate: float = 0.01,
    ) -> DistilledModel:
        """Train a student model on collected samples.

        For linear architecture, trains a simple linear model per output dimension.
        """
        samples = self.get_samples()
        if len(samples) < 10:
            raise ValueError("Need at least 10 samples for distillation")

        # Split train/val
        import random

        random.shuffle(samples)
        split_idx = int(len(samples) * (1 - validation_split))
        train_samples = samples[:split_idx]
        val_samples = samples[split_idx:]

        # Prepare training data
        import numpy as np

        # Embed inputs
        from cores.learning import embed_engagement

        x_train = np.array([embed_engagement(s.input_data) for s in train_samples])
        y_train = np.array(
            [
                list(s.teacher_output.values())[0] if isinstance(s.teacher_output, dict) and s.teacher_output else 0.0
                for s in train_samples
            ]
        )

        x_val = np.array([embed_engagement(s.input_data) for s in val_samples])
        y_val = np.array(
            [
                list(s.teacher_output.values())[0] if isinstance(s.teacher_output, dict) and s.teacher_output else 0.0
                for s in val_samples
            ]
        )

        # Train simple linear model
        if architecture == "linear":
            from sklearn.linear_model import Ridge

            model = Ridge(alpha=1.0)
            model.fit(x_train, y_train)

            # Validate
            val_pred = model.predict(x_val)
            val_loss = float(np.mean((val_pred - y_val) ** 2))

            artifacts = {
                "model_type": "linear",
                "weights": model.coef_.tolist(),
                "intercept": float(model.intercept_),
                "embedding_dim": x_train.shape[1],
            }

        elif architecture == "decision_tree":
            from sklearn.tree import DecisionTreeRegressor

            model = DecisionTreeRegressor(max_depth=5, random_state=42)
            model.fit(x_train, y_train)

            val_pred = model.predict(x_val)
            val_loss = float(np.mean((val_pred - y_val) ** 2))

            import pickle

            artifacts = {
                "model_type": "decision_tree",
                "pickled_model": pickle.dumps(model).hex(),
            }

        else:
            # Fallback: simple mean predictor
            mean_val = float(np.mean(y_train))
            val_loss = float(np.mean((y_val - mean_val) ** 2))
            artifacts = {
                "model_type": "mean_predictor",
                "mean": mean_val,
            }

        # Save model artifact
        model_id = f"distilled_{uuid.uuid4().hex[:12]}"
        model_path = self._models_dir / f"{model_id}.json"

        distilled = DistilledModel(
            id=model_id,
            name=model_name,
            teacher_model="unknown",
            architecture=architecture,
            parameters=artifacts,
            training_samples=len(train_samples),
            validation_loss=val_loss,
            artifacts_path=str(model_path),
        )

        with open(model_path, "w") as f:
            json.dump(
                {
                    "id": model_id,
                    "name": model_name,
                    "architecture": architecture,
                    "parameters": artifacts,
                    "validation_loss": val_loss,
                    "training_samples": len(train_samples),
                },
                f,
            )

        return distilled

    def predict(self, model_name: str, input_data: dict) -> Any:
        """Run inference with a distilled model."""
        model_path = self._models_dir / f"{model_name}.json"
        if not model_path.exists():
            # Try exact match
            for f in self._models_dir.glob("*.json"):
                if model_name in f.name:
                    model_path = f
                    break
            else:
                raise ValueError(f"Model {model_name} not found")

        with open(model_path) as f:
            artifact = json.load(f)

        params = artifact.get("parameters", {})
        arch = artifact.get("architecture", "linear")

        import numpy as np

        from cores.learning import embed_engagement

        emb = np.array(embed_engagement(input_data)).reshape(1, -1)

        if arch == "linear":
            weights = np.array(params.get("weights", [])).reshape(1, -1)
            intercept = params.get("intercept", 0.0)
            return float(emb @ weights.T + intercept)

        elif arch == "decision_tree":
            import pickle

            pickled = params.get("pickled_model", "")
            if pickled:
                model = pickle.loads(bytes.fromhex(pickled))
                return float(model.predict(emb)[0])

        return float(params.get("mean", 0.0))

    def get_stats(self) -> dict:
        """Get distillation pipeline stats."""
        samples = self.get_samples()
        models = list(self._models_dir.glob("*.json"))
        return {
            "total_samples": len(samples),
            "models_trained": len(models),
            "storage_path": str(self.storage_dir),
        }


# Global distillation pipeline
_distillation_pipeline = DistillationPipeline()


def set_distillation_teacher(teacher_fn) -> None:
    """Set the teacher model for distillation."""
    _distillation_pipeline.set_teacher(teacher_fn)


def collect_distillation_sample(input_data: dict, teacher_output: dict = None) -> str:
    """Collect a distillation sample."""
    return _distillation_pipeline.collect_sample(input_data, teacher_output)


def train_distilled_model(
    model_name: str,
    architecture: str = "linear",
    validation_split: float = 0.2,
    epochs: int = 100,
    learning_rate: float = 0.01,
) -> dict:
    """Train a distilled student model."""
    model = _distillation_pipeline.train_student(model_name, architecture, validation_split, epochs, learning_rate)
    return {
        "id": model.id,
        "name": model.name,
        "architecture": model.architecture,
        "training_samples": model.training_samples,
        "validation_loss": model.validation_loss,
    }


def predict_with_distilled(model_name: str, input_data: dict) -> Any:
    """Run inference with a distilled model."""
    return _distillation_pipeline.predict(model_name, input_data)


def get_distillation_stats() -> dict:
    return _distillation_pipeline.get_stats()
