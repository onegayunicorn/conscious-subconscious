"""Transports.

A transport moves :class:`~conscious_subconscious.protocols.envelope.Envelope`
objects between two endpoints. Sockets are not opened here; concrete transports
(WebSocket, MQTT, serial) live with the service and device layers that need
them. The in-process transport exists so that everything above the wire can be
tested without a network, a broker or a port binding.

That is not just test convenience. It is the reason the protocol layer can be
exercised in CI on three operating systems in under a second.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from collections.abc import Mapping
from typing import Any

from ..core.errors import ProtocolError
from .envelope import Envelope

__all__ = ["Transport", "InProcessTransport", "make_pair"]


class Transport(ABC):
    """A bidirectional, message-oriented channel."""

    #: Human-readable name used in logs and error messages.
    name: str = "transport"

    @abstractmethod
    def send(self, message: Envelope | Mapping[str, Any]) -> None:
        """Send one message. Must either succeed or raise."""

    @abstractmethod
    def receive(self, timeout: float | None = None) -> Envelope | None:
        """Return the next message, or ``None`` if none arrived in time."""

    @abstractmethod
    def close(self) -> None:
        """Release resources. Idempotent."""

    @property
    def closed(self) -> bool:
        return getattr(self, "_closed", False)

    def __enter__(self) -> Transport:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


class InProcessTransport(Transport):
    """One end of an in-memory pair.

    ``max_queue`` is finite on purpose: an unbounded queue turns a slow consumer
    into a memory leak, which is exactly the failure a backpressure-free
    protocol design invites.
    """

    name = "in-process"

    def __init__(self, *, max_queue: int = 1024, label: str = "in-process") -> None:
        if max_queue <= 0:
            raise ValueError("max_queue must be positive")
        self._inbox: deque[Envelope] = deque()
        self._outbox: deque[Envelope] | None = None
        self._max_queue = max_queue
        self._closed = False
        self.name = label

    def _bind(self, outbox: deque[Envelope]) -> None:
        self._outbox = outbox

    def send(self, message: Envelope | Mapping[str, Any]) -> None:
        if self._closed:
            raise ProtocolError(f"{self.name}: transport is closed")
        if self._outbox is None:
            raise ProtocolError(f"{self.name}: transport is not connected to a peer")
        envelope = message if isinstance(message, Envelope) else Envelope.from_dict(message)
        if len(self._outbox) >= self._max_queue:
            # Refusing is the honest behaviour. Silently dropping samples is how
            # a monitoring system ends up reporting a healthy average over an
            # unhealthy window.
            raise ProtocolError(
                f"{self.name}: peer queue is full ({self._max_queue} messages); refusing to drop"
            )
        self._outbox.append(envelope)

    def receive(self, timeout: float | None = None) -> Envelope | None:
        if self._closed:
            return None
        if not self._inbox:
            return None
        if timeout is not None and timeout < 0:
            raise ValueError("timeout must be non-negative")
        return self._inbox.popleft()

    def close(self) -> None:
        self._closed = True
        self._inbox.clear()

    @property
    def pending(self) -> int:
        return len(self._inbox)


def make_pair(
    left_label: str = "client", right_label: str = "server", *, max_queue: int = 1024
) -> tuple[InProcessTransport, InProcessTransport]:
    """Create two connected endpoints: what ``left`` sends, ``right`` receives."""
    left = InProcessTransport(max_queue=max_queue, label=left_label)
    right = InProcessTransport(max_queue=max_queue, label=right_label)
    left._bind(right._inbox)
    right._bind(left._inbox)
    return left, right
