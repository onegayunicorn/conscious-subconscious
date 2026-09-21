"""Service configuration, read from the environment once at startup.

Reading configuration in one place makes it auditable: you can see every knob a
deployment can turn, and every default it falls back to, without grepping for
``os.environ``.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from ..core.errors import ConfigurationError

__all__ = ["Settings", "load_settings"]


def _get_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} must be a number, got {raw!r}") from exc


def _get_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{key} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True, slots=True)
class Settings:
    """Resolved service settings."""

    host: str = "127.0.0.1"
    port: int = 8080
    api_key: str | None = None
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    rate_limit_per_minute: int = 120
    max_body_bytes: int = 1_048_576
    log_level: str = "INFO"
    max_sessions: int = 16
    session_ttl_seconds: float = 3600.0
    default_seed: int = 20260921
    default_dt_hours: float = 0.05
    default_horizon_hours: float = 72.0
    dev_mode: bool = False
    raw: Mapping[str, str] = field(default_factory=dict)

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key)

    def describe(self) -> dict[str, object]:
        """Safe-to-log view. The API key is reported as present or absent only."""
        return {
            "host": self.host,
            "port": self.port,
            "api_key_configured": self.auth_enabled,
            "allowed_origins": list(self.allowed_origins),
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "max_body_bytes": self.max_body_bytes,
            "log_level": self.log_level,
            "max_sessions": self.max_sessions,
            "session_ttl_seconds": self.session_ttl_seconds,
            "dev_mode": self.dev_mode,
        }


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build :class:`Settings` from ``env`` (defaults to ``os.environ``)."""
    source: Mapping[str, str] = env if env is not None else os.environ
    origins_raw = source.get("CS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    origins = tuple(part.strip() for part in origins_raw.split(",") if part.strip())
    if "*" in origins:
        # Wildcard CORS plus an API key in a header is a configuration that looks
        # locked down and is not.
        raise ConfigurationError(
            "CS_ALLOWED_ORIGINS must not contain '*'; list the origins explicitly"
        )
    api_key = source.get("CS_API_KEY") or None
    return Settings(
        host=source.get("CS_HOST", "127.0.0.1"),
        port=_get_int(source, "CS_PORT", 8080),
        api_key=api_key,
        allowed_origins=origins,
        rate_limit_per_minute=_get_int(source, "CS_RATE_LIMIT_PER_MINUTE", 120),
        max_body_bytes=_get_int(source, "CS_MAX_BODY_BYTES", 1_048_576),
        log_level=source.get("CS_LOG_LEVEL", "INFO").upper(),
        max_sessions=_get_int(source, "CS_MAX_SESSIONS", 16),
        session_ttl_seconds=_get_float(source, "CS_SESSION_TTL_SECONDS", 3600.0),
        default_seed=_get_int(source, "CS_DEFAULT_SEED", 20260921),
        default_dt_hours=_get_float(source, "CS_DEFAULT_DT_HOURS", 0.05),
        default_horizon_hours=_get_float(source, "CS_DEFAULT_HORIZON_HOURS", 72.0),
        dev_mode=bool(source.get("CS_DEV_MODE")),
        raw={key: value for key, value in source.items() if key.startswith("CS_")},
    )
