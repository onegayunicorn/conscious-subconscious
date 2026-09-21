"""The subconscious system: autonomous, unconditional, background repair.

The source document's ``SubconsciousSystem`` did exactly one thing — subtract a
constant from ``damage_level`` every tick. This version keeps the same spirit
but makes the dependencies visible, so that a reader can point at any term and
ask "why is that there?":

.. math::

    R_{base} = k_{repair} \\cdot S(G) \\cdot (1 - \\rho \\cdot I) \\cdot C(t)

where

* :math:`k_{repair}` is ``subconscious.base_repair_rate`` — **invented**;
* :math:`S(G) = G/(G+K_{gf})` is a Michaelis-Menten saturation on growth-factor
  availability :math:`G`, with :math:`K_{gf}` an **assumed** half-saturation;
* :math:`I` is the inflammation level (module signal) and :math:`\\rho` the
  assumed fraction of capacity inflammation can suppress;
* :math:`C(t)` is the circadian factor (module signal), defaulting to 1.0 and so
  absent when the circadian module is not loaded.

The conscious system never writes to the tissue. It can only raise the
``neural_drive`` channel, and the coupling term below is what turns that into
repair:

.. math::

    R_{total} = R_{base} \\cdot (1 + \\lambda \\cdot N)

:math:`\\lambda` is ``conscious.neural_drive_coupling`` — **invented**. It is the
entire mind-over-tissue claim, expressed as one number you can set to zero.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..core.events import EventKind
from ..core.params import ParameterSet
from .context import StepContext

__all__ = ["SubconsciousSystem", "RepairReport"]


@dataclass(frozen=True, slots=True)
class RepairReport:
    """What the subconscious system did this step."""

    base_rate: float
    total_rate: float
    applied: float
    growth_factor: float
    saturation: float
    inflammation_inhibition: float
    coupling_multiplier: float

    def as_dict(self) -> dict[str, float]:
        return {
            "base_rate": self.base_rate,
            "total_rate": self.total_rate,
            "applied": self.applied,
            "growth_factor": self.growth_factor,
            "saturation": self.saturation,
            "inflammation_inhibition": self.inflammation_inhibition,
            "coupling_multiplier": self.coupling_multiplier,
        }


class SubconsciousSystem:
    """Homeostatic repair. Runs every step whether or not anyone is paying attention."""

    name = "subconscious"

    def __init__(self, params: ParameterSet) -> None:
        self.params = params
        self._last: RepairReport | None = None

    # -- production --------------------------------------------------------
    def produce(self, ctx: StepContext) -> None:
        """Secrete growth factors and inflammatory mediators.

        Damage drives both: more damage means a louder repair signal. The
        direction of that relationship is not controversial; the gains are.
        """
        params = self.params
        dt = ctx.dt_hours
        damage = ctx.tissue.damage
        circadian = ctx.signal("circadian", 1.0)
        inflammation = ctx.signal("inflammation", params.value("module.inflammation.baseline"))

        gf_rate = (
            params.value("subconscious.growth_factor_production")
            * (1.0 + params.value("subconscious.damage_signal_gain") * damage)
            * circadian
        )
        ctx.field.add("growth_factor", gf_rate * dt)

        cytokine_rate = (
            params.value("subconscious.cytokine_production") * damage * (1.0 + inflammation)
        )
        ctx.field.add("cytokine", cytokine_rate * dt)

    # -- repair ------------------------------------------------------------
    def step(self, ctx: StepContext) -> RepairReport:
        params = self.params
        dt = ctx.dt_hours

        growth_factor = ctx.field.value("growth_factor")
        half_saturation = params.value("subconscious.gf_half_saturation")
        saturation = growth_factor / (growth_factor + half_saturation)

        inflammation = ctx.signal("inflammation", params.value("module.inflammation.baseline"))
        inhibition = inflammation * params.value("module.inflammation.repair_inhibition")
        circadian = ctx.signal("circadian", 1.0)

        base_rate = (
            params.value("subconscious.base_repair_rate")
            * saturation
            * max(0.0, 1.0 - inhibition)
            * circadian
        )

        neural_drive = ctx.field.value("neural_drive")
        coupling = params.value("conscious.neural_drive_coupling")
        multiplier = 1.0 + coupling * neural_drive
        total_rate = base_rate * multiplier

        applied = ctx.tissue.apply_repair(total_rate * dt)

        ctx.set_signal("subconscious.base_rate", base_rate)
        ctx.set_signal("subconscious.total_rate", total_rate)
        ctx.set_signal("subconscious.attention_multiplier", multiplier)
        # Repair that would not have happened without attention. Diagnostics only:
        # this is a decomposition of the model, not an empirical claim.
        ctx.set_signal("subconscious.attention_attributable_rate", total_rate - base_rate)

        report = RepairReport(
            base_rate=base_rate,
            total_rate=total_rate,
            applied=applied,
            growth_factor=growth_factor,
            saturation=saturation,
            inflammation_inhibition=inhibition,
            coupling_multiplier=multiplier,
        )
        self._last = report

        if applied > 0.0:
            ctx.bus.publish(
                ctx.t_hours,
                EventKind.TISSUE_REPAIR,
                self.name,
                applied=applied,
                base_rate=base_rate,
                total_rate=total_rate,
                multiplier=multiplier,
            )
        return report

    @property
    def last_report(self) -> RepairReport | None:
        return self._last

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": "autonomous homeostatic repair",
            "parameters": [
                "subconscious.base_repair_rate",
                "subconscious.growth_factor_production",
                "subconscious.damage_signal_gain",
                "subconscious.gf_half_saturation",
                "subconscious.cytokine_production",
                "conscious.neural_drive_coupling",
            ],
        }
