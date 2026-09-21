"""The device-driver contract.

Every adapter — real or synthetic — implements the same tiny surface: describe
yourself, open, read, close. Two properties are load-bearing:

**Read-only with respect to the wearer.** No shipped adapter has a ``write`` or
``stimulate`` method, and ``bidirectional`` defaults to False. A simulation
project that can drive a stimulator is a different project with a different
safety case; pretending otherwise by adding "just one" output channel is how
that boundary gets crossed by accident.

**Honest unavailability.** A driver that cannot run here raises
:class:`DeviceUnavailable`, not a generic error and not a silent empty read.
"pyserial is not installed" and "the sensor returned garbage" need different
responses from the caller, so they get different exception types.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from ..core.errors import DeviceError

__all__ = [
    "SampleQuality",
    "ChannelSpec",
    "DeviceCapabilities",
    "Sample",
    "DeviceDriver",
]


class SampleQuality(str, Enum):
    """Sensor self-assessment attached to every sample."""

    OK = "ok"
    SUSPECT = "suspect"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class ChannelSpec:
    """One channel a device exposes."""

    name: str
    unit: str = ""
    nominal_rate_hz: float = 0.0
    minimum: float | None = None
    maximum: float | None = None

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": self.name}
        if self.unit:
            payload["unit"] = self.unit
        if self.nominal_rate_hz:
            payload["nominal_rate_hz"] = self.nominal_rate_hz
        if self.minimum is not None:
            payload["minimum"] = self.minimum
        if self.maximum is not None:
            payload["maximum"] = self.maximum
        return payload


@dataclass(frozen=True, slots=True)
class DeviceCapabilities:
    """What a device can do, before it is opened."""

    channels: tuple[ChannelSpec, ...]
    sample_rate_hz: float = 0.0
    bidirectional: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "channels": [c.as_dict() for c in self.channels],
            "sample_rate_hz": self.sample_rate_hz,
            "bidirectional": self.bidirectional,
        }


@dataclass(frozen=True, slots=True)
class Sample:
    """One reading, in the channel's own units."""

    device: str
    channel: str
    value: float
    t_seconds: float
    unit: str = ""
    quality: SampleQuality = SampleQuality.OK

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "device": self.device,
            "channel": self.channel,
            "value": self.value,
            "t_seconds": self.t_seconds,
        }
        if self.unit:
            payload["unit"] = self.unit
        if self.quality is not SampleQuality.OK:
            payload["quality"] = self.quality.value
        return payload

    @property
    def usable(self) -> bool:
        """True when the sample may be fed to a module."""
        return self.quality is not SampleQuality.INVALID and self.value == self.value


class DeviceDriver(ABC):
    """Base class for hardware adapters."""

    #: Driver kind, matching the ``device.hello`` schema enum.
    kind: ClassVar[str] = ""

    def __init__(self, name: str, config: Mapping[str, Any] | None = None) -> None:
        if not name:
            raise DeviceError("device name must be non-empty")
        self.name = name
        self.config: dict[str, Any] = dict(config or {})
        self._open = False
        self.samples_read = 0

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.kind:
            raise DeviceError(f"{cls.__name__} must define a non-empty 'kind'")

    # -- lifecycle ---------------------------------------------------------
    @abstractmethod
    def open(self) -> None:
        """Acquire the device. Raise :class:`DeviceUnavailable` if impossible here."""

    @abstractmethod
    def close(self) -> None:
        """Release the device. Must be safe to call twice."""

    @abstractmethod
    def read(self) -> tuple[Sample, ...]:
        """Return every sample available since the last call (possibly none)."""

    # -- description -------------------------------------------------------
    @property
    @abstractmethod
    def capabilities(self) -> DeviceCapabilities:
        """Static description of the device's channels."""

    @property
    def is_open(self) -> bool:
        return self._open

    def require_open(self) -> None:
        if not self._open:
            raise DeviceError(f"{self.name}: device is not open")

    def describe(self) -> dict[str, Any]:
        payload = {
            "name": self.name,
            "kind": self.kind,
            "open": self._open,
            "samples_read": self.samples_read,
            **self.capabilities.as_dict(),
        }
        return payload

    def hello_payload(self) -> dict[str, Any]:
        """Build the ``device.hello`` payload for this device."""
        caps = self.capabilities
        payload: dict[str, Any] = {
            "device": self.name,
            "kind": self.kind,
            "channels": [c.as_dict() for c in caps.channels],
        }
        if caps.sample_rate_hz:
            payload["sample_rate_hz"] = caps.sample_rate_hz
        payload["bidirectional"] = caps.bidirectional
        return payload

    @classmethod
    def declared_kind(cls) -> str:
        return cls.kind

    def __enter__(self) -> DeviceDriver:
        self.open()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"{type(self).__name__}(name={self.name!r}, open={self._open})"


@dataclass(slots=True)
class DeviceStatus:
    """Mutable status snapshot a driver may publish."""

    name: str
    kind: str
    open: bool
    samples_read: int = 0
    last_error: str | None = None
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "open": self.open,
            "samples_read": self.samples_read,
            "last_error": self.last_error,
            "notes": list(self.notes),
        }
