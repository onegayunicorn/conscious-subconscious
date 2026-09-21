"""Inflammation: a signal that rises with damage and suppresses repair.

The source document had no inflammation term at all, which is why its healing
curve was a straight line. Real repair is not monotone in a useful sense — the
inflammatory phase is necessary and, while it lasts, competes with repair. This
module adds that competition as one multiplicative suppression term.

Only the *direction* of the effect is well founded. The size is assumed.
"""

from __future__ import annotations

from typing import Any, ClassVar

from ..core.params import ParameterSet
from ..model.context import StepContext
from .base import Module
from .registry import register

__all__ = ["InflammationModule"]


@register
class InflammationModule(Module):
    """Inflammation level that tracks damage and inhibits repair."""

    name: ClassVar[str] = "inflammation"

    def __init__(self, params: ParameterSet) -> None:
        super().__init__(params)
        self.level = params.value("module.inflammation.baseline")

    @classmethod
    def parameter_keys(cls) -> tuple[str, ...]:
        return (
            "module.inflammation.baseline",
            "module.inflammation.repair_inhibition",
            "module.inflammation.settling_rate",
        )

    def step(self, ctx: StepContext) -> None:
        params = self.params
        baseline = params.value("module.inflammation.baseline")
        target = baseline + (1.0 - baseline) * ctx.tissue.damage
        rate = params.value("module.inflammation.settling_rate")
        # A first-order relaxation, clamped so a large dt cannot overshoot.
        alpha = min(1.0, rate * ctx.dt_hours)
        self.level += (target - self.level) * alpha
        self.level = max(0.0, min(1.0, self.level))
        ctx.set_signal("inflammation", self.level)

    def describe(self) -> dict[str, Any]:
        described = super().describe()
        described["state"] = {"level": round(self.level, 9)}
        return described
