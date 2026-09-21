"""A small synchronous event bus.

Subsystems announce what they did (``tissue.repair``, ``conscious.focus``,
``attention.fatigued``) instead of returning it up the call stack. That keeps
the orchestrator shallow and gives the report, the API stream and the test
suite the same view of a run.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

__all__ = ["Event", "EventBus", "EventKind"]


class EventKind:
    """Well-known event names.

    Plain strings so third-party modules can emit their own names without
    editing this class.
    """

    RUN_START = "run.start"
    RUN_END = "run.end"
    TISSUE_REPAIR = "tissue.repair"
    FIELD_DECAY = "field.decay"
    CONSCIOUS_FOCUS = "conscious.focus"
    CONSCIOUS_RELEASE = "conscious.release"
    ATTENTION_FATIGUE = "attention.fatigued"
    ATTENTION_RECOVERED = "attention.recovered"
    MODULE_STEP = "module.step"
    DEVICE_READ = "device.read"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class Event:
    """One immutable observation, timestamped on the virtual clock."""

    t_hours: float
    kind: str
    source: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "t_hours": self.t_hours,
            "kind": self.kind,
            "source": self.source,
            "payload": dict(self.payload),
        }


class EventBus:
    """Records events and lets subscribers observe new ones.

    History is bounded so a long sweep cannot exhaust memory. When the bound
    is hit the *oldest* events are dropped and ``dropped`` counts the loss, so
    a report can say it truncated rather than silently lying about totals.
    """

    __slots__ = ("_history", "_subscribers", "_new", "_dropped", "_limit")

    def __init__(self, history_limit: int = 20_000) -> None:
        if history_limit <= 0:
            raise ValueError("history_limit must be positive")
        self._limit = history_limit
        self._history: deque[Event] = deque(maxlen=history_limit)
        self._new: list[Event] = []
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._dropped = 0

    @property
    def dropped(self) -> int:
        return self._dropped

    def subscribe(self, kind: str, handler: Callable[[Event], None]) -> None:
        """Call ``handler`` for every future event of ``kind`` (or ``"*"``)."""
        self._subscribers.setdefault(kind, []).append(handler)

    def emit(self, event: Event) -> None:
        if len(self._history) == self._limit:
            self._dropped += 1
        self._history.append(event)
        self._new.append(event)
        for handler in self._subscribers.get(event.kind, ()):
            handler(event)
        for handler in self._subscribers.get("*", ()):
            if event.kind != "*":
                handler(event)

    def publish(
        self,
        t_hours: float,
        kind: str,
        source: str,
        **payload: Any,
    ) -> Event:
        """Build and emit an event in one call."""
        event = Event(t_hours=t_hours, kind=kind, source=source, payload=payload)
        self.emit(event)
        return event

    def drain(self) -> tuple[Event, ...]:
        """Return events emitted since the last drain and clear the buffer."""
        pending = tuple(self._new)
        self._new.clear()
        return pending

    @property
    def history(self) -> tuple[Event, ...]:
        return tuple(self._history)

    def of_kind(self, kind: str) -> tuple[Event, ...]:
        return tuple(e for e in self._history if e.kind == kind)

    def counts(self) -> dict[str, int]:
        return dict(Counter(e.kind for e in self._history))

    def __iter__(self) -> Iterator[Event]:
        return iter(self._history)

    def __len__(self) -> int:
        return len(self._history)
