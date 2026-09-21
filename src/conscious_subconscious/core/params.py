"""Numeric parameters, each carrying its own provenance.

The original design document this project grew out of contained magic numbers
(`healing_rate = 0.5`, a `1.0–3.0` random "conscious boost") with no source.
Rather than quietly replacing them with nicer-looking numbers, the sandbox
keeps them and labels where they came from.

Grades
------
measured
    Produced by a measurement inside this project.
literature
    Supported by a cited source; see ``research/literature-review.md``.
assumed
    Chosen for convenience. No empirical support. A free knob.
invented
    Lifted from the source design document. No empirical support at all.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .errors import ParameterError

__all__ = ["Provenance", "Parameter", "ParameterSet"]


class Provenance(str, Enum):
    """Where a number came from."""

    MEASURED = "measured"
    LITERATURE = "literature"
    ASSUMED = "assumed"
    INVENTED = "invented"

    @property
    def is_supported(self) -> bool:
        """True only for values with real backing (measured or literature)."""
        return self in (Provenance.MEASURED, Provenance.LITERATURE)

    @property
    def rationale(self) -> str:
        """One-line, human-readable description used in reports."""
        return _RATIONALE[self]


_RATIONALE: dict[Provenance, str] = {
    Provenance.MEASURED: "measured within this project",
    Provenance.LITERATURE: "supported by cited literature (see research/)",
    Provenance.ASSUMED: "chosen for convenience — no empirical support",
    Provenance.INVENTED: "taken from the source design document — no empirical support",
}


@dataclass(frozen=True, slots=True)
class Parameter:
    """A single named number plus the story of where it came from."""

    key: str
    value: float
    unit: str
    provenance: Provenance
    note: str = ""
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not self.key or "." not in self.key:
            raise ParameterError(f"parameter key must be dotted and non-empty, got {self.key!r}")
        if self.minimum is not None and self.maximum is not None:
            if self.minimum > self.maximum:
                raise ParameterError(
                    f"{self.key}: minimum {self.minimum} exceeds maximum {self.maximum}"
                )
        if self.minimum is not None and self.value < self.minimum:
            raise ParameterError(f"{self.key}: value {self.value} is below minimum {self.minimum}")
        if self.maximum is not None and self.value > self.maximum:
            raise ParameterError(f"{self.key}: value {self.value} is above maximum {self.maximum}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "provenance": self.provenance.value,
            "supported": self.provenance.is_supported,
            "rationale": self.provenance.rationale,
            "note": self.note,
            "minimum": self.minimum,
            "maximum": self.maximum,
        }


class ParameterSet:
    """An immutable-by-convention collection of :class:`Parameter` objects."""

    __slots__ = ("_items",)

    def __init__(self, parameters: Iterable[Parameter]) -> None:
        items: dict[str, Parameter] = {}
        for parameter in parameters:
            if parameter.key in items:
                raise ParameterError(f"duplicate parameter key: {parameter.key!r}")
            items[parameter.key] = parameter
        if not items:
            raise ParameterError("a ParameterSet must contain at least one parameter")
        self._items = items

    # -- container protocol -------------------------------------------------
    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Parameter]:
        return iter(self.sorted())

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and key in self._items

    def __getitem__(self, key: str) -> Parameter:
        try:
            return self._items[key]
        except KeyError as exc:  # pragma: no cover - message path
            raise ParameterError(f"unknown parameter: {key!r}") from exc

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ParameterSet):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def sorted(self) -> tuple[Parameter, ...]:
        """Parameters in stable key order (makes reports diff-friendly)."""
        return tuple(self._items[key] for key in sorted(self._items))

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._items))

    # -- access ------------------------------------------------------------
    def value(self, key: str) -> float:
        """Return the float value of ``key``."""
        return self[key].value

    def parameter(self, key: str) -> Parameter:
        return self[key]

    def many(self, keys: Iterable[str]) -> dict[str, float]:
        return {key: self.value(key) for key in keys}

    # -- derivation --------------------------------------------------------
    def with_overrides(self, overrides: Mapping[str, float]) -> ParameterSet:
        """Return a new set with ``overrides`` applied.

        An overridden value is no longer traceable to its original source, so
        the override is recorded honestly with ``assumed`` provenance and a
        note naming the previous value. Silently keeping the old, flattering
        tag would be the exact dishonesty this module exists to prevent.
        """
        unknown = sorted(set(overrides) - set(self._items))
        if unknown:
            raise ParameterError("cannot override unknown parameter(s): " + ", ".join(unknown))
        merged: list[Parameter] = []
        for key in sorted(self._items):
            original = self._items[key]
            if key not in overrides:
                merged.append(original)
                continue
            new_value = float(overrides[key])
            replaced = Parameter(
                key=original.key,
                value=new_value,
                unit=original.unit,
                provenance=Provenance.ASSUMED,
                note=(
                    f"runtime override (was {original.value:g} "
                    f"{original.unit}, provenance {original.provenance.value}); "
                    "overridden values are always treated as unsupported"
                ),
                minimum=original.minimum,
                maximum=original.maximum,
            )
            merged.append(replaced)
        return ParameterSet(merged)

    # -- reporting ---------------------------------------------------------
    def unsupported(self) -> tuple[Parameter, ...]:
        """Parameters with no empirical backing, in key order."""
        return tuple(p for p in self.sorted() if not p.provenance.is_supported)

    def supported(self) -> tuple[Parameter, ...]:
        return tuple(p for p in self.sorted() if p.provenance.is_supported)

    def provenance_table(self) -> list[dict[str, Any]]:
        return [p.as_dict() for p in self.sorted()]

    def support_summary(self) -> dict[str, Any]:
        total = len(self._items)
        unsupported = len(self.unsupported())
        return {
            "total": total,
            "supported": total - unsupported,
            "unsupported": unsupported,
            "unsupported_fraction": (unsupported / total) if total else 0.0,
        }

    def to_dict(self) -> dict[str, Any]:
        return {p.key: p.value for p in self.sorted()}

    def digest(self) -> str:
        """Stable content hash used to prove two runs used identical numbers."""
        canonical = json.dumps(
            [p.as_dict() for p in self.sorted()],
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
