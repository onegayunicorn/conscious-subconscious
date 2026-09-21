"""The wire envelope.

Every message on every transport is wrapped in the same object. One envelope,
one validator, one version string — so a bug in framing is found once rather
than once per transport.

The schema is deliberately closed: unknown message types and unknown envelope
keys are rejected. A simulation protocol that silently ignores fields it does
not understand is a protocol that will one day be handed a field it should have
understood, and will do the wrong thing quietly instead of loudly.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from ..core.errors import ProtocolError
from .jsonrpc import validate_jsonrpc

__all__ = [
    "SCHEMA_VERSION",
    "MessageType",
    "Envelope",
    "new_envelope",
    "validate_envelope",
    "ENVELOPE_KEYS",
]

#: Bumped on any breaking change to the envelope or its message types.
SCHEMA_VERSION = "1.0.0"

ENVELOPE_KEYS: frozenset[str] = frozenset({"v", "id", "ts", "type", "source", "session", "payload"})

_REQUIRED_KEYS: tuple[str, ...] = ("v", "id", "ts", "type", "source", "payload")

#: Hard ceilings. A peer that sends a 100 MB payload is a denial-of-service, not
#: a chatty sensor.
MAX_PAYLOAD_BYTES = 262_144
MAX_ID_LENGTH = 128
MAX_SOURCE_LENGTH = 128

#: Same character class the MQTT topic layer enforces, kept deliberately identical.
_SESSION_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class MessageType(str, Enum):
    """Message types the protocol defines."""

    DEVICE_HELLO = "device.hello"
    DEVICE_STATE = "device.state"
    STREAM_SAMPLE = "stream.sample"
    SIM_TICK = "sim.tick"
    SIM_COMMAND = "sim.command"
    SESSION_START = "session.start"
    SESSION_STOP = "session.stop"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    JSONRPC = "jsonrpc"


def new_envelope(
    message_type: MessageType | str,
    source: str,
    payload: Mapping[str, Any] | None = None,
    *,
    session: str | None = None,
    message_id: str | None = None,
    timestamp: datetime | None = None,
    version: str = SCHEMA_VERSION,
) -> Envelope:
    """Build a valid envelope.

    ``message_id`` and ``timestamp`` are injectable so tests can produce
    byte-identical messages; in normal use they are generated.
    """
    moment = timestamp or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ProtocolError("timestamp must be timezone-aware")
    return Envelope(
        v=version,
        id=message_id or uuid.uuid4().hex,
        ts=_format_timestamp(moment),
        type=message_type.value if isinstance(message_type, MessageType) else str(message_type),
        source=source,
        session=session,
        payload=dict(payload or {}),
    )


def _format_timestamp(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _parse_timestamp(raw: str) -> datetime:
    text = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProtocolError(f"ts is not a valid ISO-8601 timestamp: {raw!r}") from exc
    if parsed.tzinfo is None:
        raise ProtocolError(f"ts must carry a timezone offset: {raw!r}")
    return parsed


@dataclass(frozen=True, slots=True)
class Envelope:
    """An immutable protocol message."""

    v: str
    id: str
    ts: str
    type: str
    source: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    session: str | None = None

    def __post_init__(self) -> None:
        problems = validate_envelope(self.as_dict())
        if problems:
            raise ProtocolError("; ".join(problems))

    def as_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "v": self.v,
            "id": self.id,
            "ts": self.ts,
            "type": self.type,
            "source": self.source,
            "payload": dict(self.payload),
        }
        if self.session is not None:
            data["session"] = self.session
        return data

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Envelope:
        problems = validate_envelope(data)
        if problems:
            raise ProtocolError("; ".join(problems))
        return cls(
            v=str(data["v"]),
            id=str(data["id"]),
            ts=str(data["ts"]),
            type=str(data["type"]),
            source=str(data["source"]),
            payload=dict(data["payload"]),
            session=str(data["session"]) if data.get("session") is not None else None,
        )

    @classmethod
    def from_json(cls, raw: str | bytes) -> Envelope:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProtocolError(f"message is not valid JSON: {exc}") from exc
        if not isinstance(parsed, dict):
            raise ProtocolError("message must be a JSON object")
        return cls.from_dict(parsed)


def validate_envelope(data: object) -> tuple[str, ...]:
    # `data` is typed `object` on purpose: this function is the boundary that
    # decides whether an untrusted payload is a mapping at all, and annotating it
    # as a Mapping would make the guard below provably dead.
    """Return every problem found, rather than only the first.

    A validator that stops at the first error makes integration tedious and
    encourages people to disable validation.
    """
    problems: list[str] = []

    if not isinstance(data, Mapping):
        return ("message must be a mapping",)

    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        problems.append(f"missing required key(s): {', '.join(sorted(missing))}")

    unknown = sorted(set(data) - ENVELOPE_KEYS)
    if unknown:
        problems.append(f"unknown key(s): {', '.join(unknown)}")

    version = data.get("v")
    if isinstance(version, str):
        if version != SCHEMA_VERSION:
            problems.append(
                f"unsupported protocol version {version!r}; this build speaks {SCHEMA_VERSION}"
            )
    elif version is not None:
        problems.append("v must be a string")

    message_id = data.get("id")
    if not isinstance(message_id, str) or not message_id:
        problems.append("id must be a non-empty string")
    elif len(message_id) > MAX_ID_LENGTH:
        problems.append(f"id exceeds {MAX_ID_LENGTH} characters")

    source = data.get("source")
    if not isinstance(source, str) or not source:
        problems.append("source must be a non-empty string")
    elif len(source) > MAX_SOURCE_LENGTH:
        problems.append(f"source exceeds {MAX_SOURCE_LENGTH} characters")

    timestamp = data.get("ts")
    if not isinstance(timestamp, str) or not timestamp:
        problems.append("ts must be a non-empty string")
    else:
        try:
            _parse_timestamp(timestamp)
        except ProtocolError as exc:
            problems.append(str(exc))

    message_type = data.get("type")
    if not isinstance(message_type, str) or not message_type:
        problems.append("type must be a non-empty string")
    else:
        known = {member.value for member in MessageType}
        if message_type not in known:
            problems.append(
                f"unknown message type {message_type!r}; known: {', '.join(sorted(known))}"
            )

    payload = data.get("payload")
    if not isinstance(payload, Mapping):
        problems.append("payload must be a mapping")
    else:
        try:
            size = len(json.dumps(payload, separators=(",", ":"), default=str).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            problems.append(f"payload is not JSON-serialisable: {exc}")
            size = 0
        if size > MAX_PAYLOAD_BYTES:
            problems.append(f"payload of {size} bytes exceeds the {MAX_PAYLOAD_BYTES} byte limit")
        if message_type == MessageType.JSONRPC:
            problems.extend(validate_jsonrpc(payload))

    session = data.get("session")
    if session is not None:
        if not isinstance(session, str) or not session:
            problems.append("session must be a non-empty string when present")
        elif not _SESSION_RE.match(session):
            # Enforced here as well as in the topic layer so that the published
            # JSON Schema and the implementation cannot disagree.
            problems.append(
                "session must match [A-Za-z0-9._-]{1,64}: wildcards or '/' would let a "
                "peer escape its namespace on a pub/sub transport"
            )

    return tuple(problems)
