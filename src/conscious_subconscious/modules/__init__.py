"""Opt-in model modules.

Modules add physiology-ish behaviour to the engine without the engine having to
know about it. Built-ins are registered lazily; see
:mod:`conscious_subconscious.modules.registry`.
"""

from __future__ import annotations

from .base import Module
from .registry import available, build, build_modules, describe_all, get, register

__all__ = [
    "Module",
    "available",
    "build",
    "build_modules",
    "describe_all",
    "get",
    "register",
]
