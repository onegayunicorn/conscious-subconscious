"""Lab Streaming Layer adapter.

LSL is the lingua franca of lab hardware: EEG amplifiers, physiological
recording rigs and experiment-control software all publish streams onto the same
local network, and LSL handles the clock synchronisation that is genuinely hard
to do yourself.

The adapter resolves a stream by name, then pulls whatever is available each
``read``. It never blocks for a full sample, because a simulation step that
stalls on a hardware clock stops being reproducible.

``pylsl`` is imported lazily: this module imports cleanly without it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar

from ..core.errors import DeviceError, DeviceUnavailable
from .base import (
    ChannelSpec,
    DeviceCapabilities,
    DeviceDriver,
    Sample,
    SampleQuality,
)

__all__ = ["LslInletDevice", "MAX_CHUNK"]

#: Ceiling on samples pulled per call, so a long stall cannot stall further.
MAX_CHUNK = 512


class LslInletDevice(DeviceDriver):
    """Read-only inlet for one LSL stream."""

    kind: ClassVar[str] = "lsl"

    def __init__(self, name: str = "lsl.inlet", config: Mapping[str, Any] | None = None):
        super().__init__(name, config)
        self._stream_name = self.config.get("stream_name") or "conscious-subconscious"
        self._channel_labels: list[str] = list(self.config.get("channel_labels", []) or [])
        self._inlet: Any = None
        self._delta = 0.0
        self._start_time = 0.0

    @property
    def capabilities(self) -> DeviceCapabilities:
        labels = self._channel_labels or ["channel_0"]
        return DeviceCapabilities(
            channels=tuple(ChannelSpec(name=label, nominal_rate_hz=0.0) for label in labels),
            sample_rate_hz=0.0,
            bidirectional=False,
        )

    def open(self) -> None:
        try:
            from pylsl import StreamInlet, resolve_byprop  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - depends on the machine
            raise DeviceUnavailable(
                "the LSL adapter needs pylsl: pip install 'conscious-subconscious[devices]'"
            ) from exc

        try:
            streams = resolve_byprop("name", self._stream_name, timeout=2.0)
        except Exception as exc:  # pragma: no cover - network dependent
            raise DeviceUnavailable(f"LSL resolution failed: {exc}") from exc
        if not streams:
            raise DeviceUnavailable(
                f"no LSL stream named {self._stream_name!r} found on this network"
            )

        try:
            self._inlet = StreamInlet(streams[0], max_buflen=360)
            info = self._inlet.info()
            if not self._channel_labels:
                channel_count = int(info.channel_count())
                self._channel_labels = [f"channel_{i}" for i in range(channel_count)]
            self._delta = float(self._inlet.info().nominal_srate() or 0.0)
            self._start_time = float(self._inlet.time_correction())
        except Exception as exc:  # pragma: no cover - hardware dependent
            raise DeviceError(f"cannot open LSL inlet: {exc}") from exc
        self._open = True

    def close(self) -> None:
        if self._inlet is not None:
            try:
                self._inlet.close_stream()
            except Exception:  # pragma: no cover - best effort
                pass
            finally:
                self._inlet = None
        self._open = False

    def read(self) -> tuple[Sample, ...]:
        self.require_open()
        produced: list[Sample] = []
        for _ in range(MAX_CHUNK):
            try:
                chunk, timestamp = self._inlet.pull_sample(timeout=0.0)
            except Exception as exc:  # pragma: no cover - hardware dependent
                raise DeviceError(f"LSL pull failed: {exc}") from exc
            if chunk is None:
                break
            t_seconds = float(timestamp) if timestamp else 0.0
            for index, value in enumerate(chunk):
                label = (
                    self._channel_labels[index]
                    if index < len(self._channel_labels)
                    else f"channel_{index}"
                )
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    numeric = float("nan")
                produced.append(
                    Sample(
                        device=self.name,
                        channel=label,
                        value=numeric,
                        t_seconds=t_seconds,
                        quality=(SampleQuality.INVALID if numeric != numeric else SampleQuality.OK),
                    )
                )
            self.samples_read += 1
        return tuple(produced)
