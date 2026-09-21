"""Markdown reports.

Two rules shape everything here:

1. **A number never appears without its provenance nearby.** The provenance
   summary sits above the results table, not in an appendix.
2. **A missing value is written as an em dash, not as 0.** "Never reached
   50% repair in 72 hours" and "reached it in zero hours" are opposite
   statements and must not render identically.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .. import DISCLAIMER, PROVENANCE_POLICY
from ..model.engine import SimulationResult

__all__ = ["render_report", "render_comparison", "EM_DASH"]

EM_DASH = "—"

#: Metrics shown in the headline table, with display formatting.
_HEADLINE: tuple[tuple[str, str, str], ...] = (
    ("time_to_50pct_repair_hours", "Time to 50% repair", "h"),
    ("time_to_full_repair_hours", "Time to full repair", "h"),
    ("area_under_damage_integrity_hours", "Area under damage", "integrity·h"),
    ("mean_integrity", "Mean integrity", ""),
    ("final_integrity", "Final integrity", ""),
    ("focus_hours", "Attention engaged", "h"),
    ("attention_spent", "Attention spent", "budget units"),
    ("attention_attributable_fraction", "Repair attributable to attention", ""),
    ("fatigue_episodes", "Fatigue episodes", ""),
)

_COMPARISON: tuple[tuple[str, str], ...] = (
    ("time_to_50pct_repair_hours", "Time to 50% repair (h)"),
    ("time_to_full_repair_hours", "Time to full repair (h)"),
    ("area_under_damage_integrity_hours", "Area under damage"),
    ("attention_attributable_fraction", "Attributable to attention"),
    ("focus_hours", "Attention engaged (h)"),
    ("fatigue_episodes", "Fatigue episodes"),
)


def _fmt(value: Any) -> str:
    if value is None:
        return EM_DASH
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if value == 0.0:
            return "0"
        if abs(value) >= 1000 or (abs(value) < 0.001):
            return f"{value:.3g}"
        return f"{value:.4f}".rstrip("0").rstrip(".")
    if isinstance(value, int):
        return str(value)
    return str(value)


def _reproduction_command(result: SimulationResult) -> str:
    config = result.config
    parts = [
        "cs-sim run",
        f"--scenario {config.scenario}",
        f"--seed {config.seed}",
        f"--dt {config.dt_hours}",
        f"--horizon {config.horizon_hours}",
        f"--modules {','.join(config.modules) if config.modules else 'none'}",
    ]
    for key, value in sorted(config.overrides.items()):
        parts.append(f"--set {key}={value}")
    return " ".join(parts)


def render_report(result: SimulationResult, *, title: str | None = None) -> str:
    """Render a single run as Markdown."""
    metrics = result.metrics
    summary = result.provenance_summary
    lines: list[str] = []

    lines.append(f"# {title or f'Simulation report — {result.scenario}'}")
    lines.append("")
    lines.append(
        "> **Boundary.** This project is an educational and artistic simulation. "
        "It is not a medical device and provides no medical advice. "
        "See `DISCLAIMER.md`."
    )
    lines.append("")
    lines.append(f"- **Scenario:** `{result.scenario}`")
    lines.append(f"- **Seed:** {result.seed}")
    lines.append(
        f"- **Time step:** {result.config.dt_hours} h over {result.config.horizon_hours} h"
    )
    lines.append(
        f"- **Tissue model:** {result.config.tissue_name}, "
        f"initial integrity {result.config.initial_integrity}"
    )
    lines.append(
        f"- **Modules:** {', '.join(result.module_names) if result.module_names else 'none'}"
    )
    lines.append(f"- **Focus policy:** `{result.config.focus_policy}`")
    lines.append("")

    lines.append("## Provenance of the numbers")
    lines.append("")
    lines.append(
        f"{summary['unsupported']} of {summary['total']} parameters carry no empirical "
        f"support ({summary['unsupported_fraction']:.0%}). Results that depend on them "
        "describe the model, not a body."
    )
    lines.append("")
    lines.append("| Parameter | Value | Unit | Provenance |")
    lines.append("|---|---:|---|---|")
    key_params = (
        "conscious.neural_drive_coupling",
        "conscious.neural_drive_gain",
        "subconscious.base_repair_rate",
        "module.inflammation.repair_inhibition",
        "module.circadian.period_hours",
    )
    for entry in result.provenance:
        if entry["key"] in key_params:
            lines.append(
                f"| `{entry['key']}` | {_fmt(entry['value'])} | {entry['unit']} | "
                f"{entry['provenance']} |"
            )
    lines.append("")
    lines.append(f"_{PROVENANCE_POLICY}_")
    lines.append("")

    lines.append("## Headline result")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    for key, label, unit in _HEADLINE:
        rendered = _fmt(metrics.get(key))
        if unit and rendered != EM_DASH:
            rendered = f"{rendered} {unit}"
        lines.append(f"| {label} | {rendered} |")
    lines.append("")

    lines.append("## What this does not show")
    lines.append("")
    lines.append(
        "- It does not show that attention, visualisation or willpower changes the rate "
        "of tissue repair in a human body."
    )
    lines.append(
        "- It does not predict healing times for any real injury. No clinical endpoint, "
        "population or measurement is modelled."
    )
    lines.append(
        "- It does not estimate the size of any real effect. Every constant that carries "
        "the effect is tagged `invented` or `assumed`."
    )
    lines.append("")

    lines.append("## Reproduce this run")
    lines.append("")
    lines.append("```bash")
    lines.append(_reproduction_command(result))
    lines.append("```")
    lines.append("")
    lines.append(
        f"Digests — parameters `{result.parameter_digest[:16]}`, config "
        f"`{result.config_digest[:16]}`, run `{result.run_digest[:16]}`. "
        "A matching run digest means byte-identical results."
    )
    lines.append("")
    lines.append(f"---\n\n_{DISCLAIMER}_")
    lines.append("")
    return "\n".join(lines)


def render_comparison(
    results: Sequence[SimulationResult], *, baseline_name: str = "baseline"
) -> str:
    """Render several runs side by side, with deltas relative to the baseline."""
    if not results:
        raise ValueError("nothing to compare")

    by_name = {r.scenario: r for r in results}
    baseline = by_name.get(baseline_name)
    lines: list[str] = []

    lines.append("# Scenario comparison")
    lines.append("")
    lines.append(
        f"{len(results)} runs, identical parameters and seed unless a scenario overrides "
        "them. Deltas are relative to "
        + (f"`{baseline_name}`." if baseline else f"`{baseline_name}` (not present in this set).")
    )
    lines.append("")

    names = [r.scenario for r in results]
    lines.append("| Metric | " + " | ".join(f"`{n}`" for n in names) + " |")
    lines.append("|---|" + "---:|" * len(names))
    for key, label in _COMPARISON:
        cells = [_fmt(by_name[n].metrics.get(key)) for n in names]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("")

    if baseline is not None and len(results) > 1:
        lines.append("### Change relative to baseline")
        lines.append("")
        lines.append("| Scenario | Time to 50% repair | Area under damage | Attention engaged |")
        lines.append("|---|---:|---:|---:|")
        base_t50 = baseline.metrics.get("time_to_50pct_repair_hours")
        base_auc = baseline.metrics.get("area_under_damage_integrity_hours")
        for result in results:
            name = result.scenario
            t50 = result.metrics.get("time_to_50pct_repair_hours")
            auc = result.metrics.get("area_under_damage_integrity_hours")
            if name == baseline_name:
                lines.append(
                    f"| `{name}` | {EM_DASH} | {EM_DASH} | "
                    f"{_fmt(result.metrics.get('focus_hours'))} h |"
                )
                continue

            def _relative(value: float | None, base: float | None) -> str:
                if value is None or base in (None, 0):
                    return EM_DASH
                return f"{(value - base) / base * 100:+.1f}%"

            lines.append(
                f"| `{name}` | {_relative(t50, base_t50)} | {_relative(auc, base_auc)} | "
                f"{_fmt(result.metrics.get('focus_hours'))} h |"
            )
        lines.append("")
        lines.append(
            "A negative percentage is a shorter time or a smaller area, i.e. the model "
            "repaired faster. It is a property of the coupling constant, not evidence "
            "about people."
        )
        lines.append("")

    lines.append("### Scenario notes")
    lines.append("")
    for result in results:
        lines.append(
            f"- **`{result.scenario}`** — seed {result.seed}, digest `{result.run_digest[:16]}`"
        )
    lines.append("")
    lines.append(f"---\n\n_{DISCLAIMER}_")
    lines.append("")
    return "\n".join(lines)
