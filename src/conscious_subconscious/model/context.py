"""Per-step state shared by every subsystem and module.

Passing one context object (rather than six positional arguments) keeps
signatures stable as the model grows, and gives modules a documented place to
publish derived quantities: the ``signals`` map.

Convention
----------
A *channel* lives on :class:`~conscious_subconscious.model.mediators.MediatorField`
and is a physical-ish quantity with units and decay. A *signal* lives in
``ctx.signals`` and is a dimensionless value that one component computes and
another consumes (inflammation level, parasympathetic tone, circadian factor).
Signals are recomputed every step; nothing persists in them by accident.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from ..core.events import EventBus
from ..core.params import ParameterSet
from ..core.rng import DeterministicRng
from .mediators import MediatorField
from .tissue import Tissue

__all__ = ["StepContext"]


@dataclass(slots=True)
class StepContext:
    """Everything a subsystem needs for one step, and nothing more."""

    t_hours: float
    dt_hours: float
    tissue: Tissue
    field: MediatorField
    params: ParameterSet
    bus: EventBus
    rng: DeterministicRng
    # Qualified deliberately: this class has an attribute called `field`, which
    # would otherwise shadow the dataclasses helper of the same name.
    signals: dict[str, float] = dataclasses.field(default_factory=dict)

    def signal(self, name: str, default: float = 0.0) -> float:
        """Read a derived signal, falling back to ``default`` when absent."""
        return self.signals.get(name, default)

    def set_signal(self, name: str, value: float) -> None:
        self.signals[name] = value

    def require_signal(self, name: str) -> float:
        """Read a signal that the module contract says must exist."""
        try:
            return self.signals[name]
        except KeyError as exc:
            raise KeyError(f"required signal {name!r} was not published this step") from exc
