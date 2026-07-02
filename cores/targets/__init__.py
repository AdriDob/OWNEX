"""Targets: modelos e inteligencia de programas bug bounty."""

from cores.targets.filters import (
    filter_targets_by_max_complexity,
    filter_targets_by_min_quality,
    filter_targets_by_platform,
)
from cores.targets.hunter import Hunter
from cores.targets.models import Scope, TargetIntel
from cores.targets.parser import parse_program_scopes

__all__ = [
    "TargetIntel", "Scope", "Hunter",
    "filter_targets_by_min_quality", "filter_targets_by_max_complexity",
    "filter_targets_by_platform", "parse_program_scopes",
]
