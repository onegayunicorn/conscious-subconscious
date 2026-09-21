"""Service layer: sessions, security primitives, telemetry.

This package deliberately does **not** import FastAPI. The HTTP application
lives in ``services.api`` and pulls in the ``api`` extra; keeping it separate
means the session manager, the rate limiter and the redactor can be tested on a
machine that has none of those dependencies installed.
"""

from __future__ import annotations

from .config import Settings, load_settings
from .security import (
    SECRET_PATTERNS,
    ApiKeyAuth,
    RateLimitDecision,
    RateLimiter,
    assert_safe_bind,
    is_loopback,
    redact,
    redact_mapping,
)
from .session import Session, SessionLimitReached, SessionManager, SessionNotFound
from .telemetry import Metrics, StandardCounters, render_prometheus, standard_metrics

__all__ = [
    "ApiKeyAuth",
    "Metrics",
    "RateLimitDecision",
    "RateLimiter",
    "SECRET_PATTERNS",
    "Session",
    "SessionLimitReached",
    "SessionManager",
    "SessionNotFound",
    "Settings",
    "StandardCounters",
    "assert_safe_bind",
    "is_loopback",
    "load_settings",
    "redact",
    "redact_mapping",
    "render_prometheus",
    "standard_metrics",
]
