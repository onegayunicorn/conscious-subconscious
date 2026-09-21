"""Parameter sweeps and one-factor sensitivity analysis.

This is the most scientifically useful thing in the package.

The model's headline result — "attention speeds repair" — comes from a
constant with no empirical support. The honest question is not "is the effect
big?" but "how much of the conclusion rests on a number nobody measured?" A
sweep answers that directly: hold everything else fixed, vary the invented
constant across a plausible range, and print what happens.

If the sign of the conclusion flips inside the range, the result is a property
of the choice of constant. Saying that out loud is cheaper than being wrong
quietly.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from ..core.errors import ConfigurationError
from ..core.params import ParameterSet
from ..model.engine import SimulationEngine, SimulationResult
from ..parameters import default_parameters
from .scenarios import get_scenario

__all__ = [
    "SweepPoint",
    "SweepResult",
    "sweep_parameter",
    "one_factor_sensitivity",
    "render_sweep_markdown",
    "render_sensitivity_markdown",
]

_SWEEP_METRICS: tuple[tuple[str, str], ...] = (
    ("time_to_50pct_repair_hours", "Time to 50% repair (h)"),
    ("time_to_full_repair_hours", "Time to full repair (h)"),
    ("area_under_damage_integrity_hours", "Area under damage"),
    ("attention_attributable_fraction", "Attributable to attention"),
)


@dataclass(frozen=True, slots=True)
class SweepPoint:
    """One parameter value and the run it produced."""

    value: float
    metrics: dict[str, Any]
    run_digest: str

    def as_dict(self) -> dict[str, Any]:
        return {"value": self.value, "metrics": dict(self.metrics), "run_digest": self.run_digest}


@dataclass(frozen=True, slots=True)
class SweepResult:
    """A one-dimensional sweep of a single parameter."""

    parameter: str
    scenario: str
    seed: int
    default_value: float | None
    points: tuple[SweepPoint, ...]
    provenance: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "parameter": self.parameter,
            "scenario": self.scenario,
            "seed": self.seed,
            "default_value": self.default_value,
            "provenance": self.provenance,
            "points": [p.as_dict() for p in self.points],
        }

    def spread(self, metric: str) -> float:
        """Absolute spread of ``metric`` across the sweep, ignoring missing values."""
        values = [
            float(p.metrics[metric]) for p in self.points if p.metrics.get(metric) is not None
        ]
        if len(values) < 2:
            return 0.0
        return max(values) - min(values)

    def is_monotonic(self, metric: str = "time_to_50pct_repair_hours") -> bool:
        """True when the metric never reverses direction as the parameter rises.

        This is the question that matters for a one-dimensional sweep: if the
        metric goes down, then up, then down again, the sweep has found an
        interior optimum and the "effect" is not a direction at all. Note that
        a *flat* sweep is monotone too — it means the parameter does nothing in
        this range, which is also worth knowing.
        """
        numbers: list[float] = []
        for point in self.points:
            value = point.metrics.get(metric)
            if value is None:
                return False
            numbers.append(float(value))
        deltas = [
            later - earlier
            for earlier, later in zip(numbers, numbers[1:], strict=False)
            if abs(later - earlier) > 1e-12
        ]
        if not deltas:
            return True
        return all(d > 0 for d in deltas) or all(d < 0 for d in deltas)


def _run(
    scenario: str, seed: int, overrides: dict[str, float], params: ParameterSet
) -> SimulationResult:
    config = get_scenario(scenario).build(seed=seed, overrides=overrides)
    return SimulationEngine(config, params).run()


def sweep_parameter(
    parameter: str,
    values: Sequence[float],
    *,
    scenario: str = "focused",
    seed: int = 20260921,
    parameters: ParameterSet | None = None,
) -> SweepResult:
    """Run ``scenario`` once per value of ``parameter``."""
    if not values:
        raise ConfigurationError("a sweep needs at least one value")
    params = parameters if parameters is not None else default_parameters()
    if parameter not in params:
        raise ConfigurationError(
            f"unknown parameter {parameter!r}; run 'cs-sim parameters' to list them"
        )

    points: list[SweepPoint] = []
    for value in values:
        result = _run(scenario, seed, {parameter: float(value)}, params)
        points.append(
            SweepPoint(
                value=float(value),
                metrics=dict(result.metrics),
                run_digest=result.run_digest,
            )
        )
    return SweepResult(
        parameter=parameter,
        scenario=scenario,
        seed=seed,
        default_value=params.value(parameter),
        points=tuple(points),
        provenance=params[parameter].provenance.value,
    )


def one_factor_sensitivity(
    *,
    parameter_keys: Iterable[str] | None = None,
    scenario: str = "focused",
    baseline_scenario: str = "baseline",
    factor: float = 0.5,
    seed: int = 20260921,
    parameters: ParameterSet | None = None,
    metric: str = "time_to_50pct_repair_hours",
) -> list[dict[str, Any]]:
    """Rank parameters by how much the headline metric moves when they are perturbed.

    Defaults to the parameters with no empirical support, because those are the
    ones whose influence is worth knowing about. Each is multiplied by
    ``1 + factor`` and by ``1 - factor`` and the largest absolute move in
    ``metric`` is recorded.
    """
    if not 0.0 < factor < 1.0:
        raise ConfigurationError("factor must lie strictly between 0 and 1")
    params = parameters if parameters is not None else default_parameters()

    if parameter_keys is None:
        keys = [p.key for p in params.unsupported()]
    else:
        keys = list(parameter_keys)

    reference = _run(baseline_scenario, seed, {}, params)
    reference_metric = _positive_metric(reference.metrics, metric)

    rows: list[dict[str, Any]] = []
    for key in keys:
        if key not in params:
            raise ConfigurationError(f"unknown parameter {key!r}")
        base_value = params.value(key)
        if base_value == 0.0:
            # A multiply-by-factor perturbation cannot move a zero-valued knob,
            # so probe it by nudging upward from zero instead.
            candidates = (0.0, 1.0)
        else:
            candidates = (base_value * (1.0 - factor), base_value * (1.0 + factor))

        spec = params[key]
        deltas: list[float] = []
        for value in candidates:
            # Clamp to the declared bounds rather than discarding the probe. A
            # parameter capped at 1.0 would otherwise be silently untestable in
            # the upward direction, which is exactly the direction that matters.
            if spec.minimum is not None:
                value = max(value, spec.minimum)
            if spec.maximum is not None:
                value = min(value, spec.maximum)
            if abs(value - base_value) < 1e-12:
                continue
            result = _run(scenario, seed, {key: value}, params)
            moved = _positive_metric(result.metrics, metric)
            deltas.append((moved - reference_metric) / reference_metric)
        if not deltas:
            continue
        largest = max(deltas, key=abs)
        rows.append(
            {
                "parameter": key,
                "provenance": params[key].provenance.value,
                "default_value": base_value,
                "metric": metric,
                "reference_value": reference_metric,
                "max_relative_change": round(largest, 6),
                "absolute_relative_change": round(abs(largest), 6),
            }
        )

    rows.sort(key=lambda row: row["absolute_relative_change"], reverse=True)
    return rows


def _positive_metric(metrics: dict[str, Any], metric: str) -> float:
    value = metrics.get(metric)
    if value is None:
        raise ConfigurationError(
            f"metric {metric!r} is missing from the run; cannot use it for sensitivity"
        )
    number = float(value)
    if number == 0.0:
        raise ConfigurationError(
            f"metric {metric!r} is zero in the reference run, so relative change is undefined"
        )
    return number


def render_sweep_markdown(sweep: SweepResult) -> str:
    """Render a sweep as Markdown."""
    lines = [
        f"# Parameter sweep — `{sweep.parameter}`",
        "",
        f"- **Scenario:** `{sweep.scenario}`",
        f"- **Seed:** {sweep.seed}",
        f"- **Declared provenance of this parameter:** `{sweep.provenance}`",
        f"- **Default value:** {sweep.default_value}",
        "",
    ]
    if sweep.provenance in {"assumed", "invented"}:
        lines += [
            "> This parameter has **no empirical support**. Everything below is a "
            "consequence of that choice, not a measurement.",
            "",
        ]
    lines.append(
        "| " + sweep.parameter + " | " + " | ".join(label for _, label in _SWEEP_METRICS) + " |"
    )
    lines.append("|---:|" + "---:|" * len(_SWEEP_METRICS))
    for point in sweep.points:
        cells = []
        for key, _ in _SWEEP_METRICS:
            value = point.metrics.get(key)
            cells.append("—" if value is None else f"{float(value):.4g}")
        lines.append(f"| {point.value:g} | " + " | ".join(cells) + " |")
    lines.append("")
    monotone = sweep.is_monotonic()
    lines.append(
        "The headline metric is "
        + ("**monotone**" if monotone else "**not monotone**")
        + " across this sweep, so the conclusion "
        + (
            "keeps its direction over the range tested."
            if monotone
            else "reverses direction inside the range tested — the range contains a "
            "turning point and the direction of the effect is not a property of the model."
        )
    )
    lines.append("")
    return "\n".join(lines)


def render_sensitivity_markdown(
    rows: Sequence[dict[str, Any]], *, scenario: str = "focused"
) -> str:
    """Render a sensitivity ranking as Markdown."""
    lines = [
        "# One-factor sensitivity",
        "",
        f"Each parameter below was multiplied by 0.5 and by 1.5 and the run repeated "
        f"against scenario `{scenario}`. The table ranks parameters by the largest "
        "relative move they produced in the reference metric.",
        "",
        "> Parameters with `assumed` or `invented` provenance are free knobs. A large "
        "number here does not mean the parameter matters in reality — it means the "
        "model's output depends on a guess.",
        "",
        "| Parameter | Provenance | Default | Max relative change |",
        "|---|---|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['parameter']}` | {row['provenance']} | {row['default_value']:g} | "
            f"{row['max_relative_change']:+.2%} |"
        )
    lines.append("")
    return "\n".join(lines)
