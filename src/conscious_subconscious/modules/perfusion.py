"""Perfusion: local delivery capacity as a leaky integrator.

The module computes a target — a baseline plus damage-driven vasodilation — and
adds production proportional to the gap. The mediator field's decay pulls the
channel back down, so the channel settles *below* the target. That is not a
bug: it is what a leaky integrator does, and it is stated here so nobody spends
an afternoon rediscovering it.

Delivery is plausibly one of the mechanisms by which any attentional or
autonomic intervention could matter in a real body. That makes it the most
worthwhile place to look for a real mechanism, and also the easiest place to
fool yourself, since the numbers are invented.
"""

from __future__ import annotations

from typing import ClassVar

from ..core.params import ParameterSet
from ..model.context import StepContext
from .base import Module
from .registry import register

__all__ = ["PerfusionModule"]


@register
class PerfusionModule(Module):
    """Damage-driven vasodilation pushing the perfusion channel toward a target."""

    name: ClassVar[str] = "perfusion"

    def __init__(self, params: ParameterSet) -> None:
        super().__init__(params)
        self.last_target = params.value("module.perfusion.baseline")

    @classmethod
    def parameter_keys(cls) -> tuple[str, ...]:
        return (
            "module.perfusion.baseline",
            "module.perfusion.vasodilation_gain",
            "module.perfusion.response_rate",
        )

    def step(self, ctx: StepContext) -> None:
        params = self.params
        target = params.value("module.perfusion.baseline") + (
            params.value("module.perfusion.vasodilation_gain") * ctx.tissue.damage
        )
        self.last_target = target
        current = ctx.field.value("perfusion")
        gap = target - current
        if gap > 0.0:
            production = gap * params.value("module.perfusion.response_rate")
            ctx.field.add("perfusion", production * ctx.dt_hours)
        ctx.set_signal("perfusion_target", target)
        ctx.set_signal("perfusion", ctx.field.value("perfusion"))
