"""Replay adapter: a recorded session played back deterministically.

Replay is what makes a hardware bug reproducible. If a run misbehaved because a
sensor produced a bad stretch of data, the fix is only verifiable if that
stretch can be played back byte for byte — which means recording must be a
first-class feature rather than a debug print.

The file format is the same comma-separated shape used everywhere else, so a
recording can be produced by hand, by the console or by ``tcpdump``-style
tooling without a custom writer:

.. code-block:: text

    t_seconds,channel,value
    0.000,heart_rate,62.4
    0.000,hrv_index,0.55
    1.000,heart_rate,61.9

Replay is *not* wall-clock paced. It hands out samples as fast as the caller
asks, so a 4-hour recording replays in milliseconds and two replays of the same
file produce identical results.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping
from pathlib import Path
from typing import Any, ClassVar

from ..core.errors import DeviceError
from .base import (
    ChannelSpec,
    DeviceCapabilities,
    DeviceDriver,
    Sample,
    SampleQuality,
)

__all__ = ["ReplayDevice", "write_recording"]


class ReplayDevice(DeviceDriver):
    """Read-only playback of a recorded sample file."""

    kind: ClassVar[str] = "replay"

    def __init__(self, name: str = "replay.session", config: Mapping[str, Any] | None = None):
        super().__init__(name, config)
        raw_path = self.config.get("path")
        if not raw_path:
            raise DeviceError("the replay adapter needs a 'path' pointing at a recording")
        self._path = Path(str(raw_path))
        self._rows: list[tuple[float, str, float]] = []
        self._cursor = 0
        self._channels: tuple[ChannelSpec, ...] = ()
        self._loop = bool(self.config.get("loop", False))

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(channels=self._channels or (ChannelSpec(name="unknown"),))

    def open(self) -> None:
        if not self._path.is_file():
            raise DeviceError(f"recording not found: {self._path}")
        rows: list[tuple[float, str, float]] = []
        seen: list[str] = []
        with self._path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"t_seconds", "channel", "value"}
            if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
                raise DeviceError(
                    f"{self._path} must have columns {sorted(required)}; found {reader.fieldnames}"
                )
            for line_number, row in enumerate(reader, start=2):
                try:
                    t_seconds = float(row["t_seconds"])
                    value = float(row["value"])
                except (TypeError, ValueError) as exc:
                    raise DeviceError(
                        f"{self._path}:{line_number} has a non-numeric t_seconds or value"
                    ) from exc
                channel = str(row["channel"]).strip()
                if not channel:
                    raise DeviceError(f"{self._path}:{line_number} has an empty channel")
                if channel not in seen:
                    seen.append(channel)
                rows.append((t_seconds, channel, value))

        if not rows:
            raise DeviceError(f"{self._path} contains no samples")
        rows.sort(key=lambda item: (item[0], item[1]))
        self._rows = rows
        self._channels = tuple(ChannelSpec(name=name) for name in seen)
        self._cursor = 0
        self._open = True

    def close(self) -> None:
        self._open = False

    def read(self) -> tuple[Sample, ...]:
        self.require_open()
        if self._cursor >= len(self._rows):
            if not self._loop:
                return ()
            self._cursor = 0
        t_seconds, channel, value = self._rows[self._cursor]
        self._cursor += 1
        self.samples_read += 1
        return (
            Sample(
                device=self.name,
                channel=channel,
                value=value,
                t_seconds=t_seconds,
                quality=SampleQuality.OK if value == value else SampleQuality.INVALID,
            ),
        )

    @property
    def exhausted(self) -> bool:
        return self._cursor >= len(self._rows)

    @property
    def remaining(self) -> int:
        return max(0, len(self._rows) - self._cursor)


def write_recording(path: str | Path, samples: Any) -> int:
    """Write ``Sample`` objects to a replayable CSV file. Returns the row count."""
    location = Path(path)
    location.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with location.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["t_seconds", "channel", "value"])
        for sample in samples:
            writer.writerow([f"{sample.t_seconds:.6f}", sample.channel, f"{sample.value:.6f}"])
            count += 1
    return count
