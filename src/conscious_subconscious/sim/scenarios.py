"""Named, reproducible run configurations.

A scenario is a :class:`RunConfig` plus a one-line summary and a caveat. The
caveat is not decoration: several scenarios exist specifically to demonstrate
that a result is produced by a parameter rather than discovered, and the report
says so where the number appears.

Scenarios are declared in Python so they can be unit-tested, and can also be
loaded from a JSON file for experimentation without touching the package.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.errors import ConfigurationError
from ..model.engine import FOCUS_POLICIES, RunConfig

__all__ = ["Scenario", "builtin_scenarios", "get_scenario", "load_scenarios", "scenario_names"]


@dataclass(frozen=True, slots=True)
class Scenario:
    """A named configuration plus the honesty note that belongs next to it."""

    name: str
    summary: str
    config: Mapping[str, Any] = field(default_factory=dict)
    caveat: str = ""

    def build(self, **overrides: Any) -> RunConfig:
        """Materialise a :class:`RunConfig`, applying caller overrides last."""
        merged: dict[str, Any] = dict(self.config)
        merged["scenario"] = self.name
        merged.update(overrides)
        return RunConfig(**merged)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "caveat": self.caveat,
            "config": dict(self.config),
        }


_BUILTIN: tuple[Scenario, ...] = (
    Scenario(
        name="baseline",
        summary="Subconscious repair alone. Attention is never engaged.",
        config={
            "focus_policy": "never",
            "modules": ("inflammation", "perfusion", "circadian"),
        },
        caveat=(
            "This is the reference condition. Every comparison below is relative to it, "
            "so an error here propagates into every other number."
        ),
    ),
    Scenario(
        name="focused",
        summary="Attention held as long as the budget allows, releasing only to recover.",
        config={
            "focus_policy": "always",
            "modules": ("inflammation", "perfusion", "circadian"),
        },
        caveat=(
            "The speed-up depends entirely on conscious.neural_drive_coupling, an "
            "invented constant. Run 'focused-uncoupled' to see the same scenario with "
            "that constant set to zero."
        ),
    ),
    Scenario(
        name="intermittent",
        summary="Attention engaged only while damage is between 20% and 80%.",
        config={
            "focus_policy": "intermittent",
            "modules": ("inflammation", "perfusion", "circadian"),
        },
        caveat=(
            "Mirrors the source document's hand-written rule, which is why it exists. "
            "The original document gave no justification for the 20/80 band."
        ),
    ),
    Scenario(
        name="focused-uncoupled",
        summary="Attention held continuously, but with the mind-to-tissue coupling set to zero.",
        config={
            "focus_policy": "always",
            "modules": ("inflammation", "perfusion", "circadian"),
            "overrides": {"conscious.neural_drive_coupling": 0.0},
        },
        caveat=(
            "The control case. Its result must be identical to 'baseline'. If it is "
            "not, something in the attention path is leaking into repair and that is "
            "a bug, not a finding."
        ),
    ),
    Scenario(
        name="expectancy-on",
        summary="Attention plus an expectancy module, with both expectancy gains enabled.",
        config={
            "focus_policy": "always",
            "modules": ("inflammation", "perfusion", "circadian", "expectancy"),
            "overrides": {
                "module.expectancy.gain": 0.5,
                "module.expectancy.perception_gain": 0.15,
            },
        },
        caveat=(
            "PURELY ILLUSTRATIVE. Both expectancy gains are invented and default to "
            "zero. Nothing here shows that expectation changes tissue repair; it only "
            "shows what the model does when you assert that it does."
        ),
    ),
    Scenario(
        name="inflammation-heavy",
        summary="Baseline repair with inflammation allowed to suppress almost all of it.",
        config={
            "focus_policy": "never",
            "modules": ("inflammation", "perfusion", "circadian"),
            "overrides": {
                "module.inflammation.baseline": 0.60,
                "module.inflammation.repair_inhibition": 0.95,
            },
        },
        caveat=(
            "Demonstrates that the model can produce arbitrarily bad outcomes by "
            "choice of constants — the same property the source document had."
        ),
    ),
    Scenario(
        name="unmodulated",
        summary="No optional modules at all: repair driven only by growth-factor saturation.",
        config={
            "focus_policy": "never",
            "modules": (),
        },
        caveat=(
            "Useful as a purity check on the module layer. With no modules the "
            "circadian factor is absent and defaults to 1.0."
        ),
    ),
    Scenario(
        name="autonomic-coupled",
        summary="Attention plus autonomic tone fed from an HRV-style index of 0.8.",
        config={
            "focus_policy": "always",
            "modules": ("inflammation", "perfusion", "circadian", "autonomic"),
        },
        caveat=(
            "The HRV index is a fixed number here, not a measurement. Wiring a real "
            "device changes where the number comes from, not whether it means anything."
        ),
    ),
    Scenario(
        name="week-long",
        summary="A seven-day horizon, to expose drift and long-run behaviour.",
        config={
            "focus_policy": "intermittent",
            "horizon_hours": 168.0,
            "modules": ("inflammation", "perfusion", "circadian"),
        },
        caveat=(
            "Nothing in the model was calibrated beyond about three days, and the "
            "tissue abstraction has no scar or re-injury term, so a week is already "
            "an extrapolation."
        ),
    ),
)

_BY_NAME: dict[str, Scenario] = {s.name: s for s in _BUILTIN}
DEFAULT_COMPARISON: tuple[str, ...] = ("baseline", "focused", "intermittent")


def builtin_scenarios() -> tuple[Scenario, ...]:
    """All built-in scenarios, in declaration order."""
    return _BUILTIN


def scenario_names() -> tuple[str, ...]:
    return tuple(_BY_NAME)


def get_scenario(name: str) -> Scenario:
    """Look up a built-in scenario by name."""
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise ConfigurationError(
            f"unknown scenario {name!r}; available: {', '.join(scenario_names())}"
        ) from exc


def load_scenarios(path: str | Path) -> tuple[Scenario, ...]:
    """Load extra scenarios from a JSON file.

    The file is either a list of objects or an object keyed by scenario name.
    Unknown keys are rejected rather than ignored: a typo in a config that
    silently does nothing is worse than a crash.
    """
    location = Path(path)
    if not location.is_file():
        raise ConfigurationError(f"scenario file not found: {location}")
    try:
        raw = json.loads(location.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{location} is not valid JSON: {exc}") from exc

    if isinstance(raw, dict):
        entries = [dict(value, name=key) for key, value in raw.items()]
    elif isinstance(raw, list):
        entries = raw
    else:
        raise ConfigurationError("scenario file must contain an object or a list")

    allowed_config = set(RunConfig.__dataclass_fields__) - {"scenario"}
    scenarios: list[Scenario] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ConfigurationError("each scenario must be an object")
        name = entry.get("name")
        if not name:
            raise ConfigurationError("every scenario needs a 'name'")
        config = entry.get("config", {})
        unknown = set(config) - allowed_config
        if unknown:
            raise ConfigurationError(
                f"scenario {name!r} has unknown config key(s): {sorted(unknown)}"
            )
        policy = config.get("focus_policy")
        if policy is not None and policy not in FOCUS_POLICIES:
            raise ConfigurationError(f"scenario {name!r} has unknown focus_policy {policy!r}")
        scenarios.append(
            Scenario(
                name=str(name),
                summary=str(entry.get("summary", "")),
                config=config,
                caveat=str(entry.get("caveat", "")),
            )
        )
    return tuple(scenarios)
