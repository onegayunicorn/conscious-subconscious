"""Framing: newline-delimited JSON.

NDJSON is chosen because it is debuggable with ``cat``, trivially streamable,
and has no length-prefix parsing bugs. It also has one classic failure mode —
a peer that never sends a newline can grow a buffer without bound — which is
why the decoder enforces a maximum line length and *fails* rather than
truncating. A truncated message that still parses is far more dangerous than a
rejected one.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ..core.errors import ProtocolError

__all__ = ["DEFAULT_MAX_LINE_BYTES", "encode", "decode", "NdjsonDecoder"]

DEFAULT_MAX_LINE_BYTES = 1_048_576


def encode(message: Mapping[str, Any]) -> bytes:
    """Serialise a message as one newline-terminated line of UTF-8 JSON."""
    try:
        body = json.dumps(message, sort_keys=True, separators=(",", ":"), default=str)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(f"message is not JSON-serialisable: {exc}") from exc
    if "\n" in body or "\r" in body:
        # json.dumps escapes control characters inside strings, so a raw
        # newline here would mean a caller smuggled one in via a custom default.
        raise ProtocolError("encoded message contains a raw newline; framing would break")
    return body.encode("utf-8") + b"\n"


def decode(line: bytes | str) -> dict[str, Any]:
    """Parse exactly one line. Rejects trailing data and non-objects."""
    text = line.decode("utf-8") if isinstance(line, bytes) else line
    text = text.rstrip("\r\n")
    if not text:
        raise ProtocolError("empty line cannot be decoded")
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ProtocolError("decoded message must be a JSON object")
    return parsed


@dataclass(slots=True)
class NdjsonDecoder:
    """Incremental decoder for a byte stream.

    Feed it whatever arrives; get back whole messages.
    """

    max_line_bytes: int = DEFAULT_MAX_LINE_BYTES
    _buffer: bytearray = field(default_factory=bytearray, init=False)
    _lines_decoded: int = field(default=0, init=False)

    def feed(self, chunk: bytes) -> list[dict[str, Any]]:
        """Append ``chunk`` and return every complete message now available."""
        if not isinstance(chunk, (bytes, bytearray)):
            raise ProtocolError("feed expects bytes")
        self._buffer.extend(chunk)

        messages: list[dict[str, Any]] = []
        while True:
            index = self._buffer.find(b"\n")
            if index < 0:
                break
            line = bytes(self._buffer[:index])
            del self._buffer[: index + 1]
            if not line.strip():
                continue
            messages.append(decode(line))
            self._lines_decoded += 1

        if len(self._buffer) > self.max_line_bytes:
            self._buffer.clear()
            raise ProtocolError(
                f"partial message exceeded {self.max_line_bytes} bytes without a newline; "
                "buffer discarded rather than truncated"
            )
        return messages

    @property
    def buffered_bytes(self) -> int:
        return len(self._buffer)

    @property
    def lines_decoded(self) -> int:
        return self._lines_decoded

    def reset(self) -> None:
        self._buffer.clear()
