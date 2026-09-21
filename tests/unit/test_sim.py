"""Scenarios, reports, sweeps and the command-line front end."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conscious_subconscious.core.errors import ConfigurationError
from conscious_subconscious.model.engine import SimulationEngine
from conscious_subconscious.modules.registry import available
from conscious_subconscious.parameters import default_parameters
from conscious_subconscious.sim.cli import main as cs_sim
from conscious_subconscious.sim.report import EM_DASH, render_comparison, render_report
from conscious_subconscious.sim.scenarios import (
    DEFAULT_COMPARISON,
    builtin_scenarios,
    get_scenario,
    load_scenarios,
    scenario_names,
)
from conscious_subconscious.sim.sweep import (
    one_factor_sensitivity,
    render_sensitivity_markdown,
    render_sweep_markdown,
    sweep_parameter,
)


class TestScenarios:
    def test_expected_scenarios_ship(self) -> None:
        assert set(DEFAULT_COMPARISON).issubset(set(scenario_names()))

    def test_default_comparison_scenarios_exist(self) -> None:
        for name in DEFAULT_COMPARISON:
            assert get_scenario(name).name == name

    def test_every_scenario_override_names_a_real_parameter(self) -> None:
        """A typo'd override would silently do nothing, which is worse than a crash."""
        params = default_parameters()
        for scenario in builtin_scenarios():
            for key in scenario.config.get("overrides", {}):
                assert key in params, f"{scenario.name}: unknown parameter {key}"

    def test_every_scenario_module_is_registered(self) -> None:
        registered = available()
        for scenario in builtin_scenarios():
            for module in scenario.config.get("modules", ()):
                assert module in registered, f"{scenario.name}: unknown module {module}"

    def test_every_scenario_builds_and_runs(self) -> None:
        for scenario in builtin_scenarios():
            config = scenario.build(dt_hours=1.0, horizon_hours=8.0)
            result = SimulationEngine(config).run()
            assert result.metrics["samples"] == 8, scenario.name

    def test_every_scenario_has_a_summary_and_a_caveat(self) -> None:
        for scenario in builtin_scenarios():
            assert scenario.summary, scenario.name
            assert scenario.caveat, scenario.name

    def test_build_applies_the_scenario_name(self) -> None:
        assert get_scenario("focused").build().scenario == "focused"

    def test_build_applies_caller_overrides_last(self) -> None:
        config = get_scenario("focused").build(seed=7, horizon_hours=3.0)
        assert (config.seed, config.horizon_hours) == (7, 3.0)

    def test_unknown_scenario_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            get_scenario("astrology")

    def test_uncoupled_control_scenario_exists_and_matches_baseline(self) -> None:
        baseline = SimulationEngine(
            get_scenario("baseline").build(dt_hours=0.1, horizon_hours=24.0)
        ).run()
        control = SimulationEngine(
            get_scenario("focused-uncoupled").build(dt_hours=0.1, horizon_hours=24.0)
        ).run()
        assert control.metrics["final_integrity"] == baseline.metrics["final_integrity"]
        assert (
            control.metrics["time_to_50pct_repair_hours"]
            == baseline.metrics["time_to_50pct_repair_hours"]
        )

    def test_autonomic_scenario_declares_the_autonomic_module(self) -> None:
        assert "autonomic" in get_scenario("autonomic-coupled").config["modules"]


class TestScenarioFiles:
    def test_load_from_json(self, tmp_path: Path) -> None:
        path = tmp_path / "extra.json"
        path.write_text(
            json.dumps(
                [
                    {
                        "name": "custom",
                        "summary": "a scenario from a file",
                        "config": {"focus_policy": "always", "modules": ["inflammation"]},
                    }
                ]
            ),
            encoding="utf-8",
        )
        loaded = load_scenarios(path)
        assert loaded[0].name == "custom"
        assert loaded[0].build().focus_policy == "always"

    def test_object_form_is_accepted(self, tmp_path: Path) -> None:
        path = tmp_path / "obj.json"
        path.write_text(json.dumps({"mine": {"summary": "x", "config": {}}}), encoding="utf-8")
        assert load_scenarios(path)[0].name == "mine"

    def test_unknown_config_key_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([{"name": "x", "config": {"nonsense": 1}}]), encoding="utf-8")
        with pytest.raises(ConfigurationError, match="unknown config key"):
            load_scenarios(path)

    def test_bad_policy_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(
            json.dumps([{"name": "x", "config": {"focus_policy": "sometimes"}}]), encoding="utf-8"
        )
        with pytest.raises(ConfigurationError):
            load_scenarios(path)

    def test_missing_name_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([{"config": {}}]), encoding="utf-8")
        with pytest.raises(ConfigurationError):
            load_scenarios(path)

    def test_invalid_json_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ConfigurationError):
            load_scenarios(path)

    def test_missing_file_is_reported(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigurationError):
            load_scenarios(tmp_path / "absent.json")


class TestReport:
    def test_single_run_report_has_the_essentials(self) -> None:
        result = SimulationEngine(
            get_scenario("focused").build(dt_hours=0.5, horizon_hours=12.0)
        ).run()
        report = render_report(result)
        assert "# Simulation report" in report
        assert "Boundary" in report
        assert "Provenance of the numbers" in report
        assert "What this does not show" in report
        assert "cs-sim run" in report
        assert "not a medical device" in report

    def test_report_names_the_invented_coupling_constant(self) -> None:
        result = SimulationEngine(get_scenario("focused").build(horizon_hours=4.0)).run()
        assert "conscious.neural_drive_coupling" in render_report(result)

    def test_missing_values_render_as_an_em_dash_not_zero(self) -> None:
        """ "Never reached 50%" and "reached it in 0 h" are opposite statements."""
        result = SimulationEngine(
            get_scenario("inflammation-heavy").build(horizon_hours=8.0, dt_hours=1.0)
        ).run()
        report = render_report(result)
        if result.metrics["time_to_50pct_repair_hours"] is None:
            assert EM_DASH in report

    def test_comparison_shows_relative_change(self) -> None:
        results = [
            SimulationEngine(get_scenario(name).build(dt_hours=0.5, horizon_hours=24.0)).run()
            for name in DEFAULT_COMPARISON
        ]
        comparison = render_comparison(results)
        assert "Change relative to baseline" in comparison
        assert "property of the coupling constant" in comparison
        assert EM_DASH in comparison

    def test_comparison_of_one_run_still_renders(self) -> None:
        result = SimulationEngine(get_scenario("baseline").build(horizon_hours=4.0)).run()
        assert "Scenario comparison" in render_comparison([result])

    def test_empty_comparison_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            render_comparison([])


class TestSweep:
    def test_sweep_runs_one_point_per_value(self) -> None:
        sweep = sweep_parameter("conscious.neural_drive_coupling", [0.0, 1.0], scenario="focused")
        assert len(sweep.points) == 2
        assert sweep.provenance == "invented"

    def test_zero_coupling_reproduces_the_no_attention_case(self) -> None:
        sweep = sweep_parameter("conscious.neural_drive_coupling", [0.0], scenario="focused")
        reference = SimulationEngine(
            get_scenario("focused").build(overrides={"conscious.neural_drive_coupling": 0.0})
        ).run()
        assert (
            sweep.points[0].metrics["time_to_50pct_repair_hours"]
            == reference.metrics["time_to_50pct_repair_hours"]
        )
        assert sweep.points[0].metrics["attention_attributable_fraction"] == 0.0

    def test_sweep_is_monotone_in_the_coupling_constant(self) -> None:
        sweep = sweep_parameter("conscious.neural_drive_coupling", [0.0, 0.5, 1.0, 2.0])
        assert sweep.is_monotonic()

    def test_spread_is_computed(self) -> None:
        sweep = sweep_parameter("conscious.neural_drive_coupling", [0.0, 2.0])
        assert sweep.spread("time_to_50pct_repair_hours") > 0

    def test_unknown_parameter_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            sweep_parameter("nope.nope", [1.0])

    def test_empty_value_list_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            sweep_parameter("conscious.neural_drive_gain", [])

    def test_render_marks_unsupported_parameters(self) -> None:
        sweep = sweep_parameter("conscious.neural_drive_coupling", [0.0, 1.0])
        rendered = render_sweep_markdown(sweep)
        assert "no empirical support" in rendered
        assert "monotone" in rendered

    def test_render_marks_supported_parameters_differently(self) -> None:
        sweep = sweep_parameter("module.circadian.period_hours", [12.0, 24.0])
        assert "no empirical support" not in render_sweep_markdown(sweep)


class TestSensitivity:
    def test_ranks_parameters_with_the_largest_move_first(self) -> None:
        rows = one_factor_sensitivity(scenario="focused")
        assert rows
        moves = [row["absolute_relative_change"] for row in rows]
        assert moves == sorted(moves, reverse=True)

    def test_only_unsupported_parameters_are_probed_by_default(self) -> None:
        params = default_parameters()
        rows = one_factor_sensitivity(scenario="focused")
        for row in rows:
            assert not params[row["parameter"]].provenance.is_supported

    def test_bounds_are_respected_for_capped_parameters(self) -> None:
        """A parameter with maximum 1.0 must still be probed, not skipped."""
        rows = one_factor_sensitivity(
            parameter_keys=["conscious.attention_budget"], scenario="focused"
        )
        assert rows

    def test_supported_parameters_can_be_probed_explicitly(self) -> None:
        rows = one_factor_sensitivity(
            parameter_keys=["module.circadian.period_hours"], scenario="focused"
        )
        assert rows[0]["provenance"] == "literature"

    def test_unknown_parameter_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            one_factor_sensitivity(parameter_keys=["ghost.key"])

    def test_bad_factor_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            one_factor_sensitivity(factor=1.5)

    def test_render_produces_a_table(self) -> None:
        rows = one_factor_sensitivity(scenario="focused")
        rendered = render_sensitivity_markdown(rows)
        assert "One-factor sensitivity" in rendered
        assert "free knobs" in rendered


class TestCli:
    def test_version(self, capsys) -> None:
        assert cs_sim(["version"]) == 0
        assert "conscious-subconscious" in capsys.readouterr().out

    def test_version_json(self, capsys) -> None:
        assert cs_sim(["version", "--json"]) == 0
        assert "disclaimer" in json.loads(capsys.readouterr().out)

    def test_scenarios(self, capsys) -> None:
        assert cs_sim(["scenarios"]) == 0
        assert "baseline" in capsys.readouterr().out

    def test_parameters(self, capsys) -> None:
        assert cs_sim(["parameters"]) == 0
        output = capsys.readouterr().out
        assert "invented" in output and "conscious.neural_drive_coupling" in output

    def test_parameters_unsupported_only(self, capsys) -> None:
        assert cs_sim(["parameters", "--unsupported"]) == 0
        assert "module.circadian.period_hours" not in capsys.readouterr().out

    def test_modules(self, capsys) -> None:
        assert cs_sim(["modules"]) == 0
        assert "inflammation" in capsys.readouterr().out

    def test_run_plain(self, capsys) -> None:
        assert cs_sim(["run", "--scenario", "baseline", "--horizon", "6", "--dt", "1"]) == 0
        assert "run_digest" in capsys.readouterr().out

    def test_run_json(self, capsys) -> None:
        assert cs_sim(["run", "--horizon", "6", "--dt", "1", "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["metrics"]["samples"] == 6

    def test_run_with_samples(self, capsys) -> None:
        assert cs_sim(["run", "--horizon", "3", "--dt", "1", "--json", "--samples"]) == 0
        assert len(json.loads(capsys.readouterr().out)["samples"]) == 3

    def test_run_report(self, capsys) -> None:
        assert (
            cs_sim(["run", "--scenario", "focused", "--horizon", "6", "--dt", "1", "--report"]) == 0
        )
        assert "# Simulation report" in capsys.readouterr().out

    def test_run_to_a_file(self, tmp_path: Path, capsys) -> None:
        target = tmp_path / "nested" / "report.md"
        assert cs_sim(["run", "--horizon", "3", "--dt", "1", "--report", "--out", str(target)]) == 0
        assert "Provenance of the numbers" in target.read_text(encoding="utf-8")

    def test_set_override_changes_the_result(self, capsys) -> None:
        assert (
            cs_sim(
                [
                    "run",
                    "--scenario",
                    "focused",
                    "--horizon",
                    "12",
                    "--dt",
                    "1",
                    "--json",
                    "--set",
                    "conscious.neural_drive_coupling=0",
                ]
            )
            == 0
        )
        payload = json.loads(capsys.readouterr().out)
        assert payload["metrics"]["attention_attributable_fraction"] == 0.0

    def test_compare(self, capsys) -> None:
        assert cs_sim(["compare", "--horizon", "12", "--dt", "1"]) == 0
        assert "Scenario comparison" in capsys.readouterr().out

    def test_compare_json(self, capsys) -> None:
        assert cs_sim(["compare", "--horizon", "6", "--dt", "1", "--json"]) == 0
        assert len(json.loads(capsys.readouterr().out)) == len(DEFAULT_COMPARISON)

    def test_sweep(self, capsys) -> None:
        assert (
            cs_sim(
                [
                    "sweep",
                    "--param",
                    "conscious.neural_drive_coupling",
                    "--values",
                    "0:1:0.5",
                    "--horizon",
                    "12",
                    "--dt",
                    "1",
                ]
            )
            == 0
        )
        assert "Parameter sweep" in capsys.readouterr().out

    def test_sensitivity(self, capsys) -> None:
        assert (
            cs_sim(
                [
                    "sensitivity",
                    "--horizon",
                    "12",
                    "--dt",
                    "1",
                    "--metric",
                    "area_under_damage_integrity_hours",
                ]
            )
            == 0
        )
        assert "One-factor sensitivity" in capsys.readouterr().out

    def test_unknown_scenario_exits_non_zero(self, capsys) -> None:
        assert cs_sim(["run", "--scenario", "nope"]) == 1

    def test_bad_set_syntax_exits_non_zero(self, capsys) -> None:
        assert cs_sim(["run", "--set", "nonsense"]) == 1

    def test_non_numeric_set_exits_non_zero(self, capsys) -> None:
        assert cs_sim(["run", "--set", "a.b=fast"]) == 1

    def test_bad_sweep_range_exits_non_zero(self, capsys) -> None:
        assert cs_sim(["sweep", "--param", "conscious.neural_drive_gain", "--values", "1:2:0"]) == 1

    def test_oversized_sweep_is_refused(self, capsys) -> None:
        assert (
            cs_sim(["sweep", "--param", "conscious.neural_drive_gain", "--values", "0:100:0.01"])
            == 1
        )

    def test_modules_none_is_accepted(self, capsys) -> None:
        assert cs_sim(["run", "--modules", "none", "--horizon", "3", "--dt", "1"]) == 0

    def test_scenarios_file_is_used(self, tmp_path: Path) -> None:
        path = tmp_path / "extra.json"
        path.write_text(
            json.dumps([{"name": "extra", "summary": "s", "config": {}}]), encoding="utf-8"
        )
        assert (
            cs_sim(
                [
                    "run",
                    "--scenario",
                    "extra",
                    "--scenarios-file",
                    str(path),
                    "--horizon",
                    "3",
                    "--dt",
                    "1",
                ]
            )
            == 0
        )
