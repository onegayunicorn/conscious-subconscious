"""Scenario definitions, sweeps, reports and the command-line interface."""

from __future__ import annotations

from .report import render_comparison, render_report
from .scenarios import (
    DEFAULT_COMPARISON,
    Scenario,
    builtin_scenarios,
    get_scenario,
    load_scenarios,
    scenario_names,
)
from .sweep import (
    SweepPoint,
    SweepResult,
    one_factor_sensitivity,
    render_sensitivity_markdown,
    render_sweep_markdown,
    sweep_parameter,
)

__all__ = [
    "DEFAULT_COMPARISON",
    "Scenario",
    "SweepPoint",
    "SweepResult",
    "builtin_scenarios",
    "get_scenario",
    "load_scenarios",
    "one_factor_sensitivity",
    "render_comparison",
    "render_report",
    "render_sensitivity_markdown",
    "render_sweep_markdown",
    "scenario_names",
    "sweep_parameter",
]
