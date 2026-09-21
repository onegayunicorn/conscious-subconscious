"""A synthetic device that needs no hardware.

This is the default adapter everywhere, and it is the reason the console, the
API and the pipelines can all be demonstrated on a machine with no sensors.
Each device owns its own seeded random stream, so two simulated devices in one
session do not perturb each other and adding a third does not change the first
two.

The generator is deliberately simple and *declared*: a resting mean, a slow
respiratory-sinus-arrhythmia-like oscillation, and bounded noise. It is a
cartoon of a heart-rate signal and it is labelled as one.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any, ClassVar

from ..core.rng import DeterministicRng
from .base import (
    ChannelSpec,
    DeviceCapabilities,
    DeviceDriver,
    Sample,
    SampleQuality,
)

__all__ = ["SimulatedCardioDevice", "DEFAULT_CHANNELS"]

DEFAULT_CHANNELS: tuple[ChannelSpec, ...] = (
    ChannelSpec(name="heart_rate", unit="bpm", nominal_rate_hz=1.0, minimum=25.0, maximum=220.0),
    ChannelSpec(name="hrv_index", unit="ratio", nominal_rate_hz=1.0, minimum=0.0, maximum=1.0),
)


class SimulatedCardioDevice(DeviceDriver):
    """A deterministic synthetic heart-rate and HRV-index source."""

    kind: ClassVar[str] = "simulated"

    def __init__(self, name: str = "sim.cardiovascular", config: Mapping[str, Any] | None = None):
        super().__init__(name, config)
        self._rate_hz = float(self.config.get("sample_rate_hz", 1.0))
        self._mean_bpm = float(self.config.get("mean_bpm", 62.0))
        self._rsa_amplitude = float(self.config.get("rsa_amplitude_bpm", 4.0))
        self._breath_period_s = float(self.config.get("breath_period_seconds", 5.0))
        self._noise_bpm = float(self.config.get("noise_bpm", 1.5))
        self._hrv_mean = float(self.config.get("hrv_index_mean", 0.55))
        self._elapsed_s = 0.0
        if self._rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        self._rng = DeterministicRng(int(self.config.get("seed", 20260921)))
        self._next_sample_at = 0.0

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            channels=DEFAULT_CHANNELS,
            sample_rate_hz=self._rate_hz,
            bidirectional=False,
        )

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def read(self) -> tuple[Sample, ...]:
        """Return one sample per elapsed interval, or an empty tuple.

        Time advances by the read interval regardless of how often ``read`` is
        called, so polling faster does not fabricate data.
        """
        self.require_open()
        interval = 1.0 / self._rate_hz
        produced: list[Sample] = []

        # At most a bounded batch, so a long gap cannot produce an unbounded list.
        while self._elapsed_s + 1e-12 >= self._next_sample_at and len(produced) < 64:
            t = self._next_sample_at
            rsa = self._rsa_amplitude * math.sin(2.0 * math.pi * t / self._breath_period_s)
            noise = (
                self._rng.normal("simulated.bpm_noise", 0.0, self._noise_bpm)
                if self._noise_bpm > 0
                else 0.0
            )
            bpm = self._mean_bpm + rsa + noise
            quality = SampleQuality.SUSPECT if not 25.0 <= bpm <= 220.0 else SampleQuality.OK
            produced.append(
                Sample(
                    device=self.name,
                    channel="heart_rate",
                    value=round(bpm, 6),
                    t_seconds=round(t, 6),
                    unit="bpm",
                    quality=quality,
                )
            )
            index = self._hrv_mean + 0.1 * math.sin(2.0 * math.pi * t / 60.0)
            produced.append(
                Sample(
                    device=self.name,
                    channel="hrv_index",
                    value=round(max(0.0, min(1.0, index)), 6),
                    t_seconds=round(t, 6),
                    unit="ratio",
                )
            )
            self._next_sample_at += interval
            self.samples_read += 1

        self._elapsed_s += interval
        return tuple(produced)
