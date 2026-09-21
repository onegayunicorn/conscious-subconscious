"""``cs-sim`` — the command-line front end.

Exit codes
----------
0
    Success.
1
    A user-input problem (unknown scenario, bad ``--set``, bad range).
2
    A configuration error surfaced from the model layer.

Output is written to stdout unless ``--out`` is given, so the tool composes
with pipes. ``--json`` emits machine-readable output on the same channel.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .. import DISCLAIMER, __version__
from ..core.errors import ConsciousSubconsciousError
from ..core.params import ParameterSet
from ..model.engine import FOCUS_POLICIES, SimulationEngine, SimulationResult
from ..modules.registry import describe_all
from ..parameters import default_parameters
from .report import render_comparison, render_report
from .scenarios import (
    DEFAULT_COMPARISON,
    Scenario,
    builtin_scenarios,
    load_scenarios,
    scenario_names,
)
from .sweep import (
    one_factor_sensitivity,
    render_sensitivity_markdown,
    render_sweep_markdown,
    sweep_parameter,
)

__all__ = ["main", "build_parser"]


def _parse_overrides(pairs: Sequence[str]) -> dict[str, float]:
    overrides: dict[str, float] = {}
    for pair in pairs:
        if "=" not in pair:
            raise ValueError(f"--set expects key=value, got {pair!r}")
        key, _, raw = pair.partition("=")
        key = key.strip()
        try:
            overrides[key] = float(raw)
        except ValueError as exc:
            raise ValueError(f"--set {key}: {raw!r} is not a number") from exc
    return overrides


def _parse_modules(raw: str) -> tuple[str, ...]:
    if raw.strip().lower() in {"none", ""}:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _parse_values(raw: str) -> list[float]:
    values: list[float] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if ":" in token:
            parts = token.split(":")
            if len(parts) not in {2, 3}:
                raise ValueError(f"range must be start:stop[:step], got {token!r}")
            start, stop = float(parts[0]), float(parts[1])
            step = float(parts[2]) if len(parts) == 3 else (stop - start) / 5.0
            if step <= 0:
                raise ValueError(f"range step must be positive in {token!r}")
            count = int(round((stop - start) / step)) + 1
            if count < 2 or count > 500:
                raise ValueError(f"range {token!r} implies {count} points; use 2..500")
            values.extend(round(start + index * step, 12) for index in range(count))
        else:
            values.append(float(token))
    if not values:
        raise ValueError("no values parsed")
    return values


def _emit(text: str, out: str | None) -> None:
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")
    else:
        print(text)


def _resolve_scenarios(args: argparse.Namespace) -> tuple[Scenario, ...]:
    scenarios = list(builtin_scenarios())
    for extra in getattr(args, "scenarios_file", None) or []:
        scenarios.extend(load_scenarios(extra))
    return tuple(scenarios)


def _find_scenario(args: argparse.Namespace, name: str) -> Scenario:
    for scenario in _resolve_scenarios(args):
        if scenario.name == name:
            return scenario
    raise ValueError(f"unknown scenario {name!r}; available: {', '.join(scenario_names())}")


def _parameters(args: argparse.Namespace) -> ParameterSet:
    return default_parameters()


def _run_once(args: argparse.Namespace, scenario_name: str) -> SimulationResult:
    scenario = _find_scenario(args, scenario_name)
    overrides = dict(scenario.config.get("overrides", {}))
    overrides.update(_parse_overrides(args.set or []))
    config = scenario.build(
        seed=args.seed,
        dt_hours=args.dt,
        horizon_hours=args.horizon,
        focus_policy=args.policy or scenario.config.get("focus_policy", "never"),
        modules=_parse_modules(args.modules)
        if args.modules is not None
        else scenario.config.get("modules", ()),
        overrides=overrides,
    )
    return SimulationEngine(config, _parameters(args)).run()


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_run(args: argparse.Namespace) -> int:
    result = _run_once(args, args.scenario)
    if args.json:
        payload = json.dumps(result.as_dict(include_samples=args.samples), indent=2, sort_keys=True)
        _emit(payload, args.out)
        return 0
    if args.report:
        scenario = _find_scenario(args, args.scenario)
        body = render_report(result)
        if scenario.caveat:
            body = body.replace(
                "## What this does not show",
                f"## Scenario caveat\n\n{scenario.caveat}\n\n## What this does not show",
                1,
            )
        _emit(body, args.out)
        return 0
    summary = result.metrics
    print(
        f"scenario={result.scenario} seed={result.seed} modules={','.join(result.module_names) or 'none'}"
    )
    for key in (
        "time_to_50pct_repair_hours",
        "time_to_full_repair_hours",
        "area_under_damage_integrity_hours",
        "attention_attributable_fraction",
        "focus_hours",
        "fatigue_episodes",
    ):
        print(f"  {key} = {summary.get(key)}")
    print(f"  run_digest = {result.run_digest[:16]}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    names = args.scenarios or list(DEFAULT_COMPARISON)
    results = [_run_once(args, name) for name in names]
    if args.json:
        _emit(
            json.dumps([r.as_dict(include_samples=args.samples) for r in results], indent=2),
            args.out,
        )
        return 0
    _emit(render_comparison(results, baseline_name=names[0]), args.out)
    return 0


def cmd_sweep(args: argparse.Namespace) -> int:
    try:
        values = _parse_values(args.values)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sweep = sweep_parameter(
        args.param,
        values,
        scenario=args.scenario,
        seed=args.seed,
        parameters=_parameters(args),
    )
    if args.json:
        _emit(json.dumps(sweep.as_dict(), indent=2), args.out)
        return 0
    _emit(render_sweep_markdown(sweep), args.out)
    return 0


def cmd_sensitivity(args: argparse.Namespace) -> int:
    rows = one_factor_sensitivity(
        scenario=args.scenario,
        baseline_scenario=args.baseline,
        factor=args.factor,
        seed=args.seed,
        parameters=_parameters(args),
        metric=args.metric,
    )
    if args.json:
        _emit(json.dumps(rows, indent=2), args.out)
        return 0
    _emit(render_sensitivity_markdown(rows, scenario=args.scenario), args.out)
    return 0


def cmd_scenarios(args: argparse.Namespace) -> int:
    scenarios = _resolve_scenarios(args)
    if args.json:
        _emit(json.dumps([s.as_dict() for s in scenarios], indent=2), args.out)
        return 0
    lines = ["Available scenarios:", ""]
    for scenario in scenarios:
        lines.append(f"  {scenario.name:<22} {scenario.summary}")
        if scenario.caveat:
            lines.append(f"  {'':<22} caveat: {scenario.caveat}")
    _emit("\n".join(lines), args.out)
    return 0


def cmd_parameters(args: argparse.Namespace) -> int:
    params = _parameters(args)
    selected = params.unsupported() if args.unsupported else params.sorted()
    if args.json:
        _emit(json.dumps([p.as_dict() for p in selected], indent=2), args.out)
        return 0
    lines = [
        f"{len(selected)} parameter(s); "
        f"{params.support_summary()['unsupported']} of {len(params)} lack empirical support.",
        "",
        f"{'key':<44} {'value':>10}  {'unit':<18} provenance",
        "-" * 96,
    ]
    for parameter in selected:
        lines.append(
            f"{parameter.key:<44} {parameter.value:>10.4g}  "
            f"{parameter.unit:<18} {parameter.provenance.value}"
        )
    lines.append("")
    lines.append(
        "Every parameter not graded 'measured' or 'literature' is a free knob. "
        "Set the important ones with --set and see how the answer moves."
    )
    _emit("\n".join(lines), args.out)
    return 0


def cmd_modules(args: argparse.Namespace) -> int:
    described = describe_all()
    if args.json:
        _emit(json.dumps(described, indent=2), args.out)
        return 0
    lines = ["Registered modules:", ""]
    for entry in described:
        lines.append(f"  {entry['name']:<16} {entry['doc']}")
        parameters = entry["parameters"]
        for key in parameters if isinstance(parameters, list) else []:
            lines.append(f"      {key}")
    _emit("\n".join(lines), args.out)
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    if args.json:
        _emit(json.dumps({"version": __version__, "disclaimer": DISCLAIMER}, indent=2), args.out)
        return 0
    _emit(f"conscious-subconscious {__version__}\n\n{DISCLAIMER}", args.out)
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs-sim",
        description=(
            "Reproducible simulation of subconscious repair and conscious attention "
            "acting on a scalar tissue model. Educational use only."
        ),
        epilog=DISCLAIMER,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"cs-sim {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--seed", type=int, default=20260921)
        sub.add_argument("--dt", type=float, default=0.05, help="time step in hours")
        sub.add_argument("--horizon", type=float, default=72.0, help="run length in hours")
        sub.add_argument("--policy", choices=FOCUS_POLICIES, default=None)
        sub.add_argument("--modules", default=None, help="comma list, or 'none'")
        sub.add_argument("--set", action="append", metavar="KEY=VALUE", help="parameter override")
        sub.add_argument("--out", default=None, help="write output to a file")
        sub.add_argument("--json", action="store_true")
        sub.add_argument("--samples", action="store_true", help="include the full time series")
        sub.add_argument(
            "--scenarios-file", action="append", default=[], help="extra scenarios (JSON)"
        )

    run = subparsers.add_parser("run", help="run one scenario")
    add_common(run)
    run.add_argument("--scenario", default="baseline")
    run.add_argument("--report", action="store_true", help="emit a Markdown report")
    run.set_defaults(func=cmd_run)

    compare = subparsers.add_parser("compare", help="compare scenarios against a baseline")
    add_common(compare)
    compare.add_argument("--scenarios", nargs="*", default=None)
    compare.set_defaults(func=cmd_compare)

    sweep = subparsers.add_parser("sweep", help="sweep one parameter")
    add_common(sweep)
    sweep.add_argument("--param", required=True)
    sweep.add_argument(
        "--values",
        required=True,
        help="comma list, or start:stop[:step] range, e.g. 0:2:0.5",
    )
    sweep.add_argument("--scenario", default="focused")
    sweep.set_defaults(func=cmd_sweep)

    sensitivity = subparsers.add_parser(
        "sensitivity", help="rank unsupported parameters by influence"
    )
    add_common(sensitivity)
    sensitivity.add_argument("--scenario", default="focused")
    sensitivity.add_argument("--baseline", default="baseline")
    sensitivity.add_argument("--factor", type=float, default=0.5)
    sensitivity.add_argument("--metric", default="time_to_50pct_repair_hours")
    sensitivity.set_defaults(func=cmd_sensitivity)

    scenarios = subparsers.add_parser("scenarios", help="list scenarios")
    scenarios.add_argument("--json", action="store_true")
    scenarios.add_argument("--out", default=None)
    scenarios.add_argument("--scenarios-file", action="append", default=[])
    scenarios.set_defaults(func=cmd_scenarios)

    params = subparsers.add_parser("parameters", help="list parameters and their provenance")
    params.add_argument("--unsupported", action="store_true", help="only unsupported values")
    params.add_argument("--json", action="store_true")
    params.add_argument("--out", default=None)
    params.set_defaults(func=cmd_parameters)

    modules = subparsers.add_parser("modules", help="list registered modules")
    modules.add_argument("--json", action="store_true")
    modules.add_argument("--out", default=None)
    modules.set_defaults(func=cmd_modules)

    version = subparsers.add_parser("version", help="print version and disclaimer")
    version.add_argument("--json", action="store_true")
    version.add_argument("--out", default=None)
    version.set_defaults(func=cmd_version)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except ConsciousSubconsciousError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
