"""A virtual clock.

The simulation never reads the wall clock, so runs are reproducible and can be
executed thousands of times faster than real time. Time is measured in hours
because the biological timescales being caricatured (inflammation, perfusion,
tissue repair) are conventionally discussed in hours to days.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import ConfigurationError

__all__ = ["VirtualClock"]

#: Guard-rail so a typo in a scenario cannot start an unbounded loop.
MAX_STEPS = 10_000_000


@dataclass(slots=True)
class VirtualClock:
    """Fixed-step virtual clock.

    ``t_hours`` is recomputed from ``steps * dt_hours`` on every tick rather
    than accumulated, which removes floating-point drift over long runs.
    """

    dt_hours: float = 0.05
    t_hours: float = field(default=0.0, init=False)
    steps: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.dt_hours <= 0:
            raise ConfigurationError(f"dt_hours must be positive, got {self.dt_hours}")
        self.t_hours = 0.0
        self.steps = 0

    def tick(self) -> float:
        """Advance one step and return the new time in hours."""
        if self.steps >= MAX_STEPS:
            raise ConfigurationError(
                f"virtual clock exceeded {MAX_STEPS} steps; check durations and dt"
            )
        self.steps += 1
        self.t_hours = round(self.steps * self.dt_hours, 12)
        return self.t_hours

    def reset(self) -> None:
        self.t_hours = 0.0
        self.steps = 0

    @property
    def elapsed_hours(self) -> float:
        return self.t_hours

    def steps_for(self, hours: float) -> int:
        """Number of whole steps needed to cover ``hours``."""
        if hours < 0:
            raise ConfigurationError("hours must be non-negative")
        return int(round(hours / self.dt_hours))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dt_hours": self.dt_hours,
            "t_hours": self.t_hours,
            "steps": self.steps,
        }
