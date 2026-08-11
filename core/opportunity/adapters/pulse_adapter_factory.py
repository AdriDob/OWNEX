"""Pulse adapter interface and factory."""

from __future__ import annotations

from core.opportunity.adapters.pulse import PulseAdapterFactory  # noqa: F401
from core.opportunity.adapters.pulse_adapter_base import PulseAdapter  # noqa: F401

__all__ = ["PulseAdapterFactory", "PulseAdapter"]
