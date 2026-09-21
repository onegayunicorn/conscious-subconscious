"""Device registry.

Adapters are looked up by ``kind`` so that a session configuration can say
``{"kind": "simulated"}`` without importing driver modules. Imports of optional
dependencies stay inside each driver, so registering an adapter never requires
its third-party package to be installed.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, TypeVar

from ..core.errors import DeviceError, DeviceUnavailable
from .base import DeviceDriver
from .ble_heart_rate import BleHeartRateDevice
from .lsl_device import LslInletDevice
from .replay import ReplayDevice
from .serial_bridge import SerialBridgeDevice
from .simulated import SimulatedCardioDevice

__all__ = ["register", "available", "get", "build", "build_all", "describe_all"]

_REGISTRY: dict[str, type[DeviceDriver]] = {}

_D = TypeVar("_D", bound=type[DeviceDriver])


def register(cls: _D) -> _D:
    """Register a driver class under its ``kind``."""
    existing = _REGISTRY.get(cls.kind)
    if existing is not None and existing is not cls:
        raise DeviceError(f"device kind {cls.kind!r} is already registered by {existing.__name__}")
    _REGISTRY[cls.kind] = cls
    return cls


for _driver in (
    SimulatedCardioDevice,
    SerialBridgeDevice,
    LslInletDevice,
    BleHeartRateDevice,
    ReplayDevice,
):
    register(_driver)


def available() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def get(kind: str) -> type[DeviceDriver]:
    try:
        return _REGISTRY[kind]
    except KeyError as exc:
        raise DeviceError(
            f"unknown device kind {kind!r}; available: {', '.join(available())}"
        ) from exc


def build(spec: Mapping[str, Any]) -> DeviceDriver:
    """Instantiate one driver from a spec mapping.

    Required key: ``kind``. Optional: ``name``, plus any driver-specific keys.
    """
    if not isinstance(spec, Mapping):
        raise DeviceError("device spec must be a mapping")
    kind = spec.get("kind")
    if not kind:
        raise DeviceError("device spec needs a 'kind'")
    driver = get(str(kind))
    name = str(spec.get("name") or f"{kind}.device")
    config = {key: value for key, value in spec.items() if key not in {"kind", "name"}}
    return driver(name, config)


def build_all(
    specs: Iterable[Mapping[str, Any]], *, keep_unavailable: bool = True
) -> tuple[DeviceDriver, ...]:
    """Instantiate several drivers, tolerating unavailable hardware.

    With ``keep_unavailable`` set (the default), a driver whose constructor
    raises :class:`DeviceUnavailable` is skipped and reported through the
    returned tuple's absence. Callers that need to know what was skipped should
    use :func:`build_reported` instead.
    """
    drivers: list[DeviceDriver] = []
    for spec in specs:
        try:
            drivers.append(build(spec))
        except DeviceUnavailable:
            if not keep_unavailable:
                raise
    return tuple(drivers)


def build_reported(
    specs: Iterable[Mapping[str, Any]],
) -> tuple[tuple[DeviceDriver, ...], list[dict[str, str]]]:
    """Instantiate drivers and also report which specs could not be built.

    Returning the failures rather than swallowing them is the difference
    between "the sensor was not found" and "the sensor was found and broken".
    """
    drivers: list[DeviceDriver] = []
    problems: list[dict[str, str]] = []
    for spec in specs:
        kind = str(spec.get("kind", "?"))
        try:
            drivers.append(build(spec))
        except (DeviceUnavailable, DeviceError) as exc:
            problems.append({"kind": kind, "error": f"{type(exc).__name__}: {exc}"})
    return tuple(drivers), problems


def describe_all() -> list[dict[str, Any]]:
    """Describe every registered driver kind without opening anything."""
    described: list[dict[str, Any]] = []
    for kind in available():
        cls = _REGISTRY[kind]
        described.append(
            {
                "kind": kind,
                "class": cls.__name__,
                "doc": (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else "",
            }
        )
    return described
