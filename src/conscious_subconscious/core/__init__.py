"""Core primitives with no third-party dependencies.

Everything in this subpackage runs on a bare CPython interpreter: no numpy, no
pydantic, no FastAPI. That is a deliberate constraint — the engine must remain
runnable in a locked-down or offline environment, and it must be trivially
testable.
"""

from __future__ import annotations

from .clock import VirtualClock
from .errors import (
    ConfigurationError,
    ConsciousSubconsciousError,
    DeviceError,
    DeviceUnavailable,
    HardeningFindingError,
    ParameterError,
    PipelineError,
    ProtocolError,
)
from .events import Event, EventBus, EventKind
from .params import Parameter, ParameterSet, Provenance
from .rng import DeterministicRng

__all__ = [
    "ConfigurationError",
    "ConsciousSubconsciousError",
    "DeterministicRng",
    "DeviceError",
    "DeviceUnavailable",
    "Event",
    "EventBus",
    "EventKind",
    "HardeningFindingError",
    "Parameter",
    "ParameterError",
    "ParameterSet",
    "PipelineError",
    "ProtocolError",
    "Provenance",
    "VirtualClock",
]
