"""Pipeline steps.

Each step is a small class with a ``run`` method and a declared ``uses`` name.
The registry means a DAG file can name a step without importing Python, and a
test can exercise a step in isolation with a hand-built context.

Convention: a step reads only from ``ctx.outputs`` (its declared dependencies)
and returns a plain dict. It never touches the filesystem except in ``Load*``
and ``Write*`` steps, which take their paths from explicit configuration.
"""

from __future__ import annotations

import csv
import json
from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, ClassVar, TypeVar

from ..core.errors import PipelineError
from .dsp import band_power, mean, resample_linear, rmssd_ms, stdev

__all__ = [
    "PipelineContext",
    "Step",
    "register_step",
    "get_step",
    "available_steps",
    "LoadCsvStep",
    "ValidateStep",
    "ResampleStep",
    "FeatureStep",
    "SummariseStep",
    "WriteJsonStep",
]

_REGISTRY: dict[str, type[Step]] = {}


class PipelineContext:
    """Mutable state passed between steps."""

    __slots__ = ("inputs", "workdir", "outputs", "log")

    def __init__(
        self,
        inputs: Mapping[str, Any] | None = None,
        workdir: Path | None = None,
    ) -> None:
        self.inputs: dict[str, Any] = dict(inputs or {})
        self.workdir = workdir or Path()
        self.outputs: dict[str, dict[str, Any]] = {}
        self.log: list[str] = []

    def output(self, step_name: str) -> dict[str, Any]:
        """Fetch a dependency's output. A missing dependency is a pipeline bug."""
        try:
            return self.outputs[step_name]
        except KeyError as exc:
            raise PipelineError(
                f"step output {step_name!r} is not available; check the DAG's 'needs'"
            ) from exc

    def record(self, message: str) -> None:
        self.log.append(message)

    def resolve(self, path: str) -> Path:
        """Resolve a configured path against the workdir unless it is absolute."""
        candidate = Path(path)
        return candidate if candidate.is_absolute() else (self.workdir / candidate)


class Step(ABC):
    """Base class for pipeline steps."""

    uses: ClassVar[str] = ""

    def __init__(self, name: str, params: Mapping[str, Any] | None = None) -> None:
        self.name = name
        self.params = dict(params or {})

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not cls.uses:
            raise PipelineError(f"{cls.__name__} must define a non-empty 'uses'")

    @abstractmethod
    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        """Execute the step and return its output mapping."""

    def required(self, key: str) -> Any:
        if key not in self.params:
            raise PipelineError(f"step {self.name!r} ({self.uses}) requires parameter {key!r}")
        return self.params[key]

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        """Parameter keys this step cannot run without.

        Declared so that a DAG can be validated when it is *loaded* rather than
        part-way through a run. A missing parameter discovered after three steps
        have already executed is a confusing failure; discovered at load time it
        is a one-line fix.
        """
        return ()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"{type(self).__name__}(name={self.name!r})"


_S = TypeVar("_S", bound=type[Step])


def register_step(cls: _S) -> _S:
    existing = _REGISTRY.get(cls.uses)
    if existing is not None and existing is not cls:
        raise PipelineError(f"step {cls.uses!r} is already registered by {existing.__name__}")
    _REGISTRY[cls.uses] = cls
    return cls


def available_steps() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def get_step(uses: str) -> type[Step]:
    try:
        return _REGISTRY[uses]
    except KeyError as exc:
        raise PipelineError(
            f"unknown step {uses!r}; available: {', '.join(available_steps())}"
        ) from exc


# ---------------------------------------------------------------------------
@register_step
class LoadCsvStep(Step):
    """Read a ``t_seconds,channel,value`` recording into memory.

    The same shape the serial and BLE adapters emit, so a recording made from
    live hardware is immediately pipeline-processable.
    """

    uses = "load_csv"

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        return ("path",)

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        path = ctx.resolve(str(self.required("path")))
        if not path.is_file():
            raise PipelineError(f"input file not found: {path}")
        rows: list[tuple[float, str, float]] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            required = {"t_seconds", "channel", "value"}
            if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
                raise PipelineError(
                    f"{path} must have columns {sorted(required)}; found {reader.fieldnames}"
                )
            for line_number, row in enumerate(reader, start=2):
                try:
                    rows.append(
                        (
                            float(row["t_seconds"]),
                            str(row["channel"]).strip(),
                            float(row["value"]),
                        )
                    )
                except (TypeError, ValueError) as exc:
                    raise PipelineError(f"{path}:{line_number} is malformed") from exc
        ctx.record(f"load_csv: {len(rows)} rows from {path}")
        return {"rows": rows, "path": str(path), "row_count": len(rows)}


@register_step
class ValidateStep(Step):
    """Quality gate. Fails the pipeline rather than passing junk downstream."""

    uses = "validate"

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        return ("source",)

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        source = ctx.output(str(self.required("source")))
        rows: list[tuple[float, str, float]] = list(source["rows"])
        min_rows = int(self.params.get("min_rows", 1))
        problems: list[str] = []

        if len(rows) < min_rows:
            problems.append(f"only {len(rows)} rows, minimum is {min_rows}")

        seen: set[tuple[float, str]] = set()
        duplicates = 0
        non_finite = 0
        for t_seconds, channel, value in rows:
            if value != value or value in (float("inf"), float("-inf")):
                non_finite += 1
            key = (t_seconds, channel)
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
            if not channel:
                problems.append("row with empty channel")

        if non_finite:
            problems.append(f"{non_finite} non-finite value(s)")
        tolerance = int(self.params.get("max_duplicate_timestamps", 0))
        if duplicates > tolerance:
            problems.append(
                f"{duplicates} duplicate (t, channel) pair(s), tolerance is {tolerance}"
            )

        if problems:
            raise PipelineError("validation failed: " + "; ".join(sorted(set(problems))))

        channels = sorted({channel for _, channel, _ in rows})
        ctx.record(f"validate: {len(rows)} rows across {len(channels)} channel(s)")
        return {"rows": rows, "channels": channels, "row_count": len(rows)}


@register_step
class ResampleStep(Step):
    """Resample one channel onto a uniform grid."""

    uses = "resample"

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        return ("source", "channel", "rate_hz")

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        source = ctx.output(str(self.required("source")))
        channel = str(self.required("channel"))
        rate_hz = float(self.required("rate_hz"))
        if rate_hz <= 0:
            raise PipelineError("rate_hz must be positive")

        rows: list[tuple[float, str, float]] = list(source["rows"])
        times = [t for t, name, _ in rows if name == channel]
        values = [v for _, name, v in rows if name == channel]
        if len(times) < 2:
            raise PipelineError(
                f"channel {channel!r} has {len(times)} sample(s); at least 2 are needed"
            )

        pairs = sorted(zip(times, values, strict=True))
        # Collapse duplicate timestamps by averaging instead of failing. At this
        # point the data has already passed the validate step, so a duplicate
        # here is a deliberate choice by the caller, not an unnoticed defect.
        collapsed_t: list[float] = []
        collapsed_v: list[float] = []
        for t_seconds, value in pairs:
            if collapsed_t and collapsed_t[-1] == t_seconds:
                collapsed_v[-1] = (collapsed_v[-1] + value) / 2.0
            else:
                collapsed_t.append(t_seconds)
                collapsed_v.append(value)

        step = 1.0 / rate_hz
        span = collapsed_t[-1] - collapsed_t[0]
        count = int(span * rate_hz) + 1
        if count < 2:
            raise PipelineError(f"resampled series would have {count} point(s)")
        target = [collapsed_t[0] + index * step for index in range(count)]
        resampled = resample_linear(collapsed_t, collapsed_v, target)

        ctx.record(f"resample: {channel} -> {count} points at {rate_hz} Hz")
        return {
            "channel": channel,
            "rate_hz": rate_hz,
            "times": target,
            "values": resampled,
            "count": count,
        }


@register_step
class FeatureStep(Step):
    """Per-channel descriptive and spectral features."""

    uses = "features"

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        return ("source",)

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        source = ctx.output(str(self.required("source")))
        rows: list[tuple[float, str, float]] = list(source["rows"])
        channels = sorted({channel for _, channel, _ in rows})
        if not channels:
            raise PipelineError("no channels to featurise")

        bands: list[dict[str, Any]] = list(self.params.get("bands", []))
        features: dict[str, dict[str, Any]] = {}

        for channel in channels:
            times = [t for t, name, _ in rows if name == channel]
            values = [v for _, name, v in rows if name == channel]
            if not values:
                continue
            rate = _estimate_rate(times)
            entry: dict[str, Any] = {
                "count": len(values),
                "mean": round(mean(values), 9),
                "stdev": round(stdev(values), 9),
                "min": round(min(values), 9),
                "max": round(max(values), 9),
                "duration_seconds": round(times[-1] - times[0], 9) if len(times) > 1 else 0.0,
                "estimated_rate_hz": round(rate, 6),
            }
            if channel in ("heart_rate", "rr_interval"):
                entry["rmssd_ms"] = (
                    None if len(values) < 2 else round(float(rmssd_ms(values) or 0.0), 6)
                )
            for band in bands:
                name = str(band.get("name", "band"))
                if rate <= 0:
                    entry[f"power_{name}"] = None
                    continue
                try:
                    entry[f"power_{name}"] = round(
                        band_power(
                            values,
                            sample_rate_hz=rate,
                            low_hz=float(band["low_hz"]),
                            high_hz=float(band["high_hz"]),
                        ),
                        9,
                    )
                except PipelineError:
                    # An out-of-range band is reported as absent, not as zero:
                    # zero would look like a measurement.
                    entry[f"power_{name}"] = None
            features[channel] = entry

        ctx.record(f"features: {len(features)} channel(s)")
        return {"features": features, "channels": channels}


@register_step
class SummariseStep(Step):
    """Fold several upstream feature blocks into one summary object."""

    uses = "summarise"

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        return ("sources",)

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        sources: Iterable[str] = self.required("sources")
        combined: dict[str, Any] = {}
        for step_name in sources:
            output = ctx.output(step_name)
            for key, value in output.items():
                if key in combined:
                    raise PipelineError(
                        f"summarise would overwrite key {key!r} from {step_name!r}; "
                        "rename the upstream output instead of losing data"
                    )
                combined[key] = value
        ctx.record(f"summarise: merged {len(list(sources))} source(s)")
        return combined


@register_step
class WriteJsonStep(Step):
    """Write the named keys of an upstream output to a JSON file."""

    uses = "write_json"

    @classmethod
    def required_params(cls) -> tuple[str, ...]:
        return ("source", "path")

    def run(self, ctx: PipelineContext) -> dict[str, Any]:
        source = ctx.output(str(self.required("source")))
        path = ctx.resolve(str(self.required("path")))
        keys = list(self.params.get("keys", []))
        payload = {key: source.get(key) for key in keys} if keys else dict(source)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        ctx.record(f"write_json: {path}")
        return {"path": str(path), "keys": sorted(payload)}


def _estimate_rate(times: list[float]) -> float:
    """Median-based sample-rate estimate.

    The median is used rather than the mean because a single dropped sample is
    otherwise enough to report a rate that never existed.
    """
    if len(times) < 2:
        return 0.0
    # Unequal lengths are intentional: consecutive-pair iteration.
    deltas = sorted(later - earlier for earlier, later in zip(times, times[1:], strict=False))
    if not deltas:
        return 0.0
    middle = deltas[len(deltas) // 2]
    return 0.0 if middle <= 0 else 1.0 / middle
