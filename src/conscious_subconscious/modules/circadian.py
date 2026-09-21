"""Circadian modulation of repair signalling.

Publishes a dimensionless ``circadian`` factor in ``[1 - A, 1 + A]`` that the
subconscious repair rule multiplies its rate by. With the circadian module
absent the factor defaults to 1.0 and the term disappears entirely.

The *existence* of circadian variation in human physiology is well established,
and the 24 h period is therefore tagged ``literature``. The *depth* of
modulation used here is assumed — it is a plausible-looking number, not a
measured one.
"""

from __future__ import annotations

import math
from typing import ClassVar

from ..model.context import StepContext
from .base import Module
from .registry import register

__all__ = ["CircadianModule"]


@register
class CircadianModule(Module):
    """Sinusoidal circadian factor, phase-locked to the virtual clock."""

    name: ClassVar[str] = "circadian"

    @classmethod
    def parameter_keys(cls) -> tuple[str, ...]:
        return ("module.circadian.amplitude", "module.circadian.period_hours")

    def step(self, ctx: StepContext) -> None:
        amplitude = self.params.value("module.circadian.amplitude")
        period = self.params.value("module.circadian.period_hours")
        phase = 2.0 * math.pi * (ctx.t_hours % period) / period
        factor = 1.0 + amplitude * math.sin(phase)
        ctx.set_signal("circadian", factor)
        ctx.set_signal("circadian_phase_radians", phase)
