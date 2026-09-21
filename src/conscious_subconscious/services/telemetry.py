"""Prometheus-style metrics, rendered by hand.

A full client library is not worth a dependency here: the exposition format is
a dozen lines of text, and writing it directly means the output is exactly what
this service actually measures rather than what a library decided to expose.

Only counters and gauges are supported. Histograms are deliberately absent —
without them, nobody can accidentally start reporting p99 latencies computed
from four samples.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from ..core.errors import ConfigurationError

__all__ = ["Metrics", "render_prometheus", "escape_label"]

#: Prefix on every metric name, so this service cannot collide with another.
NAMESPACE = "conscious_subconscious"


def escape_label(value: str) -> str:
    """Escape a Prometheus label value."""
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


@dataclass(slots=True)
class _Sample:
    name: str
    help_text: str
    labels: tuple[str, ...] = ()


class Metrics:
    """A tiny thread-safe counter/gauge registry."""

    def __init__(self) -> None:
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._gauges: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._help: dict[str, str] = {}
        self._label_names: dict[str, tuple[str, ...]] = {}
        self._lock = threading.Lock()

    def _register(self, name: str, help_text: str, labels: Iterable[str]) -> None:
        if not name:
            raise ConfigurationError("metric name must be non-empty")
        existing = self._help.get(name)
        if existing is None:
            self._help[name] = help_text
            self._label_names[name] = tuple(labels)
        elif existing != help_text:
            raise ConfigurationError(f"metric {name!r} already registered with different help text")

    def inc(self, name: str, help_text: str = "", amount: float = 1.0, **labels: str) -> None:
        self._register(name, help_text, labels)
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + amount

    def set(self, name: str, value: float, help_text: str = "", **labels: str) -> None:
        self._register(name, help_text, labels)
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            self._gauges[key] = float(value)

    def counter_value(self, name: str, **labels: str) -> float:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            return self._counters.get(key, 0.0)

    def gauge_value(self, name: str, **labels: str) -> float:
        key = (name, tuple(sorted(labels.items())))
        with self._lock:
            return self._gauges.get(key, 0.0)

    def snapshot(self) -> dict[str, float]:
        """Flat ``name{labels}`` -> value view, for the JSON status endpoint."""
        with self._lock:
            combined: dict[str, float] = {}
            for (name, labels), value in self._counters.items():
                combined[_render_key(name, labels)] = value
            for (name, labels), value in self._gauges.items():
                combined[_render_key(name, labels)] = value
        return combined


def _render_key(name: str, labels: tuple[tuple[str, str], ...]) -> str:
    if not labels:
        return name
    inner = ",".join(f'{key}="{escape_label(value)}"' for key, value in labels)
    return f"{name}{{{inner}}}"


def render_prometheus(metrics: Metrics) -> str:
    """Render the registry in Prometheus text exposition format (version 0.0.4)."""
    lines: list[str] = []
    with metrics._lock:  # noqa: SLF001 - same module owns the layout
        counters = dict(metrics._counters)
        gauges = dict(metrics._gauges)
        help_text = dict(metrics._help)

    grouped: dict[str, list[tuple[tuple[tuple[str, str], ...], float]]] = {}
    for (name, labels), value in counters.items():
        grouped.setdefault(name, []).append((labels, value))
    for (name, labels), value in gauges.items():
        grouped.setdefault(name, []).append((labels, value))

    for name in sorted(grouped):
        full = name if name.startswith(f"{NAMESPACE}_") else f"{NAMESPACE}_{name}"
        description = help_text.get(name, "")
        if description:
            lines.append(f"# HELP {full} {description}")
        kind = "counter" if any(key[0] == name for key in counters) else "gauge"
        lines.append(f"# TYPE {full} {kind}")
        for labels, value in sorted(grouped[name]):
            rendered_labels = ""
            if labels:
                inner = ",".join(
                    f'{key}="{escape_label(label_value)}"' for key, label_value in labels
                )
                rendered_labels = f"{{{inner}}}"
            lines.append(f"{full}{rendered_labels} {value:g}")
    lines.append("")
    return "\n".join(lines)


def standard_metrics(
    *,
    sessions_open: int,
    sessions_created: int,
    requests_total: Mapping[str, int],
    steps_total: int,
    rejected_requests: int,
) -> Metrics:
    """Build the service's standard metric set."""
    metrics = Metrics()
    metrics.set("sessions_open", float(sessions_open), "Simulation sessions currently open.")
    metrics.inc(
        "sessions_created_total",
        "Simulation sessions created since start.",
        float(sessions_created),
    )
    for reason, count in requests_total.items():
        metrics.inc("requests_total", "HTTP requests handled.", float(count), reason=reason)
    metrics.inc("steps_total", "Simulation steps executed.", float(steps_total))
    metrics.inc(
        "rejected_requests_total",
        "Requests rejected by authentication or rate limiting.",
        float(rejected_requests),
    )
    return metrics


@dataclass(slots=True)
class StandardCounters:
    """Mutable counters the app increments as it serves requests."""

    sessions_created: int = 0
    steps_total: int = 0
    rejected_requests: int = 0
    requests_by_status: dict[str, int] = field(default_factory=dict)

    def record_request(self, status: str) -> None:
        self.requests_by_status[status] = self.requests_by_status.get(status, 0) + 1

    def as_metrics(self, *, sessions_open: int) -> Metrics:
        return standard_metrics(
            sessions_open=sessions_open,
            sessions_created=self.sessions_created,
            requests_total=self.requests_by_status,
            steps_total=self.steps_total,
            rejected_requests=self.rejected_requests,
        )
