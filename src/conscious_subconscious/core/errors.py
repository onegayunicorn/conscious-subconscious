"""Exception hierarchy.

Every error raised deliberately by the project derives from
:class:`ConsciousSubconsciousError`, so callers can catch the whole family.
"""

from __future__ import annotations

__all__ = [
    "ConsciousSubconsciousError",
    "ParameterError",
    "ConfigurationError",
    "ProtocolError",
    "DeviceError",
    "DeviceUnavailable",
    "PipelineError",
    "HardeningFindingError",
]


class ConsciousSubconsciousError(Exception):
    """Base class for every deliberate error in this project."""


class ParameterError(ConsciousSubconsciousError, ValueError):
    """A parameter is missing, malformed, duplicated or out of range."""


class ConfigurationError(ConsciousSubconsciousError, ValueError):
    """A scenario or run configuration is inconsistent."""


class ProtocolError(ConsciousSubconsciousError, ValueError):
    """A wire message does not satisfy the protocol envelope."""


class DeviceError(ConsciousSubconsciousError, RuntimeError):
    """A hardware adapter failed at runtime."""


class DeviceUnavailable(DeviceError):
    """An adapter cannot be used here: missing dependency, port or peer.

    This is deliberately distinct from :class:`DeviceError`: it means "this
    machine cannot do that", not "the device misbehaved". Callers usually want
    to skip rather than abort.
    """


class PipelineError(ConsciousSubconsciousError, RuntimeError):
    """A data pipeline failed to validate or execute."""


class HardeningFindingError(ConsciousSubconsciousError, RuntimeError):
    """A blocking hardening finding was found (only raised in strict mode)."""
