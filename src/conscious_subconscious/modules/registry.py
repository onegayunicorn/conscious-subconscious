"""Module registry.

Built-in modules are imported lazily so that importing this module can never
create an import cycle with :mod:`conscious_subconscious.model`. Third-party
modules can register themselves with :func:`register` at import time.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable
from typing import TypeVar

from ..core.errors import ConfigurationError
from ..core.params import ParameterSet
from .base import Module

__all__ = ["register", "available", "build", "build_modules", "get", "describe_all"]

_REGISTRY: dict[str, type[Module]] = {}

#: Import order is irrelevant: modules must not depend on one another.
_BUILTIN: tuple[str, ...] = (
    "autonomic",
    "circadian",
    "expectancy",
    "inflammation",
    "perfusion",
)

_M = TypeVar("_M", bound=type[Module])


def register(cls: _M) -> _M:
    """Class decorator that adds a module to the registry."""
    existing = _REGISTRY.get(cls.name)
    if existing is not None and existing is not cls:
        raise ConfigurationError(
            f"module name {cls.name!r} is already registered by {existing.__name__}"
        )
    _REGISTRY[cls.name] = cls
    return cls


def _load_builtin() -> None:
    if _REGISTRY:
        return
    for name in _BUILTIN:
        importlib.import_module(f"{__package__}.{name}")


def available() -> tuple[str, ...]:
    """Names of every registered module, sorted."""
    _load_builtin()
    return tuple(sorted(_REGISTRY))


def get(name: str) -> type[Module]:
    """Look up a module class by name."""
    _load_builtin()
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ConfigurationError(
            f"unknown module {name!r}; available: {', '.join(available())}"
        ) from exc


def build(names: Iterable[str], params: ParameterSet) -> tuple[Module, ...]:
    """Instantiate modules for ``names``.

    Names are deduplicated and sorted so that the same configuration always
    produces the same module order, regardless of how a caller listed them.
    """
    _load_builtin()
    wanted = sorted(set(names))
    return tuple(get(name)(params) for name in wanted)


def build_modules(names: Iterable[str], params: ParameterSet) -> tuple[Module, ...]:
    """Alias kept because both names read naturally at call sites."""
    return build(names, params)


def describe_all() -> list[dict[str, object]]:
    """Describe every registered module, for ``cs-sim modules`` and the API."""
    _load_builtin()
    return [_describe(name) for name in available()]


def _describe(name: str) -> dict[str, object]:
    cls = _REGISTRY[name]
    return {
        "name": name,
        "class": cls.__name__,
        "doc": (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else "",
        "parameters": list(cls.parameter_keys()),
    }
