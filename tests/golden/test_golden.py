"""Golden reference runs.

These lock the model's numerical output against a committed file. Every other
test in the suite checks a *property* (monotonicity, bounds, determinism); these
check the numbers themselves.

That distinction matters: a refactor can keep every property intact while
quietly changing every value — a reordered step, a renamed variable, a subtly
different decay. A property test passes; a golden test fails and asks whether
the change was intended.

Deliberate model changes are expected. Regenerate with::

    python3 tools/update_golden.py

and review the diff before committing it. A golden file updated without reading
the diff is a golden file that has stopped doing anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conscious_subconscious.model.engine import SimulationEngine
from conscious_subconscious.parameters import default_parameters
from conscious_subconscious.sim.scenarios import get_scenario

GOLDEN_PATH = Path(__file__).parent / "golden_runs.json"


@pytest.fixture(scope="module")
def golden() -> dict:
    assert GOLDEN_PATH.is_file(), "golden_runs.json is missing; run tools/update_golden.py"
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.mark.golden
def test_golden_file_declares_its_parameters(golden: dict) -> None:
    assert set(golden["runs"]) == {"baseline", "focused", "intermittent", "focused-uncoupled"}


@pytest.mark.golden
def test_parameter_digest_is_unchanged(golden: dict) -> None:
    """Catches a changed default, which shifts every result below."""
    assert default_parameters().digest() == golden["parameter_digest"]


@pytest.mark.golden
@pytest.mark.parametrize("name", ["baseline", "focused", "intermittent", "focused-uncoupled"])
def test_metrics_match_the_reference(golden: dict, name: str) -> None:
    expected = golden["runs"][name]
    result = SimulationEngine(
        get_scenario(name).build(
            seed=golden["seed"],
            dt_hours=golden["dt_hours"],
            horizon_hours=golden["horizon_hours"],
        )
    ).run()
    assert result.metrics == expected["metrics"], (
        f"{name}: metrics drifted from the golden reference. If the change was "
        "intended, run tools/update_golden.py and read the diff."
    )
    assert result.run_digest == expected["run_digest"]


@pytest.mark.golden
def test_golden_reference_is_internally_consistent(golden: dict) -> None:
    """The reference must itself show the model's defining property."""
    baseline = golden["runs"]["baseline"]["metrics"]
    control = golden["runs"]["focused-uncoupled"]["metrics"]

    for key in (
        "final_integrity",
        "time_to_50pct_repair_hours",
        "area_under_damage_integrity_hours",
    ):
        assert baseline[key] == control[key], key

    assert baseline["attention_attributable_fraction"] == 0.0
    assert control["attention_attributable_fraction"] == 0.0


@pytest.mark.golden
def test_golden_attention_scenario_repairs_faster_than_the_reference(golden: dict) -> None:
    baseline = golden["runs"]["baseline"]["metrics"]
    focused = golden["runs"]["focused"]["metrics"]
    assert (
        focused["area_under_damage_integrity_hours"] < baseline["area_under_damage_integrity_hours"]
    )
    assert focused["attention_attributable_fraction"] > 0.0
