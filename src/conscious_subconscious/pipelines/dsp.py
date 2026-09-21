"""Small signal-processing helpers, with no numpy dependency.

Everything here is pure Python over sequences. That is a deliberate choice: the
core package must install and run with no third-party packages, and the volumes
involved (a few thousand samples per session) do not justify a numerical
dependency. The ``science`` extra exists for heavier analysis, not for this.

Every function returns plain Python types and never mutates its input.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from ..core.errors import PipelineError
from ..devices.ble_heart_rate import rmssd_ms

__all__ = [
    "mean",
    "stdev",
    "zscore",
    "moving_average",
    "resample_linear",
    "band_power",
    "rmssd_ms",
    "channel_series",
]


def mean(values: Sequence[float]) -> float:
    if not values:
        raise PipelineError("mean of an empty sequence is undefined")
    return sum(values) / len(values)


def stdev(values: Sequence[float], *, sample: bool = True) -> float:
    """Standard deviation. ``sample=True`` uses the n-1 denominator."""
    if len(values) < 2:
        return 0.0
    mu = mean(values)
    divisor = len(values) - 1 if sample else len(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / divisor)


def zscore(values: Sequence[float]) -> list[float]:
    """Zero-mean, unit-variance copy. A constant series maps to all zeros.

    Returning zeros rather than raising is intentional: a flat channel is a real
    observation (a disconnected sensor), and downstream code should see it as
    "no information" rather than crash on it.
    """
    if not values:
        return []
    mu = mean(values)
    sigma = stdev(values, sample=False)
    if sigma == 0.0:
        return [0.0 for _ in values]
    return [(value - mu) / sigma for value in values]


def moving_average(values: Sequence[float], window: int) -> list[float]:
    """Centred-free trailing moving average of the given window size.

    The first ``window - 1`` outputs use the shorter prefix available rather
    than being dropped or back-filled, so the output length always equals the
    input length. A back-filled start would invent data at the beginning of a
    recording, which is exactly where sensor artefacts live.
    """
    if window < 1:
        raise PipelineError("window must be at least 1")
    out: list[float] = []
    running = 0.0
    for index, value in enumerate(values):
        running += value
        if index >= window:
            running -= values[index - window]
        out.append(running / min(index + 1, window))
    return out


def resample_linear(
    times: Sequence[float],
    values: Sequence[float],
    target_times: Sequence[float],
) -> list[float]:
    """Linear interpolation onto ``target_times``.

    ``times`` must be sorted and have no duplicate timestamps; duplicate
    timestamps make "the value at t" ambiguous, and picking one silently is how
    a de-duplication bug becomes a plausible-looking trend.
    """
    if len(times) != len(values):
        raise PipelineError("times and values must have the same length")
    if len(times) < 2:
        raise PipelineError("need at least two points to resample")
    for earlier, later in zip(times, times[1:], strict=False):
        if later < earlier:
            raise PipelineError("times must be sorted ascending")
        if later == earlier:
            raise PipelineError(f"duplicate timestamp {earlier!r}; resampling would be ambiguous")

    out: list[float] = []
    cursor = 0
    for target in target_times:
        if target <= times[0]:
            out.append(values[0])
            continue
        if target >= times[-1]:
            out.append(values[-1])
            continue
        while cursor + 1 < len(times) and times[cursor + 1] < target:
            cursor += 1
        t0, t1 = times[cursor], times[cursor + 1]
        v0, v1 = values[cursor], values[cursor + 1]
        span = t1 - t0
        ratio = 0.0 if span == 0 else (target - t0) / span
        out.append(v0 + (v1 - v0) * ratio)
    return out


def band_power(
    values: Sequence[float],
    *,
    sample_rate_hz: float,
    low_hz: float,
    high_hz: float,
) -> float:
    """Power in a frequency band, by direct DFT over that band only.

    A full FFT would be faster and would also pull in a dependency for a job
    that is usually a handful of bins on a few thousand samples. The direct sum
    also makes the frequency resolution explicit rather than hiding it inside a
    library's windowing defaults.

    Returns the summed squared magnitude, normalised by the number of samples.
    """
    if sample_rate_hz <= 0:
        raise PipelineError("sample_rate_hz must be positive")
    if low_hz < 0 or high_hz <= low_hz:
        raise PipelineError("require 0 <= low_hz < high_hz")
    if high_hz > sample_rate_hz / 2:
        raise PipelineError(f"high_hz {high_hz} exceeds the Nyquist frequency {sample_rate_hz / 2}")
    count = len(values)
    if count < 2:
        return 0.0

    series = zscore(values)
    total = 0.0
    # Frequency resolution is one bin per (count / sample_rate) seconds.
    resolution = sample_rate_hz / count
    first = max(1, int(math.floor(low_hz / resolution)))
    last = int(math.ceil(high_hz / resolution))
    for bin_index in range(first, last + 1):
        omega = 2.0 * math.pi * bin_index / count
        real = 0.0
        imaginary = 0.0
        for index, value in enumerate(series):
            angle = omega * index
            real += value * math.cos(angle)
            imaginary -= value * math.sin(angle)
        total += real * real + imaginary * imaginary
    return total / count


def channel_series(
    rows: Iterable[tuple[float, str, float]], channel: str
) -> tuple[list[float], list[float]]:
    """Extract ``(times, values)`` for one channel from ``(t, channel, value)`` rows."""
    times: list[float] = []
    values: list[float] = []
    for t_seconds, name, value in rows:
        if name == channel:
            times.append(t_seconds)
            values.append(value)
    return times, values
