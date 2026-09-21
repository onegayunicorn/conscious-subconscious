"""Autonomic tone: a bridge for real hardware.

This is the module that hardware feeds. A heart-rate-variability or
respiration-derived index in ``[0, 1]`` arrives from a device adapter, is
converted into modelled parasympathetic tone, and pushes a small amount of
production into the perfusion channel.

It is deliberately a *one-way* bridge. Nothing in this project lets a device
change tissue integrity directly, and nothing lets the simulation send a
stimulus to a body. The hardware layer is read-only with respect to the person
wearing the sensor; see ``security/threat-model.md``.

HRV biofeedback has reasonable evidence for *stress and anxiety* outcomes (see
``research/literature-review.md``). It has no established effect on tissue
repair, and this module does not claim one — it only moves a channel whose
downstream effect is itself an invented coupling.
"""

from __future__ import annotations

from typing import Any, ClassVar

from ..core.params import ParameterSet
from ..model.context import StepContext
from .base import Module
from .registry import register

__all__ = ["AutonomicModule"]


@register
class AutonomicModule(Module):
    """Maps an external HRV-style index onto modelled parasympathetic tone."""

    name: ClassVar[str] = "autonomic"

    def __init__(self, params: ParameterSet) -> None:
        super().__init__(params)
        #: Neutral resting assumption until a device or caller says otherwise.
        self.hrv_index = 0.5
        self.samples_received = 0

    @classmethod
    def parameter_keys(cls) -> tuple[str, ...]:
        return (
            "module.autonomic.parasympathetic_gain",
            "module.autonomic.perfusion_gain",
        )

    def observe(self, index: float) -> None:
        """Accept an external index in ``[0, 1]`` (clamped, not rejected).

        A sensor that reports nonsense should not crash a run; the clamp is
        intentional and the raw value is not retained.
        """
        value = float(index)
        if value != value:  # NaN guard
            return
        self.hrv_index = max(0.0, min(1.0, value))
        self.samples_received += 1

    def step(self, ctx: StepContext) -> None:
        index = ctx.signal("hrv_index", self.hrv_index)
        index = max(0.0, min(1.0, index))
        tone = max(
            0.0, min(1.0, self.params.value("module.autonomic.parasympathetic_gain") * index)
        )
        ctx.set_signal("parasympathetic", tone)

        production = self.params.value("module.autonomic.perfusion_gain") * tone
        if production > 0.0:
            ctx.field.add("perfusion", production * ctx.dt_hours)

    def describe(self) -> dict[str, Any]:
        described = super().describe()
        described["state"] = {
            "hrv_index": round(self.hrv_index, 6),
            "samples_received": self.samples_received,
        }
        return described
