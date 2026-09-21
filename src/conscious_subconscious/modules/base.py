"""The module contract.

A *module* is an optional, independently testable piece of physiology-ish
behaviour that runs once per step, before the systems. Modules are how the
model grows without the engine collecting special cases.

Contract
--------
A module may:

* read ``ctx.tissue``, ``ctx.field``, ``ctx.params``, ``ctx.signals`` and time;
* add production to mediator channels via ``ctx.field.add``;
* publish derived values into ``ctx.signals``.

A module must **not**:

* change ``ctx.tissue.integrity`` — only ``SubconsciousSystem.step`` may do that,
  so that the single path from mind to tissue stays inspectable;
* draw from an unnamed random stream (use ``ctx.rng.uniform("<module>.<what>", ...)``);
* depend on another module having already run. Ordering between modules is not
  part of the contract, precisely because that kind of coupling is invisible
  until it breaks.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from ..core.errors import ConfigurationError
from ..core.params import ParameterSet
from ..model.context import StepContext

__all__ = ["Module"]


class Module(ABC):
    """Base class for opt-in model behaviour."""

    #: Stable identifier used in scenario configs.
    name: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.name:
            raise ConfigurationError(f"{cls.__name__} must define a non-empty 'name'")

    def __init__(self, params: ParameterSet) -> None:
        self.params = params

    @abstractmethod
    def step(self, ctx: StepContext) -> None:
        """Advance one step. Must be side-effect free with respect to tissue."""

    @classmethod
    def parameter_keys(cls) -> tuple[str, ...]:
        """Parameter keys this module reads. Empty for modules that read none."""
        return ()

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parameters": list(self.parameter_keys()),
            "doc": (type(self).__doc__ or "").strip().splitlines()[0] if type(self).__doc__ else "",
        }

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"{type(self).__name__}(name={self.name!r})"
