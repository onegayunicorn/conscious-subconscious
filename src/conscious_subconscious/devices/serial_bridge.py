"""Serial adapter for a microcontroller bridge.

The wire format is intentionally boring and self-describing so that firmware in
``hardware/firmware/`` can emit it with ``Serial.println`` and no JSON library:

.. code-block:: text

    CS,<channel>,<value>
    CS,<channel>,<value>,<quality>

Lines that do not start with ``CS,`` are treated as device chatter and ignored —
firmware that prints a boot banner should not crash the host. A ``CS,`` line
that is malformed *is* an error, because at that point the device is speaking
the protocol and speaking it wrongly.

``pyserial`` is imported lazily, so this module imports cleanly on a machine
without it and fails with a useful message only when someone actually opens a
port.
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

__all__ = ["PREFIX", "parse_line", "SerialBridgeDevice"]

PREFIX = "CS"
MAX_LINE_BYTES = 512

CHANNELS: tuple[ChannelSpec, ...] = (
    ChannelSpec(name="heart_rate", unit="bpm", nominal_rate_hz=1.0, minimum=25.0, maximum=220.0),
    ChannelSpec(name="eda", unit="microsiemens", nominal_rate_hz=4.0, minimum=0.0),
    ChannelSpec(name="skin_temperature", unit="degC", nominal_rate_hz=1.0),
    ChannelSpec(name="hrv_index", unit="ratio", nominal_rate_hz=0.2, minimum=0.0, maximum=1.0),
)


def parse_line(line: str, *, device: str, t_seconds: float) -> Sample | None:
    """Parse one serial line.

    Returns ``None`` for lines that are not protocol lines. Raises
    :class:`DeviceError` for lines that are protocol lines but malformed.
    """
    text = line.strip()
    if not text or not text.startswith(f"{PREFIX},"):
        return None

    parts = [part.strip() for part in text.split(",")]
    if len(parts) not in (3, 4):
        raise DeviceError(
            f"malformed {PREFIX} line with {len(parts)} fields (expected 3 or 4): {text!r}"
        )
    channel = parts[1]
    if not channel:
        raise DeviceError(f"empty channel in line {text!r}")
    try:
        value = float(parts[2])
    except ValueError as exc:
        raise DeviceError(f"non-numeric value in line {text!r}") from exc
    if value != value:  # NaN
        raise DeviceError(f"NaN value in line {text!r}")

    quality = SampleQuality.OK
    if len(parts) == 4:
        try:
            quality = SampleQuality(parts[3])
        except ValueError as exc:
            raise DeviceError(
                f"unknown quality {parts[3]!r}; expected one of "
                f"{', '.join(q.value for q in SampleQuality)}"
            ) from exc

    known = {spec.name for spec in CHANNELS}
    if channel not in known:
        # Unknown channels are marked invalid rather than rejected: firmware may
        # legitimately be newer than the host, and an unrecognised channel must
        # never silently reach a module that would misinterpret it.
        quality = SampleQuality.INVALID

    return Sample(
        device=device,
        channel=channel,
        value=value,
        t_seconds=t_seconds,
        quality=quality,
    )


class SerialBridgeDevice(DeviceDriver):
    """Read-only serial reader for the ``CS,`` line protocol."""

    kind: ClassVar[str] = "serial"

    def __init__(self, name: str = "serial.bridge", config: Mapping[str, Any] | None = None):
        super().__init__(name, config)
        self._port = self.config.get("port") or ""
        self._baud = int(self.config.get("baud", 115200))
        self._timeout = float(self.config.get("timeout_seconds", 0.2))
        self._handle: Any = None
        self._elapsed_s = 0.0
        self._interval_s = 1.0 / float(self.config.get("sample_rate_hz", 4.0))
        self.rejected_lines = 0

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            channels=CHANNELS,
            sample_rate_hz=1.0 / self._interval_s,
            bidirectional=False,
        )

    def open(self) -> None:
        if not self._port:
            raise DeviceUnavailable(
                "no serial port configured; set CS_SERIAL_PORT or pass {'port': ...}"
            )
        try:
            import serial  # noqa: PLC0415
        except ImportError as exc:  # pragma: no cover - depends on the machine
            raise DeviceUnavailable(
                "the serial adapter needs pyserial: pip install 'conscious-subconscious[devices]'"
            ) from exc
        try:
            self._handle = serial.Serial(self._port, self._baud, timeout=self._timeout)
        except Exception as exc:  # pragma: no cover - hardware dependent
            raise DeviceUnavailable(f"cannot open serial port {self._port!r}: {exc}") from exc
        self._open = True

    def close(self) -> None:
        if self._handle is not None:
            try:
                self._handle.close()
            finally:
                self._handle = None
        self._open = False

    def read(self) -> tuple[Sample, ...]:
        self.require_open()
        produced: list[Sample] = []
        # Bounded drain: a chatty device must not be able to starve the caller.
        for _ in range(256):
            try:
                raw = self._handle.readline(MAX_LINE_BYTES)
            except Exception as exc:  # pragma: no cover - hardware dependent
                raise DeviceError(f"serial read failed: {exc}") from exc
            if not raw:
                break
            try:
                text = raw.decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover - decode never raises with 'replace'
                self.rejected_lines += 1
                continue
            if len(text) >= MAX_LINE_BYTES:
                self.rejected_lines += 1
                continue
            self._elapsed_s += self._interval_s
            sample = parse_line(text, device=self.name, t_seconds=round(self._elapsed_s, 6))
            if sample is None:
                continue
            produced.append(sample)
            self.samples_read += 1
        return tuple(produced)
