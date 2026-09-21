"""Bluetooth LE heart-rate adapter.

The parsing is separated from the Bluetooth stack on purpose:

* :func:`parse_heart_rate_measurement` is a pure function over bytes. It is
  fully tested in CI with no radio, no adapter and no ``bleak`` installed.
* :class:`BleHeartRateDevice` is the thin layer that receives those bytes.

That split exists because the parsing is where the bugs are — the characteristic
has a flags byte, two widths for the same field, optional sections, and 1/1024 s
units for RR intervals. Getting it wrong produces plausible-looking numbers,
which is the worst kind of wrong.

This adapter is **read-only**: it subscribes to notifications and never writes a
characteristic.
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

__all__ = [
    "HEART_RATE_SERVICE_UUID",
    "HEART_RATE_MEASUREMENT_UUID",
    "parse_heart_rate_measurement",
    "rmssd_ms",
    "hrv_index_from_rmssd",
    "BleHeartRateDevice",
]

HEART_RATE_SERVICE_UUID = "0000180d-0000-1000-8000-00805f9b34fb"
HEART_RATE_MEASUREMENT_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

#: RR intervals are transmitted in units of 1/1024 s.
RR_UNIT_SECONDS = 1.0 / 1024.0

#: Convenience mapping used to present RMSSD as a 0..1 index. These bounds are a
#: presentation choice, NOT a clinical interpretation, and nothing in the model
#: depends on them being meaningful.
HRV_INDEX_RMSSD_MIN_MS = 20.0
HRV_INDEX_RMSSD_MAX_MS = 80.0

CHANNELS: tuple[ChannelSpec, ...] = (
    ChannelSpec(name="heart_rate", unit="bpm", nominal_rate_hz=1.0, minimum=25.0, maximum=220.0),
    ChannelSpec(name="hrv_index", unit="ratio", nominal_rate_hz=0.2, minimum=0.0, maximum=1.0),
)


def parse_heart_rate_measurement(data: bytes) -> dict[str, Any]:
    """Parse a Heart Rate Measurement (0x2A37) notification.

    Returns ``heart_rate`` (bpm), ``contact_supported``, ``contact_detected``,
    ``energy_expended_kj`` (when present) and ``rr_intervals_s``.

    Raises :class:`DeviceError` on a malformed frame. A truncated frame is not
    recovered by guessing: the only safe answer to "which half of a 16-bit value
    did I receive?" is to refuse.
    """
    if not isinstance(data, (bytes, bytearray)):
        raise DeviceError("heart-rate measurement must be bytes")
    if not data:
        raise DeviceError("heart-rate measurement frame is empty")

    flags = data[0]
    wide_value = bool(flags & 0x01)
    contact_supported = bool(flags & 0x02)
    contact_detected = bool(flags & 0x04)
    energy_present = bool(flags & 0x08)
    rr_present = bool(flags & 0x10)

    cursor = 1
    if wide_value:
        if len(data) < cursor + 2:
            raise DeviceError("frame declares a 16-bit rate but is truncated")
        heart_rate = float(data[cursor] | (data[cursor + 1] << 8))
        cursor += 2
    else:
        if len(data) < cursor + 1:
            raise DeviceError("frame declares an 8-bit rate but is truncated")
        heart_rate = float(data[cursor])
        cursor += 1

    if heart_rate == 0.0:
        # A zero rate is the standard way to signal "no measurement", not a
        # person with no pulse.
        raise DeviceError("heart-rate value is 0, which means 'no measurement'")

    energy_kj: float | None = None
    if energy_present:
        if len(data) < cursor + 2:
            raise DeviceError("frame declares energy expended but is truncated")
        energy_kj = float(data[cursor] | (data[cursor + 1] << 8))
        cursor += 2

    rr_intervals: list[float] = []
    if rr_present:
        remaining = len(data) - cursor
        if remaining % 2 != 0:
            raise DeviceError(
                f"RR interval section has {remaining} bytes, which is not a whole "
                "number of 16-bit intervals"
            )
        while cursor + 1 < len(data):
            raw = data[cursor] | (data[cursor + 1] << 8)
            rr_intervals.append(raw * RR_UNIT_SECONDS)
            cursor += 2

    quality = SampleQuality.OK
    if contact_supported and not contact_detected:
        # Poor electrode contact is the single most common source of nonsense
        # HRV data. Flagging it lets the module layer refuse the sample.
        quality = SampleQuality.SUSPECT

    return {
        "heart_rate": heart_rate,
        "contact_supported": contact_supported,
        "contact_detected": contact_detected,
        "energy_expended_kj": energy_kj,
        "rr_intervals_s": rr_intervals,
        "quality": quality,
    }


def rmssd_ms(rr_intervals_s: list[float] | tuple[float, ...]) -> float | None:
    """Root mean square of successive differences, in milliseconds.

    Returns ``None`` when there are fewer than two intervals, because RMSSD of a
    single interval is undefined — returning 0.0 would look like a measurement.
    """
    if len(rr_intervals_s) < 2:
        return None
    differences = [
        (later - earlier) * 1000.0
        for earlier, later in zip(rr_intervals_s, rr_intervals_s[1:], strict=False)
    ]
    mean_square = float(sum(d * d for d in differences) / len(differences))
    return mean_square**0.5


def hrv_index_from_rmssd(rmssd: float | None) -> float | None:
    """Map RMSSD in milliseconds onto a 0..1 index for the autonomic module.

    A presentation convenience with hard-coded bounds, not a clinical measure.
    The clamp is deliberate: an index outside [0, 1] would be clamped downstream
    anyway, and doing it here keeps the provenance of the clipping visible.
    """
    if rmssd is None or rmssd != rmssd:
        return None
    span = HRV_INDEX_RMSSD_MAX_MS - HRV_INDEX_RMSSD_MIN_MS
    return max(0.0, min(1.0, (rmssd - HRV_INDEX_RMSSD_MIN_MS) / span))


class BleHeartRateDevice(DeviceDriver):
    """Read-only BLE heart-rate subscriber."""

    kind: ClassVar[str] = "ble-heart-rate"

    def __init__(self, name: str = "ble.heart-rate", config: Mapping[str, Any] | None = None):
        super().__init__(name, config)
        self._address = self.config.get("address") or None
        self._pending: list[Sample] = []
        self._rr_window: list[float] = []
        self._index_khz = int(self.config.get("hrv_sample_every_n_beats", 15))

    @property
    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(channels=CHANNELS, sample_rate_hz=1.0, bidirectional=False)

    def open(self) -> None:
        try:
            import bleak  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on the machine
            raise DeviceUnavailable(
                "the BLE adapter needs the 'bleak' package: pip install "
                "'conscious-subconscious[devices]'"
            ) from exc
        raise DeviceUnavailable(
            "BLE scanning is not started by this process. Run a host bridge that "
            "subscribes to the heart-rate characteristic and forwards parsed "
            "samples, or use the simulated adapter for offline work."
        )

    def close(self) -> None:
        self._open = False
        self._pending.clear()

    def ingest(self, data: bytes, *, t_seconds: float) -> tuple[Sample, ...]:
        """Feed a raw characteristic value and queue the derived samples.

        Kept public so a host bridge can push notifications in without this
        class having to own an event loop.
        """
        parsed = parse_heart_rate_measurement(data)
        produced: list[Sample] = [
            Sample(
                device=self.name,
                channel="heart_rate",
                value=parsed["heart_rate"],
                t_seconds=t_seconds,
                unit="bpm",
                quality=parsed["quality"],
            )
        ]
        self._rr_window.extend(parsed["rr_intervals_s"])
        if len(self._rr_window) > 120:
            del self._rr_window[:-120]
        self._rr_count = getattr(self, "_rr_count", 0) + 1
        if self._index_khz > 0 and self._rr_count % self._index_khz == 0:
            index = hrv_index_from_rmssd(rmssd_ms(self._rr_window))
            if index is not None:
                produced.append(
                    Sample(
                        device=self.name,
                        channel="hrv_index",
                        value=round(index, 6),
                        t_seconds=t_seconds,
                        unit="ratio",
                        quality=parsed["quality"],
                    )
                )
        self._pending.extend(produced)
        self.samples_read += 1
        return tuple(produced)

    def read(self) -> tuple[Sample, ...]:
        self.require_open()
        drained = tuple(self._pending)
        self._pending.clear()
        return drained
