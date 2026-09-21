"""Request models.

Only requests are modelled with pydantic. Responses are plain dictionaries built
by the engine's own ``as_dict`` methods, because a second declarative description
of the result shape would be a second thing to keep in sync — and the one that
drifts would be the schema, not the engine.

``extra="forbid"`` everywhere: a client that sends a typo'd field must be told,
not silently ignored.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = ["SimulationCreate", "CommandRequest", "RunRequest", "StepRequest"]


def _check_overrides(overrides: dict[str, float]) -> dict[str, float]:
    for key, value in overrides.items():
        if not key or "." not in key:
            raise ValueError(
                f"override key {key!r} must be dotted, e.g. 'conscious.neural_drive_gain'"
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"override value for {key!r} must be a number")
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"override value for {key!r} must be finite")
    return overrides


class SimulationCreate(BaseModel):
    """Body of ``POST /v1/sessions``."""

    model_config = ConfigDict(extra="forbid")

    scenario: str = Field(default="baseline", max_length=64)
    seed: int = Field(default=20260921, ge=0, le=2**31 - 1)
    dt_hours: float = Field(default=0.05, gt=0, le=1.0, description="Virtual time step in hours.")
    horizon_hours: float = Field(default=72.0, gt=0, le=8760.0, description="Run length in hours.")
    tissue_name: str = Field(default="muscle tissue", min_length=1, max_length=64)
    focus_policy: Literal["never", "always", "intermittent"] = "never"
    modules: list[str] = Field(default_factory=list, max_length=16)
    overrides: dict[str, float] = Field(default_factory=dict)

    @field_validator("overrides")
    @classmethod
    def validate_overrides(cls, value: dict[str, float]) -> dict[str, float]:
        return _check_overrides(value)

    @field_validator("modules")
    @classmethod
    def validate_modules(cls, value: list[str]) -> list[str]:
        for name in value:
            if not name or len(name) > 32:
                raise ValueError(f"module name {name!r} is not usable")
        return sorted(set(value))


class RunRequest(BaseModel):
    """Body of ``POST /v1/sessions/{id}/run``."""

    model_config = ConfigDict(extra="forbid")

    hours: float | None = Field(
        default=None,
        gt=0,
        le=8760.0,
        description="Run to this many elapsed hours; omit to run the configured horizon.",
    )


class StepRequest(BaseModel):
    """Body of ``POST /v1/sessions/{id}/step``."""

    model_config = ConfigDict(extra="forbid")

    count: int = Field(default=1, ge=1, le=10_000, description="How many steps to advance.")


class CommandRequest(BaseModel):
    """Body of ``POST /v1/sessions/{id}/commands``.

    There is deliberately no command that sets tissue integrity. Nothing may
    bypass the repair rule, including an API caller.
    """

    model_config = ConfigDict(extra="forbid")

    command: Literal["focus", "release", "set_policy"]
    target: str | None = Field(default=None, max_length=128)
    policy: Literal["never", "always", "intermittent"] | None = None

    @model_validator(mode="after")
    def policy_required_for_set_policy(self) -> CommandRequest:
        """Cross-field rule.

        Expressed as a model validator rather than a field validator because it
        depends on a sibling field, and a field validator's view of its siblings
        depends on declaration order — a brittle thing to rely on for a rule that
        guards a state change.
        """
        if self.command == "set_policy" and self.policy is None:
            raise ValueError("policy is required when command='set_policy'")
        return self
