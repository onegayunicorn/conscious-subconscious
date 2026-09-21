"""Authentication, rate limiting, redaction and request-size limits.

These are small, dependency-free building blocks rather than a framework, so
they can be unit-tested directly and so that the API cannot quietly acquire a
security posture that is only visible in middleware configuration nobody reads.

Two decisions worth stating explicitly:

* **An empty API key disables authentication.** That is convenient in
  development and unacceptable on a network interface, so
  :func:`assert_safe_bind` refuses to start on a non-loopback host with no key
  configured. Convenience is allowed; silent exposure is not.
* **Log redaction is a positive list of patterns, not a filter of known
  secrets.** A pattern list that only removes keys the author remembered will
  leak the first key they did not.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..core.errors import ConfigurationError

__all__ = [
    "ApiKeyAuth",
    "RateLimiter",
    "RateLimitDecision",
    "redact",
    "redact_mapping",
    "assert_safe_bind",
    "is_loopback",
    "SECRET_PATTERNS",
]

#: Patterns that must never appear in a log line.
SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github_pat", re.compile(r"github_pat_[A-Za-z0-9_]{20,}")),
    ("github_classic", re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}")),
    ("anthropic", re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}")),
    ("openai", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("aws_access_key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("slack", re.compile(r"xox[abprs]-[A-Za-z0-9\-]{10,}")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    # Requires a long token after the assignment. A looser pattern would redact
    # `api_key: str | None = None`, which appears in ordinary type annotations
    # and would train reviewers to ignore the redactor.
    (
        "api_key_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token|password)\b\s*[:=]\s*[\"']?"
            r"[A-Za-z0-9_\-]{16,}"
        ),
    ),
)

_MASK = "[redacted]"


def redact(text: str) -> str:
    """Replace anything that looks like a credential with a mask.

    Apply this to every outbound log line and to every error message that
    echoes caller input.
    """
    if not text:
        return text
    redacted = text
    for _, pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_MASK, redacted)
    return redacted


def redact_mapping(payload: Mapping[str, Any], *, depth: int = 0) -> dict[str, Any]:
    """Recursively redact string values in a mapping (bounded depth)."""
    if depth > 6:
        return {"_truncated": "[depth limit]"}
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            out[key] = redact(value)
        elif isinstance(value, Mapping):
            out[key] = redact_mapping(value, depth=depth + 1)
        elif isinstance(value, (list, tuple)):
            out[key] = [
                redact(item)
                if isinstance(item, str)
                else redact_mapping(item, depth=depth + 1)
                if isinstance(item, Mapping)
                else item
                for item in value
            ]
        else:
            out[key] = value
    return out


@dataclass(slots=True)
class ApiKeyAuth:
    """Constant-time API-key check with an explicit "disabled" state."""

    key: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.key)

    @property
    def enabled(self) -> bool:
        return self.configured

    def check(self, provided: str | None) -> bool:
        """True when the request may proceed."""
        if not self.configured:
            return True
        if not provided:
            return False
        # compare_digest avoids leaking length/prefix information through timing.
        import hmac  # noqa: PLC0415

        return hmac.compare_digest(provided, self.key or "")

    def describe(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "scheme": "X-API-Key",
            "note": (
                "authentication is DISABLED (no CS_API_KEY set); acceptable only on a "
                "loopback interface"
            )
            if not self.enabled
            else "requests must present a valid X-API-Key header",
        }


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: float = 0.0
    remaining: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "retry_after_seconds": round(self.retry_after_seconds, 3),
            "remaining": self.remaining,
        }


@dataclass(slots=True)
class _Bucket:
    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Sliding-window limiter, per client identifier.

    A sliding window rather than a token bucket because it is easier to reason
    about from the outside: "at most N requests in any 60-second window" is a
    sentence an operator can verify against a log.
    """

    def __init__(self, *, per_minute: int = 120, clock: Any = time.monotonic) -> None:
        if per_minute < 1:
            raise ConfigurationError("per_minute must be at least 1")
        self.per_minute = per_minute
        self.window_seconds = 60.0
        self._clock = clock
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def check(self, client: str) -> RateLimitDecision:
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets.setdefault(client, _Bucket())
            bucket.timestamps = [t for t in bucket.timestamps if t > cutoff]
            if len(bucket.timestamps) >= self.per_minute:
                oldest = bucket.timestamps[0]
                return RateLimitDecision(
                    allowed=False,
                    retry_after_seconds=max(0.0, self.window_seconds - (now - oldest)),
                    remaining=0,
                )
            bucket.timestamps.append(now)
            return RateLimitDecision(
                allowed=True, remaining=self.per_minute - len(bucket.timestamps)
            )

    def reset(self, client: str | None = None) -> None:
        with self._lock:
            if client is None:
                self._buckets.clear()
            else:
                self._buckets.pop(client, None)

    @property
    def tracked_clients(self) -> int:
        with self._lock:
            return len(self._buckets)


def is_loopback(host: str) -> bool:
    """True for the hosts that are not reachable from another machine."""
    normalised = (host or "").strip().lower()
    return normalised in {"127.0.0.1", "::1", "localhost", "127.0.0.1.localhost"}


def assert_safe_bind(*, host: str, api_key: str | None) -> None:
    """Refuse a configuration that would expose an unauthenticated service.

    Called at startup. Failing loudly here is much better than a service that
    quietly accepts anonymous write requests from the network.
    """
    if is_loopback(host):
        return
    if not api_key:
        raise ConfigurationError(
            f"refusing to bind to {host!r} without CS_API_KEY set: an "
            "unauthenticated simulation API must not be reachable off-host"
        )
