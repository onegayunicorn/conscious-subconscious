"""Topic naming for publish/subscribe transports (MQTT, and anything similar).

One place decides what a topic looks like, so a producer and a consumer cannot
disagree about it:

.. code-block:: text

    cs/v1/sessions/{session}/events
    cs/v1/sessions/{session}/commands
    cs/v1/sessions/{session}/devices/{device}/stream
    cs/v1/sessions/{session}/devices/{device}/state

Session and device identifiers are restricted to ``[A-Za-z0-9._-]``. MQTT level
separators are ``/`` and the wildcards ``+`` and ``#`` are meaningful, so an
identifier containing either would let a peer publish into another session's
namespace. That is a small thing that turns into a large thing.
"""

from __future__ import annotations

import re
from typing import Any

from ..core.errors import ProtocolError

__all__ = [
    "TOPIC_ROOT",
    "TOPIC_VERSION",
    "KINDS",
    "validate_identifier",
    "session_topic",
    "device_topic",
    "device_wildcard",
    "session_wildcard",
    "parse_topic",
]

TOPIC_ROOT = "cs"
TOPIC_VERSION = "v1"

#: Topic kinds a session exposes.
KINDS: tuple[str, ...] = ("events", "commands", "devices")

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def validate_identifier(value: str, *, what: str = "identifier") -> str:
    """Validate a session or device identifier for use in a topic."""
    if not isinstance(value, str) or not _IDENTIFIER_RE.match(value):
        raise ProtocolError(
            f"{what} must match [A-Za-z0-9._-]{{1,64}}, got {value!r} "
            "(wildcards and '/' would let a peer escape its namespace)"
        )
    return value


def session_topic(session: str, kind: str = "events") -> str:
    """``cs/v1/sessions/{session}/{kind}``."""
    validate_identifier(session, what="session")
    if kind not in ("events", "commands"):
        raise ProtocolError(f"session kind must be 'events' or 'commands', got {kind!r}")
    return f"{TOPIC_ROOT}/{TOPIC_VERSION}/sessions/{session}/{kind}"


def device_topic(session: str, device: str, leaf: str = "stream") -> str:
    """``cs/v1/sessions/{session}/devices/{device}/{leaf}``."""
    validate_identifier(session, what="session")
    validate_identifier(device, what="device")
    if leaf not in ("stream", "state", "command", "hello"):
        raise ProtocolError(f"unknown device leaf {leaf!r}")
    return f"{TOPIC_ROOT}/{TOPIC_VERSION}/sessions/{session}/devices/{device}/{leaf}"


def device_wildcard(session: str, leaf: str = "stream") -> str:
    """Subscribe to every device's ``leaf`` in a session."""
    validate_identifier(session, what="session")
    return f"{TOPIC_ROOT}/{TOPIC_VERSION}/sessions/{session}/devices/+/{leaf}"


def session_wildcard() -> str:
    """Subscribe to every session's events. Intended for operators, not clients."""
    return f"{TOPIC_ROOT}/{TOPIC_VERSION}/sessions/+/events"


def parse_topic(topic: str) -> dict[str, Any]:
    """Parse a concrete (non-wildcard) topic back into its parts."""
    if not isinstance(topic, str) or not topic:
        raise ProtocolError("topic must be a non-empty string")
    if "+" in topic or "#" in topic:
        raise ProtocolError("cannot parse a wildcard topic; resolve it first")
    parts = topic.split("/")
    if len(parts) < 4 or parts[0] != TOPIC_ROOT:
        raise ProtocolError(f"not a {TOPIC_ROOT} topic: {topic!r}")
    if parts[1] != TOPIC_VERSION:
        raise ProtocolError(f"unsupported topic version {parts[1]!r}; expected {TOPIC_VERSION!r}")

    if parts[2] != "sessions" or len(parts) < 5:
        raise ProtocolError(f"unexpected topic shape: {topic!r}")
    session = validate_identifier(parts[3], what="session")

    if parts[4] in ("events", "commands"):
        if len(parts) != 5:
            raise ProtocolError(f"trailing levels in topic {topic!r}")
        return {"session": session, "kind": parts[4]}

    if parts[4] == "devices":
        if len(parts) != 7:
            raise ProtocolError(f"device topic needs 7 levels, got {len(parts)}: {topic!r}")
        return {
            "session": session,
            "kind": "devices",
            "device": validate_identifier(parts[5], what="device"),
            "leaf": parts[6],
        }

    raise ProtocolError(f"unknown topic segment {parts[4]!r} in {topic!r}")
