"""Session management for the API.

Each session owns exactly one :class:`~conscious_subconscious.model.engine.SimulationEngine`.
Two rules keep that safe under a web server:

**One writer per engine.** The engine mutates a tissue scalar and an attention
budget; two concurrent ``step`` calls would interleave and produce a state that
corresponds to no configuration. Every mutation therefore takes the session lock,
and reads that only need a consistent snapshot take it too.

**Bounded and reaped.** A session holds a full time series in memory. The manager
caps how many exist and expires idle ones, because "unbounded in-memory growth"
is the failure mode every demo API ships with.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from ..core.errors import ConfigurationError
from ..model.engine import RunConfig, SimulationEngine, SimulationResult

__all__ = ["Session", "SessionManager", "SessionNotFound", "SessionLimitReached"]


class SessionNotFound(KeyError):
    """No session with that identifier (or it expired)."""


class SessionLimitReached(RuntimeError):
    """The manager is at capacity and cannot evict anything."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class Session:
    """One running simulation plus its bookkeeping."""

    id: str
    engine: SimulationEngine
    created_at: datetime = field(default_factory=_now)
    last_access: datetime = field(default_factory=_now)
    lock: threading.RLock = field(default_factory=threading.RLock)
    commands_applied: int = 0

    def touch(self) -> None:
        self.last_access = _now()

    def age_seconds(self, *, now: datetime | None = None) -> float:
        return ((now or _now()) - self.created_at).total_seconds()

    def idle_seconds(self, *, now: datetime | None = None) -> float:
        return ((now or _now()) - self.last_access).total_seconds()

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "last_access": self.last_access.isoformat(),
            "age_seconds": round(self.age_seconds(), 3),
            "idle_seconds": round(self.idle_seconds(), 3),
            "commands_applied": self.commands_applied,
            **self.engine.snapshot(),
        }


class SessionManager:
    """Thread-safe registry of simulation sessions."""

    def __init__(self, *, max_sessions: int = 16, ttl_seconds: float = 3600.0) -> None:
        if max_sessions < 1:
            raise ConfigurationError("max_sessions must be at least 1")
        if ttl_seconds <= 0:
            raise ConfigurationError("ttl_seconds must be positive")
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    # -- lifecycle ---------------------------------------------------------
    def create(self, config: RunConfig | None = None) -> Session:
        """Create a session, evicting expired ones first."""
        with self._lock:
            self.reap()
            if len(self._sessions) >= self.max_sessions:
                raise SessionLimitReached(
                    f"{self.max_sessions} sessions are already open; close one or "
                    "wait for the idle timeout"
                )
            session_id = uuid.uuid4().hex[:16]
            session = Session(id=session_id, engine=SimulationEngine(config))
            self._sessions[session_id] = session
            return session

    def get(self, session_id: str) -> Session:
        """Fetch a session, refreshing its idle timer."""
        with self._lock:
            try:
                session = self._sessions[session_id]
            except KeyError as exc:
                raise SessionNotFound(session_id) from exc
            session.touch()
            return session

    def peek(self, session_id: str) -> Session:
        """Fetch a session without refreshing its idle timer."""
        with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise SessionNotFound(session_id) from exc

    def delete(self, session_id: str) -> None:
        with self._lock:
            if self._sessions.pop(session_id, None) is None:
                raise SessionNotFound(session_id)

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            return tuple(sorted(self._sessions))

    def __len__(self) -> int:
        with self._lock:
            return len(self._sessions)

    # -- maintenance -------------------------------------------------------
    def reap(self) -> tuple[str, ...]:
        """Drop sessions idle longer than the TTL. Returns the removed ids."""
        cutoff = _now() - timedelta(seconds=self.ttl_seconds)
        with self._lock:
            expired = [
                session_id
                for session_id, session in self._sessions.items()
                if session.last_access < cutoff
            ]
            for session_id in expired:
                del self._sessions[session_id]
            return tuple(sorted(expired))

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    # -- operations --------------------------------------------------------
    def step(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        with session.lock:
            return session.engine.step()

    def run_to(self, session_id: str, hours: float) -> SimulationResult:
        session = self.get(session_id)
        with session.lock:
            return session.engine.run_to(hours)

    def run(self, session_id: str) -> SimulationResult:
        session = self.get(session_id)
        with session.lock:
            return session.engine.run()

    def command(self, session_id: str, name: str, **kwargs: Any) -> dict[str, Any]:
        session = self.get(session_id)
        with session.lock:
            result = session.engine.command(name, **kwargs)
            session.commands_applied += 1
            return result

    def snapshot(self, session_id: str) -> dict[str, Any]:
        session = self.get(session_id)
        with session.lock:
            return session.as_dict()

    def result(self, session_id: str) -> SimulationResult | None:
        session = self.get(session_id)
        with session.lock:
            return session.engine.result
