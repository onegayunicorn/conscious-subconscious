#!/usr/bin/env python3
"""Regenerate tests/golden/golden_runs.json.

Kept as a script rather than a `pytest --update-golden` flag on purpose: updating
a golden file should be a deliberate, visible act with a diff to review, not a
side effect of running the tests. If the update path is one flag away from the
verification path, it will eventually be used to make a red test go green.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / "tests" / "golden" / "golden_runs.json"
SCENARIOS = ("baseline", "focused", "intermittent", "focused-uncoupled")
SEED = 20260921
DT_HOURS = 0.1
HORIZON_HOURS = 24.0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print instead of writing")
    parser.add_argument("--no-diff", action="store_true", help="do not show the diff afterwards")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT / "src"))
    from conscious_subconscious.model.engine import SimulationEngine  # noqa: PLC0415
    from conscious_subconscious.parameters import default_parameters  # noqa: PLC0415
    from conscious_subconscious.sim.scenarios import get_scenario  # noqa: PLC0415

    previous = TARGET.read_text(encoding="utf-8") if TARGET.is_file() else ""

    payload = {
        "_comment": (
            "Reference output for the shipped scenarios. Regenerate with "
            "tools/update_golden.py, and only after confirming the change in numbers "
            "is intended. Any diff here means the model's numerical behaviour changed."
        ),
        "seed": SEED,
        "dt_hours": DT_HOURS,
        "horizon_hours": HORIZON_HOURS,
        "parameter_digest": default_parameters().digest(),
        "runs": {},
    }
    for name in SCENARIOS:
        result = SimulationEngine(
            get_scenario(name).build(seed=SEED, dt_hours=DT_HOURS, horizon_hours=HORIZON_HOURS)
        ).run()
        payload["runs"][name] = {
            "run_digest": result.run_digest,
            "config_digest": result.config_digest,
            "metrics": result.metrics,
        }

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"

    if args.dry_run:
        print(rendered)
        return 0

    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"wrote {TARGET}")

    if args.no_diff or not previous:
        return 0
    print("\ndiff (previous -> new):")
    completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", "diff", "--no-color", "--", str(TARGET.relative_to(ROOT))],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    print(completed.stdout or "(no diff — regenerating was a no-op)")
    print(
        "Review the diff above. A metrics change means the model's numbers moved; "
        "a digest-only change usually means a comment or default changed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
