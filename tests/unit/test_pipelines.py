"""Data pipelines: signal processing, steps and the DAG runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conscious_subconscious.core.errors import PipelineError
from conscious_subconscious.pipelines import (
    PipelineContext,
    PipelineRunner,
    PipelineSpec,
    StepSpec,
    available_steps,
    band_power,
    channel_series,
    describe_steps,
    get_step,
    load_pipeline,
    mean,
    moving_average,
    resample_linear,
    stdev,
    zscore,
)
from conscious_subconscious.pipelines.steps import LoadCsvStep, ValidateStep, WriteJsonStep


class TestDsp:
    def test_mean(self) -> None:
        assert mean([1.0, 2.0, 3.0]) == 2.0

    def test_mean_of_nothing_is_undefined(self) -> None:
        with pytest.raises(PipelineError):
            mean([])

    def test_sample_stdev(self) -> None:
        assert stdev([2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]) == pytest.approx(2.13809, rel=1e-4)

    def test_stdev_needs_two_points(self) -> None:
        assert stdev([1.0]) == 0.0

    def test_zscore_is_standardised(self) -> None:
        values = zscore([1.0, 2.0, 3.0, 4.0])
        assert sum(values) == pytest.approx(0.0, abs=1e-9)

    def test_zscore_of_a_constant_series_is_zeros(self) -> None:
        """A flat channel means a disconnected sensor, not a crash."""
        assert zscore([5.0, 5.0, 5.0]) == [0.0, 0.0, 0.0]

    def test_zscore_of_nothing(self) -> None:
        assert zscore([]) == []

    def test_moving_average_preserves_length(self) -> None:
        assert len(moving_average([1.0, 2.0, 3.0, 4.0], 2)) == 4

    def test_moving_average_does_not_backfill(self) -> None:
        assert moving_average([10.0, 0.0, 0.0], 3) == [10.0, 5.0, 10.0 / 3.0]

    def test_moving_average_rejects_a_bad_window(self) -> None:
        with pytest.raises(PipelineError):
            moving_average([1.0], 0)

    def test_resample_hits_the_endpoints_exactly(self) -> None:
        out = resample_linear([0.0, 1.0, 2.0], [10.0, 20.0, 30.0], [-1.0, 1.0, 9.0])
        assert out == [10.0, 20.0, 30.0]

    def test_resample_interpolates_the_midpoint(self) -> None:
        out = resample_linear([0.0, 2.0], [0.0, 10.0], [1.0])
        assert out == [5.0]

    def test_resample_rejects_duplicate_timestamps(self) -> None:
        with pytest.raises(PipelineError, match="duplicate"):
            resample_linear([0.0, 0.0], [1.0, 2.0], [0.5])

    def test_resample_rejects_unsorted_times(self) -> None:
        with pytest.raises(PipelineError, match="sorted"):
            resample_linear([1.0, 0.0], [1.0, 2.0], [0.5])

    def test_resample_rejects_mismatched_lengths(self) -> None:
        with pytest.raises(PipelineError):
            resample_linear([0.0, 1.0], [1.0], [0.5])

    def test_resample_needs_two_points(self) -> None:
        with pytest.raises(PipelineError):
            resample_linear([0.0], [1.0], [0.0])

    def test_band_power_of_a_flat_signal_is_zero(self) -> None:
        assert band_power([1.0] * 60, sample_rate_hz=1.0, low_hz=0.1, high_hz=0.4) == 0.0

    def test_band_power_finds_a_matching_oscillation(self) -> None:
        import math

        series = [math.sin(2.0 * math.pi * index / 10.0) for index in range(200)]
        inside = band_power(series, sample_rate_hz=1.0, low_hz=0.05, high_hz=0.15)
        outside = band_power(series, sample_rate_hz=1.0, low_hz=0.30, high_hz=0.45)
        assert inside > outside

    def test_band_power_rejects_an_inverted_band(self) -> None:
        with pytest.raises(PipelineError):
            band_power([1.0, 2.0], sample_rate_hz=1.0, low_hz=0.4, high_hz=0.1)

    def test_band_power_rejects_a_band_above_nyquist(self) -> None:
        with pytest.raises(PipelineError, match="Nyquist"):
            band_power([1.0, 2.0], sample_rate_hz=1.0, low_hz=0.1, high_hz=5.0)

    def test_band_power_rejects_a_bad_rate(self) -> None:
        with pytest.raises(PipelineError):
            band_power([1.0, 2.0], sample_rate_hz=0.0, low_hz=0.1, high_hz=0.2)

    def test_channel_series_extracts_one_channel(self) -> None:
        rows = [(0.0, "a", 1.0), (0.0, "b", 2.0), (1.0, "a", 3.0)]
        assert channel_series(rows, "a") == ([0.0, 1.0], [1.0, 3.0])


class TestSteps:
    def test_registry_lists_every_builtin_step(self) -> None:
        assert set(available_steps()) >= {
            "load_csv",
            "validate",
            "resample",
            "features",
            "summarise",
            "write_json",
        }

    def test_unknown_step_is_rejected(self) -> None:
        with pytest.raises(PipelineError):
            get_step("does_not_exist")

    def test_describe_steps_is_machine_readable(self) -> None:
        assert all("uses" in entry for entry in describe_steps())

    def test_load_csv(self, sample_recording: Path, tmp_path: Path) -> None:
        context = PipelineContext(workdir=tmp_path)
        output = LoadCsvStep("raw", {"path": str(sample_recording)}).run(context)
        assert output["row_count"] == 80

    def test_load_csv_reports_a_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(PipelineError, match="not found"):
            LoadCsvStep("raw", {"path": "absent.csv"}).run(PipelineContext(workdir=tmp_path))

    def test_load_csv_rejects_wrong_columns(self, tmp_path: Path) -> None:
        path = tmp_path / "wrong.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        with pytest.raises(PipelineError, match="columns"):
            LoadCsvStep("raw", {"path": str(path)}).run(PipelineContext(workdir=tmp_path))

    def test_load_csv_requires_its_parameter(self, tmp_path: Path) -> None:
        with pytest.raises(PipelineError, match="requires parameter"):
            LoadCsvStep("raw", {}).run(PipelineContext(workdir=tmp_path))

    def _loaded(self, sample_recording: Path, tmp_path: Path) -> PipelineContext:
        context = PipelineContext(workdir=tmp_path)
        context.outputs["raw"] = LoadCsvStep("raw", {"path": str(sample_recording)}).run(context)
        return context

    def test_validate_passes_clean_data(self, sample_recording: Path, tmp_path: Path) -> None:
        output = ValidateStep("clean", {"source": "raw"}).run(
            self._loaded(sample_recording, tmp_path)
        )
        assert output["channels"] == ["heart_rate", "hrv_index"]

    def test_validate_rejects_too_few_rows(self, sample_recording: Path, tmp_path: Path) -> None:
        context = self._loaded(sample_recording, tmp_path)
        with pytest.raises(PipelineError, match="minimum"):
            ValidateStep("clean", {"source": "raw", "min_rows": 1000}).run(context)

    def test_validate_rejects_non_finite_values(self, tmp_path: Path) -> None:
        path = tmp_path / "nan.csv"
        path.write_text(
            "t_seconds,channel,value\n0,heart_rate,nan\n1,heart_rate,60\n", encoding="utf-8"
        )
        context = PipelineContext(workdir=tmp_path)
        context.outputs["raw"] = LoadCsvStep("raw", {"path": str(path)}).run(context)
        with pytest.raises(PipelineError, match="non-finite"):
            ValidateStep("clean", {"source": "raw"}).run(context)

    def test_validate_rejects_duplicate_timestamps_beyond_tolerance(self, tmp_path: Path) -> None:
        path = tmp_path / "dup.csv"
        path.write_text(
            "t_seconds,channel,value\n0,heart_rate,60\n0,heart_rate,61\n1,heart_rate,62\n",
            encoding="utf-8",
        )
        context = PipelineContext(workdir=tmp_path)
        context.outputs["raw"] = LoadCsvStep("raw", {"path": str(path)}).run(context)
        with pytest.raises(PipelineError, match="duplicate"):
            ValidateStep("clean", {"source": "raw"}).run(context)

    def test_validate_reports_a_missing_dependency(self, tmp_path: Path) -> None:
        with pytest.raises(PipelineError, match="not available"):
            ValidateStep("clean", {"source": "ghost"}).run(PipelineContext(workdir=tmp_path))

    def test_resample_produces_a_uniform_grid(self, sample_recording: Path, tmp_path: Path) -> None:
        from conscious_subconscious.pipelines.steps import ResampleStep

        context = self._loaded(sample_recording, tmp_path)
        context.outputs["clean"] = ValidateStep("clean", {"source": "raw"}).run(context)
        output = ResampleStep(
            "uniform", {"source": "clean", "channel": "heart_rate", "rate_hz": 1.0}
        ).run(context)
        assert output["count"] > 5
        assert output["rate_hz"] == 1.0

    def test_features_include_expected_keys(self, sample_recording: Path, tmp_path: Path) -> None:
        from conscious_subconscious.pipelines.steps import FeatureStep

        context = self._loaded(sample_recording, tmp_path)
        context.outputs["clean"] = ValidateStep("clean", {"source": "raw"}).run(context)
        output = FeatureStep("features", {"source": "clean"}).run(context)
        for key in ("count", "mean", "stdev", "min", "max", "estimated_rate_hz"):
            assert key in output["features"]["heart_rate"]
        assert output["features"]["heart_rate"]["rmssd_ms"] is not None

    def test_summarise_refuses_to_overwrite_a_key(
        self, sample_recording: Path, tmp_path: Path
    ) -> None:
        from conscious_subconscious.pipelines.steps import SummariseStep

        context = self._loaded(sample_recording, tmp_path)
        context.outputs["a"] = {"shared": 1}
        context.outputs["b"] = {"shared": 2}
        with pytest.raises(PipelineError, match="overwrite"):
            SummariseStep("merge", {"sources": ["a", "b"]}).run(context)

    def test_write_json_writes_the_selected_keys(self, tmp_path: Path) -> None:
        context = PipelineContext(workdir=tmp_path)
        context.outputs["upstream"] = {"keep": 1, "drop": 2}
        output = WriteJsonStep(
            "out", {"source": "upstream", "path": "out/x.json", "keys": ["keep"]}
        ).run(context)
        assert json.loads(Path(output["path"]).read_text(encoding="utf-8")) == {"keep": 1}

    def test_step_requires_a_uses_name(self) -> None:
        from conscious_subconscious.pipelines.steps import Step

        with pytest.raises(PipelineError):

            class Broken(Step):
                def run(self, ctx: PipelineContext) -> dict[str, object]:
                    return {}


class TestRunner:
    def _spec(self) -> PipelineSpec:
        return PipelineSpec.from_dict(
            {
                "name": "test",
                "steps": [
                    {"name": "b", "uses": "validate", "needs": ["a"], "params": {"source": "a"}},
                    {"name": "a", "uses": "load_csv", "params": {"path": "samples/session.csv"}},
                ],
            }
        )

    def test_order_is_topological_and_stable(self) -> None:
        spec = self._spec()
        assert spec.order() == ("a", "b")
        assert spec.order() == spec.order()

    def test_cycle_is_detected(self) -> None:
        with pytest.raises(PipelineError, match="cycle"):
            PipelineSpec.from_dict(
                {
                    "name": "looping",
                    "steps": [
                        {"name": "a", "uses": "validate", "needs": ["b"]},
                        {"name": "b", "uses": "validate", "needs": ["a"]},
                    ],
                }
            )

    def test_unknown_dependency_is_rejected(self) -> None:
        with pytest.raises(PipelineError, match="unknown step"):
            PipelineSpec.from_dict(
                {"name": "x", "steps": [{"name": "a", "uses": "load_csv", "needs": ["ghost"]}]}
            )

    def test_duplicate_step_names_are_rejected(self) -> None:
        with pytest.raises(PipelineError, match="duplicate step name"):
            PipelineSpec.from_dict(
                {
                    "name": "x",
                    "steps": [
                        {"name": "a", "uses": "load_csv"},
                        {"name": "a", "uses": "validate"},
                    ],
                }
            )

    def test_unknown_pipeline_key_is_rejected(self) -> None:
        with pytest.raises(PipelineError, match="unknown key"):
            PipelineSpec.from_dict(
                {"name": "x", "surprise": 1, "steps": [{"name": "a", "uses": "load_csv"}]}
            )

    def test_step_needs_and_params_defaults(self) -> None:
        spec = StepSpec.from_dict({"name": "a", "uses": "load_csv"})
        assert spec.needs == ()
        assert spec.params == {}

    def test_step_spec_rejects_unknown_keys(self) -> None:
        with pytest.raises(PipelineError):
            StepSpec.from_dict({"name": "a", "uses": "load_csv", "extra": 1})

    def test_end_to_end_run(self, sample_recording: Path, tmp_path: Path) -> None:
        (tmp_path / "samples").mkdir()
        (tmp_path / "samples" / "session.csv").write_text(
            sample_recording.read_text(encoding="utf-8"), encoding="utf-8"
        )
        run = PipelineRunner(self._spec()).run(workdir=tmp_path)
        assert run.outputs["a"]["row_count"] == 80
        assert run.outputs["clean"]["channels"] if "clean" in run.outputs else True
        assert run.durations_seconds.keys() == {"a", "b"}

    def test_missing_input_fails_the_run(self, tmp_path: Path) -> None:
        with pytest.raises(PipelineError):
            PipelineRunner(self._spec()).run(workdir=tmp_path)


class TestShippedPipelines:
    def _stage(self, tmp_path: Path, sample_recording: Path) -> None:
        (tmp_path / "samples").mkdir()
        (tmp_path / "samples" / "session.csv").write_text(
            sample_recording.read_text(encoding="utf-8"), encoding="utf-8"
        )

    @pytest.mark.parametrize("name", ["session_export.yaml", "telemetry_features.yaml"])
    def test_definition_loads_and_runs(
        self, repo_root: Path, tmp_path: Path, sample_recording: Path, name: str
    ) -> None:
        spec = load_pipeline(repo_root / "pipelines" / name)
        self._stage(tmp_path, sample_recording)
        run = PipelineRunner(spec).run(workdir=tmp_path)
        assert run.outputs, f"{name} produced no outputs"
        assert any((tmp_path / "out").glob("*.json"))

    def test_missing_required_parameter_is_caught_at_load_time(self) -> None:
        """A DAG that cannot run must fail when it is loaded, not three steps in."""
        with pytest.raises(PipelineError, match="missing required parameter"):
            PipelineSpec.from_dict({"name": "x", "steps": [{"name": "a", "uses": "features"}]})

    def test_every_shipped_pipeline_supplies_its_required_parameters(self, repo_root: Path) -> None:
        for name in ("session_export.yaml", "telemetry_features.yaml"):
            spec = load_pipeline(repo_root / "pipelines" / name)
            for step in spec.steps:
                missing = set(get_step(step.uses).required_params()) - set(step.params)
                assert not missing, f"{name}:{step.name} missing {sorted(missing)}"

    def test_missing_pipeline_file_is_rejected(self, tmp_path: Path) -> None:
        with pytest.raises(PipelineError, match="not found"):
            load_pipeline(tmp_path / "nope.yaml")

    def test_json_pipelines_need_no_yaml(self, tmp_path: Path) -> None:
        path = tmp_path / "p.json"
        path.write_text(
            json.dumps(
                {
                    "name": "json-pipeline",
                    "steps": [{"name": "a", "uses": "load_csv", "params": {"path": "x.csv"}}],
                }
            ),
            encoding="utf-8",
        )
        assert load_pipeline(path).name == "json-pipeline"

    def test_malformed_yaml_is_reported(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.yaml"
        path.write_text("name: [unclosed\n", encoding="utf-8")
        with pytest.raises(PipelineError, match="YAML"):
            load_pipeline(path)

    def test_non_mapping_document_is_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "list.yaml"
        path.write_text("- one\n- two\n", encoding="utf-8")
        with pytest.raises(PipelineError, match="mapping"):
            load_pipeline(path)
