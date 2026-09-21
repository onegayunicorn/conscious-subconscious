"""The damaged region being modelled.

A tissue is a single scalar ``integrity`` plus a ceiling. That is a severe
abstraction, and it is worth being explicit about what it is *not*: there is no
geometry, no cell population, no fibre orientation, no scar formation. The
source document used the same abstraction, so keeping it makes the port honest,
but no result here should be read as a statement about real tissue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.errors import ConfigurationError

__all__ = ["Tissue"]

_REPAIR_EPSILON = 1e-12


@dataclass(slots=True)
class Tissue:
    """A scalar model of a damaged region."""

    name: str = "muscle tissue"
    integrity: float = 0.20
    max_integrity: float = 1.0
    #: Cumulative repair actually applied, in integrity units.
    total_repair: float = field(default=0.0, init=False)
    #: Cumulative repair that was discarded because integrity was already at the ceiling.
    wasted_repair: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if self.max_integrity <= 0:
            raise ConfigurationError("max_integrity must be positive")
        if not 0.0 <= self.integrity <= self.max_integrity:
            raise ConfigurationError(
                f"integrity {self.integrity} must lie in [0, {self.max_integrity}]"
            )
        if not self.name:
            raise ConfigurationError("tissue name must be non-empty")

    @property
    def damage(self) -> float:
        """Remaining damage as a fraction of the ceiling, in ``[0, 1]``."""
        return max(0.0, (self.max_integrity - self.integrity) / self.max_integrity)

    @property
    def is_healed(self) -> bool:
        return self.integrity >= self.max_integrity - _REPAIR_EPSILON

    def apply_repair(self, amount: float) -> float:
        """Add ``amount`` of integrity; returns how much was actually applied.

        Repair that overshoots the ceiling is counted in ``wasted_repair``
        rather than dropped, so a comparison between two scenarios cannot
        pretend an overshooting rule was more efficient than it was.
        """
        if amount < 0:
            raise ValueError(f"repair amount must be non-negative, got {amount}")
        headroom = self.max_integrity - self.integrity
        if headroom <= 0.0:
            self.wasted_repair += amount
            return 0.0
        applied = min(amount, headroom)
        self.integrity += applied
        self.total_repair += applied
        self.wasted_repair += amount - applied
        return applied

    def apply_damage(self, amount: float) -> float:
        """Reduce integrity; returns how much damage was actually applied."""
        if amount < 0:
            raise ValueError(f"damage amount must be non-negative, got {amount}")
        applied = min(amount, self.integrity)
        self.integrity -= applied
        return applied

    def recovered_fraction(self) -> float:
        """Fraction of the *original* damage that has been repaired, in ``[0, 1]``."""
        return max(0.0, min(1.0, self.total_repair / self.max_integrity))

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "integrity": round(self.integrity, 12),
            "damage": round(self.damage, 12),
            "max_integrity": self.max_integrity,
            "total_repair": round(self.total_repair, 12),
            "wasted_repair": round(self.wasted_repair, 12),
            "is_healed": self.is_healed,
        }
