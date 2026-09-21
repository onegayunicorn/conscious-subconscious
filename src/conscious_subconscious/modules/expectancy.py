"""Expectancy: the placebo/nocebo-shaped module, disabled by default.

Why it ships at all
-------------------
The source document implies a mind-over-tissue effect without ever separating
it from expectation. Expectancy effects are real and well documented — but for
*subjective* outcomes (pain, nausea, perceived improvement). Whether expecting
to heal changes how fast tissue actually repairs is a different question that
the literature does not settle.

So the module exists, is wired to two explicitly separated outputs, and ships
with **both gains at zero**:

* ``module.expectancy.perception_gain`` — shifts *felt* progress only. No
  physical effect. This is the honest use of the evidence.
* ``module.expectancy.gain`` — adds production to the ``neural_drive`` channel.
  This is the physical claim, and it is off. Turning it on is a deliberate act
  that produces a model result, not a discovery about people.

A disabled module that documents why it is disabled is more useful than a
missing one, because it stops the next person from "adding" it as if it were an
oversight.
"""

from __future__ import annotations

from typing import Any, ClassVar

from ..model.context import StepContext
from .base import Module
from .registry import register

__all__ = ["ExpectancyModule"]


@register
class ExpectancyModule(Module):
    """Expectancy-driven perception bias, with an opt-in physical channel."""

    name: ClassVar[str] = "expectancy"

    @classmethod
    def parameter_keys(cls) -> tuple[str, ...]:
        return ("module.expectancy.gain", "module.expectancy.perception_gain")

    @property
    def enabled(self) -> bool:
        """True when either gain is non-zero."""
        return (
            self.params.value("module.expectancy.gain") > 0.0
            or self.params.value("module.expectancy.perception_gain") > 0.0
        )

    def step(self, ctx: StepContext) -> None:
        if not self.enabled:
            ctx.set_signal("expectancy", 0.0)
            return

        perception_gain = self.params.value("module.expectancy.perception_gain")
        physical_gain = self.params.value("module.expectancy.gain")

        # Crude belief proxy: expectancy rises as visible damage falls. A real
        # study would measure expectancy before and during the intervention;
        # this model has no way to do that, which is itself a limitation.
        belief = 1.0 - ctx.tissue.damage

        ctx.set_signal("expectancy", perception_gain * belief)
        if physical_gain > 0.0:
            ctx.field.add("neural_drive", physical_gain * belief * ctx.dt_hours)

    def describe(self) -> dict[str, Any]:
        described = super().describe()
        described["state"] = {"enabled": self.enabled}
        if not self.enabled:
            described["note"] = (
                "both gains are 0.0 by default; enabling them constitutes an "
                "assumption, not a finding"
            )
        return described
