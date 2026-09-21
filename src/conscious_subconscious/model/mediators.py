"""The mediator field: the modelled signalling layer between mind and tissue.

This is the only path by which the conscious system can reach the tissue. It
cannot "heal" anything directly — it can only add to a signalling channel, and
the subconscious repair rule decides what, if anything, that does. Keeping the
coupling explicit is what makes the central assumption inspectable.

Channels are **leaky integrators**: production is added, then each channel
decays exponentially. The source document this project grew out of had no
decay, so its accumulator could only grow — a modelling bug worth naming.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

__all__ = ["CHANNELS", "MediatorField"]

#: Channel name -> what it represents. Keep in sync with ``parameters.py``.
CHANNELS: Mapping[str, str] = {
    "atp": "local energy availability",
    "cytokine": "inflammatory mediator concentration",
    "growth_factor": "repair-promoting growth signalling",
    "perfusion": "local blood flow / delivery capacity",
    "neural_drive": "efferent neural activity attributed to attention",
}


class MediatorField:
    """Named scalar channels with production, exponential decay and auditing."""

    __slots__ = ("_values", "_decay", "_produced", "_dissipated")

    def __init__(
        self,
        decay_per_hour: Mapping[str, float],
        initial: Mapping[str, float] | None = None,
    ) -> None:
        unknown = set(decay_per_hour) - set(CHANNELS)
        if unknown:
            raise ValueError(f"unknown mediator channel(s): {sorted(unknown)}")
        missing = set(CHANNELS) - set(decay_per_hour)
        if missing:
            raise ValueError(f"missing decay constant for channel(s): {sorted(missing)}")
        for channel, rate in decay_per_hour.items():
            if rate < 0:
                raise ValueError(f"decay for {channel!r} must be non-negative")
        self._decay: dict[str, float] = {k: float(v) for k, v in decay_per_hour.items()}
        self._values: dict[str, float] = dict.fromkeys(CHANNELS, 0.0)
        if initial:
            for channel, value in initial.items():
                self.set(channel, value)
        self._produced: dict[str, float] = dict.fromkeys(CHANNELS, 0.0)
        self._dissipated: dict[str, float] = dict.fromkeys(CHANNELS, 0.0)

    # -- access ------------------------------------------------------------
    def value(self, channel: str) -> float:
        try:
            return self._values[channel]
        except KeyError as exc:
            raise ValueError(f"unknown mediator channel: {channel!r}") from exc

    def set(self, channel: str, value: float) -> float:
        """Overwrite a channel; negative clamps to zero. Returns the new value."""
        self.value(channel)  # validates the name
        clamped = max(0.0, float(value))
        self._values[channel] = clamped
        return clamped

    def add(self, channel: str, amount: float) -> float:
        """Add production to a channel. Returns the new value.

        Negative production is rejected rather than silently absorbed, because
        a channel that can go negative usually means a sign error upstream.
        """
        if amount < 0:
            raise ValueError(f"production for {channel!r} must be non-negative, got {amount}")
        self.value(channel)
        self._values[channel] += float(amount)
        self._produced[channel] += float(amount)
        return self._values[channel]

    # -- dynamics ----------------------------------------------------------
    def step(self, dt_hours: float) -> dict[str, float]:
        """Apply exponential decay for ``dt_hours`` and return the new values."""
        if dt_hours < 0:
            raise ValueError("dt_hours must be non-negative")
        for channel, rate in self._decay.items():
            before = self._values[channel]
            if before == 0.0:
                continue
            after = before * math.exp(-rate * dt_hours)
            # Guard against underflow turning a live channel into a dead one.
            if after < 1e-12:
                after = 0.0
            self._dissipated[channel] += before - after
            self._values[channel] = after
        return dict(self._values)

    # -- reporting ---------------------------------------------------------
    def snapshot(self) -> dict[str, float]:
        return dict(self._values)

    def audit(self) -> dict[str, dict[str, float]]:
        """Cumulative production and dissipation per channel.

        Useful as a self-check: a channel whose production is zero yet whose
        value is non-zero indicates a bookkeeping error.
        """
        return {
            channel: {
                "current": self._values[channel],
                "produced": self._produced[channel],
                "dissipated": self._dissipated[channel],
            }
            for channel in CHANNELS
        }

    def reset(self) -> None:
        for channel in CHANNELS:
            self._values[channel] = 0.0
            self._produced[channel] = 0.0
            self._dissipated[channel] = 0.0

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        rendered = ", ".join(f"{k}={v:.4g}" for k, v in self._values.items())
        return f"MediatorField({rendered})"
