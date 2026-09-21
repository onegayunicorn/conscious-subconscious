"""Time-series recording and summary statistics.

Metrics are defined once, here, and reused by the CLI report, the JSON export
and the API. Two definitions matter more than they look:

* ``time_to_half_repair`` is the first time the *recovered fraction of the
  original damage* reaches 0.5 — not the time integrity crosses 0.5. Those are
  different numbers whenever the initial damage differs, and using the sloppy
  one makes scenarios with different starting injuries incomparable.
* ``attention_attributable_repair`` is a decomposition of the model, not a
  biological measurement: it is the repair the coupling term added on top of
  the baseline rate. It says nothing about real tissue.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

__all__ = ["Sample", "MetricsRecorder", "SUMMARY_KEYS"]


@dataclass(frozen=True, slots=True)
class Sample:
    """One recorded instant of the run."""

    t_hours: float
    integrity: float
    damage: float
    attention: float
    focused: bool
    fatigued: bool
    perceived_progress: float
    mediators: Mapping[str, float]
    rates: Mapping[str, float]

    def as_dict(self, *, round_to: int = 9) -> dict[str, Any]:
        return {
            "t_hours": round(self.t_hours, round_to),
            "integrity": round(self.integrity, round_to),
            "damage": round(self.damage, round_to),
            "attention": round(self.attention, round_to),
            "focused": self.focused,
            "fatigued": self.fatigued,
            "perceived_progress": round(self.perceived_progress, round_to),
            "mediators": {k: round(v, round_to) for k, v in sorted(self.mediators.items())},
            "rates": {k: round(v, round_to) for k, v in sorted(self.rates.items())},
        }


#: Keys always present in :meth:`MetricsRecorder.summary`.
SUMMARY_KEYS: tuple[str, ...] = (
    "samples",
    "final_integrity",
    "time_to_50pct_repair_hours",
    "time_to_full_repair_hours",
    "area_under_damage_integrity_hours",
    "mean_integrity",
    "peak_neural_drive",
    "peak_growth_factor",
    "attention_spent",
    "focus_hours",
    "min_attention",
    "fatigue_episodes",
    "total_repair",
    "attention_attributable_repair",
    "attention_attributable_fraction",
    "final_perception_gap",
)


class MetricsRecorder:
    """Accumulates samples and derives comparable summary statistics."""

    __slots__ = (
        "_samples",
        "_initial_integrity",
        "_max_integrity",
        "_dt_hours",
        "_prev_integrity",
        "_area_under_damage",
        "_integrity_sum",
        "_attention_spent",
        "_fatigue_episodes",
    )

    def __init__(
        self,
        initial_integrity: float,
        max_integrity: float = 1.0,
        dt_hours: float = 0.05,
    ) -> None:
        if max_integrity <= initial_integrity:
            raise ValueError("max_integrity must exceed initial_integrity")
        self._samples: list[Sample] = []
        self._initial_integrity = initial_integrity
        self._max_integrity = max_integrity
        self._dt_hours = dt_hours
        self._prev_integrity = initial_integrity
        self._area_under_damage = 0.0
        self._integrity_sum = 0.0
        self._attention_spent = 0.0
        self._fatigue_episodes = 0

    # -- ingestion ---------------------------------------------------------
    def record(
        self,
        sample: Sample,
        *,
        attention_spent_delta: float = 0.0,
        fatigue_episode: bool = False,
    ) -> None:
        """Append a sample and fold it into the running integrals."""
        if sample.t_hours < 0:
            raise ValueError("t_hours must be non-negative")
        if attention_spent_delta < 0:
            raise ValueError("attention_spent_delta must be non-negative")

        # Trapezoid rule over remaining damage.
        damage_prev = max(0.0, self._max_integrity - self._prev_integrity) / self._max_integrity
        damage_now = sample.damage
        self._area_under_damage += 0.5 * (damage_prev + damage_now) * self._dt_hours
        self._prev_integrity = sample.integrity
        self._integrity_sum += sample.integrity
        self._attention_spent += attention_spent_delta
        if fatigue_episode:
            self._fatigue_episodes += 1
        self._samples.append(sample)

    # -- access ------------------------------------------------------------
    @property
    def samples(self) -> tuple[Sample, ...]:
        return tuple(self._samples)

    def __len__(self) -> int:
        return len(self._samples)

    @property
    def area_under_damage(self) -> float:
        return self._area_under_damage

    # -- derived -----------------------------------------------------------
    def threshold_time(self, recovered_fraction: float) -> float | None:
        """First time the recovered fraction of the original damage reaches ``recovered_fraction``.

        Returns ``None`` when the run never gets there — which is information,
        not a failure, and must not be silently reported as 0 or infinity.
        """
        if not 0.0 <= recovered_fraction <= 1.0:
            raise ValueError("recovered_fraction must lie in [0, 1]")
        span = self._max_integrity - self._initial_integrity
        if span <= 0:
            return 0.0
        target = self._initial_integrity + recovered_fraction * span
        for sample in self._samples:
            if sample.integrity >= target:
                return round(sample.t_hours, 9)
        return None

    def summary(self) -> dict[str, Any]:
        """Comparable statistics for the completed run."""
        if not self._samples:
            raise ValueError("cannot summarise a run with no samples")

        last = self._samples[-1]
        peak_neural_drive = max(s.mediators.get("neural_drive", 0.0) for s in self._samples)
        peak_growth_factor = max(s.mediators.get("growth_factor", 0.0) for s in self._samples)
        min_attention = min(s.attention for s in self._samples)
        focus_hours = sum(self._dt_hours for s in self._samples if s.focused)

        total_repair = sum(
            s.rates.get("subconscious.total_rate", 0.0) * self._dt_hours for s in self._samples
        )
        attributable = sum(
            s.rates.get("subconscious.attention_attributable_rate", 0.0) * self._dt_hours
            for s in self._samples
        )
        fraction = (attributable / total_repair) if total_repair > 0 else 0.0

        return {
            "samples": len(self._samples),
            "final_integrity": round(last.integrity, 9),
            "time_to_50pct_repair_hours": self.threshold_time(0.5),
            "time_to_full_repair_hours": self.threshold_time(1.0),
            "area_under_damage_integrity_hours": round(self._area_under_damage, 9),
            "mean_integrity": round(self._integrity_sum / len(self._samples), 9),
            "peak_neural_drive": round(peak_neural_drive, 9),
            "peak_growth_factor": round(peak_growth_factor, 9),
            "attention_spent": round(self._attention_spent, 9),
            "focus_hours": round(focus_hours, 9),
            "min_attention": round(min_attention, 9),
            "fatigue_episodes": self._fatigue_episodes,
            "total_repair": round(total_repair, 9),
            "attention_attributable_repair": round(attributable, 9),
            "attention_attributable_fraction": round(fraction, 9),
            "final_perception_gap": round(last.perceived_progress - last.integrity, 9),
        }
