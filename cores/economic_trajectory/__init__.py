"""APP FACTORY — trayectoria económica (spec ECONOMIC TRAJECTORY TRACKER)."""

from cores.economic_trajectory.trajectory import (
    build_trajectory,
    calibrate_scenarios,
    calibration_level,
    channel_economics,
    channel_validation,
    compare_scenario_to_real,
    gap_to_target,
    scenarios_block,
)

__all__ = [
    "build_trajectory",
    "calibration_level",
    "calibrate_scenarios",
    "channel_economics",
    "channel_validation",
    "compare_scenario_to_real",
    "gap_to_target",
    "scenarios_block",
]
