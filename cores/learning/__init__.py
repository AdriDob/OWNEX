"""Learning loop — continuous improvement for agents.

This module re-exports all learning components. Use lazy imports to avoid circular imports.
"""

from __future__ import annotations


# Core engagement functions - lazy loaded
def record_engagement_outcome(*args, **kwargs):
    from .engagements import record_engagement_outcome as _fn

    return _fn(*args, **kwargs)


def find_similar_engagements(*args, **kwargs):
    from .engagements import find_similar_engagements as _fn

    return _fn(*args, **kwargs)


def get_learning_stats(*args, **kwargs):
    from .engagements import get_learning_stats as _fn

    return _fn(*args, **kwargs)


def embed_engagement(*args, **kwargs):
    from .engagements import embed_engagement as _fn

    return _fn(*args, **kwargs)


# Contrastive learning
def add_success_failure_pair(*args, **kwargs):
    from .contrastive import add_success_failure_pair as _fn

    return _fn(*args, **kwargs)


def train_contrastive(*args, **kwargs):
    from .contrastive import train_contrastive as _fn

    return _fn(*args, **kwargs)


def score_engagement_likelihood(*args, **kwargs):
    from .contrastive import score_engagement_likelihood as _fn

    return _fn(*args, **kwargs)


def get_contrastive_model_state(*args, **kwargs):
    from .contrastive import get_contrastive_model_state as _fn

    return _fn(*args, **kwargs)


# Prompt evolution
def initialize_prompt_evolution(*args, **kwargs):
    from .evolution import initialize_prompt_evolution as _fn

    return _fn(*args, **kwargs)


def set_prompt_fitness_evaluator(*args, **kwargs):
    from .evolution import set_prompt_fitness_evaluator as _fn

    return _fn(*args, **kwargs)


def evolve_prompts(*args, **kwargs):
    from .evolution import evolve_prompts as _fn

    return _fn(*args, **kwargs)


def get_best_prompt(*args, **kwargs):
    from .evolution import get_best_prompt as _fn

    return _fn(*args, **kwargs)


def get_evolution_stats(*args, **kwargs):
    from .evolution import get_evolution_stats as _fn

    return _fn(*args, **kwargs)


# Model distillation
def set_distillation_teacher(*args, **kwargs):
    from .distillation import set_distillation_teacher as _fn

    return _fn(*args, **kwargs)


def collect_distillation_sample(*args, **kwargs):
    from .distillation import collect_distillation_sample as _fn

    return _fn(*args, **kwargs)


def train_distilled_model(*args, **kwargs):
    from .distillation import train_distilled_model as _fn

    return _fn(*args, **kwargs)


def predict_with_distilled(*args, **kwargs):
    from .distillation import predict_with_distilled as _fn

    return _fn(*args, **kwargs)


def get_distillation_stats(*args, **kwargs):
    from .distillation import get_distillation_stats as _fn

    return _fn(*args, **kwargs)


# Learning loop
def start_learning_loop(*args, **kwargs):
    from .loop import start_learning_loop as _fn

    return _fn(*args, **kwargs)


def stop_learning_loop(*args, **kwargs):
    from .loop import stop_learning_loop as _fn

    return _fn(*args, **kwargs)


def force_learning_cycle(*args, **kwargs):
    from .loop import force_learning_cycle as _fn

    return _fn(*args, **kwargs)


def get_learning_loop_status(*args, **kwargs):
    from .loop import get_learning_loop_status as _fn

    return _fn(*args, **kwargs)


def get_learning_history(*args, **kwargs):
    from .loop import get_learning_history as _fn

    return _fn(*args, **kwargs)


def register_prompt_update_callback(*args, **kwargs):
    from .loop import register_prompt_update_callback as _fn

    return _fn(*args, **kwargs)


# Service getters (used by the API router)
def get_profile_service(*args, **kwargs):
    from .profile import get_profile_service as _fn

    return _fn(*args, **kwargs)


def get_event_tracker(*args, **kwargs):
    from .tracker import get_event_tracker as _fn

    return _fn(*args, **kwargs)


def get_prioritizer(*args, **kwargs):
    from .prioritizer import get_prioritizer as _fn

    return _fn(*args, **kwargs)


def get_explainer(*args, **kwargs):
    from .explainer import get_explainer as _fn

    return _fn(*args, **kwargs)


def get_memory_builder(*args, **kwargs):
    from .memory import get_memory_builder as _fn

    return _fn(*args, **kwargs)


def get_exporter(*args, **kwargs):
    from .export import get_exporter as _fn

    return _fn(*args, **kwargs)


__all__ = [
    "record_engagement_outcome",
    "find_similar_engagements",
    "get_learning_stats",
    "embed_engagement",
    "add_success_failure_pair",
    "train_contrastive",
    "score_engagement_likelihood",
    "get_contrastive_model_state",
    "initialize_prompt_evolution",
    "set_prompt_fitness_evaluator",
    "evolve_prompts",
    "get_best_prompt",
    "get_evolution_stats",
    "set_distillation_teacher",
    "collect_distillation_sample",
    "train_distilled_model",
    "predict_with_distilled",
    "get_distillation_stats",
    "start_learning_loop",
    "stop_learning_loop",
    "force_learning_cycle",
    "get_learning_loop_status",
    "get_learning_history",
    "register_prompt_update_callback",
    "get_profile_service",
    "get_event_tracker",
    "get_prioritizer",
    "get_explainer",
    "get_memory_builder",
    "get_exporter",
]
