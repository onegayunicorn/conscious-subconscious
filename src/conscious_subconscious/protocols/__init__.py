"""The wire protocol: envelope, JSON-RPC control, topics, framing, transports.

The TypeScript console consumes the same contract, defined once as JSON Schema
in ``protocols/schemas/`` at the repository root and checked by
``tests/conformance``. When the two implementations disagree, the schema is the
tie-breaker.
"""

from __future__ import annotations

from .codec import DEFAULT_MAX_LINE_BYTES, NdjsonDecoder, decode, encode
from .envelope import (
    ENVELOPE_KEYS,
    SCHEMA_VERSION,
    Envelope,
    MessageType,
    new_envelope,
    validate_envelope,
)
from .jsonrpc import (
    ErrorCode,
    error,
    is_error,
    is_request,
    is_response,
    notification,
    request,
    response,
    validate_jsonrpc,
)
from .topics import (
    KINDS,
    TOPIC_ROOT,
    TOPIC_VERSION,
    device_topic,
    device_wildcard,
    parse_topic,
    session_topic,
    session_wildcard,
    validate_identifier,
)
from .transport import InProcessTransport, Transport, make_pair

__all__ = [
    "DEFAULT_MAX_LINE_BYTES",
    "ENVELOPE_KEYS",
    "ErrorCode",
    "Envelope",
    "InProcessTransport",
    "KINDS",
    "MessageType",
    "NdjsonDecoder",
    "SCHEMA_VERSION",
    "TOPIC_ROOT",
    "TOPIC_VERSION",
    "Transport",
    "decode",
    "device_topic",
    "device_wildcard",
    "encode",
    "error",
    "is_error",
    "is_request",
    "is_response",
    "make_pair",
    "new_envelope",
    "notification",
    "parse_topic",
    "request",
    "response",
    "session_topic",
    "session_wildcard",
    "validate_envelope",
    "validate_identifier",
    "validate_jsonrpc",
]
