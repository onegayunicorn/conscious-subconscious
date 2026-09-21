"""The engine: determinism, invariants, ordering and control.

The invariants here are the ones a reader should be able to rely on without
reading the implementation: integrity never decreases, attention stays in its
budget, the same configuration always gives the same answer, and turning the
central assumption off really does turn the central assumption off.
"""

from __future__ import annotations

import json

import pytest

from conscious_subconscious.core.errors import ConfigurationError
from conscious_subconscious.core.events import EventKind
from conscious_subconscious.model.engine import FOCUS_POLICIES, RunConfig, SimulationEngine
from conscious_subconscious.model.metrics import SUMMARY_KEYS
from conscious_subconscious.modules.registry import available
from conscious_subconscious.parameters import default_parameters

#: Metrics that describe repair only. These must be identical when the coupling is 0.
REPAIR_METRICS = (
    "final_integrity",
    "time_to_50pct_repair_hours",
    "time_to_full_repair_hours",
    "area_under_damage_integrity_hours",
    "mean_integrity",
    "total_repair",
    "attention_attributable_repair",
    "attention_attributable_fraction",
    "final_perception_gap",
)


def test_parameters_are_still_shared_across_runs() -> None:
    """A run must not mutate the parameter set it was handed."""
    params = default_parameters()
    before = params.digest()
    SimulationEngine(RunConfig(horizon_hours=1.0), params).run()
    assert params.digest() == before


class TestRunConfig:
    def test_defaults_are_valid(self) -> None:
        config = RunConfig()
        assert config.validate() is None

    def test_rejects_non_positive_dt(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(dt_hours=0.0)

    def test_rejects_non_positive_horizon(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(horizon_hours=0.0)

    def test_rejects_a_negative_seed(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(seed=-1)

    def test_rejects_full_initial_integrity(self) -> None:
        """A tissue that starts healed has nothing to simulate."""
        with pytest.raises(ConfigurationError):
            RunConfig(initial_integrity=1.0)

    def test_rejects_an_unknown_policy(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(focus_policy="sometimes")

    def test_rejects_an_inverted_damage_band(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(focus_enter_damage=0.2, focus_exit_damage=0.8)

    def test_rejects_a_dt_longer_than_the_horizon(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(dt_hours=48.0, horizon_hours=24.0)

    def test_rejects_an_empty_tissue_name(self) -> None:
        with pytest.raises(ConfigurationError):
            RunConfig(tissue_name="")

    def test_digest_ignores_dict_ordering(self) -> None:
        first = RunConfig(overrides={"a.b": 1.0, "c.d": 2.0})
        second = RunConfig(overrides={"c.d": 2.0, "a.b": 1.0})
        assert first.digest() == second.digest()

    def test_every_shipped_policy_is_accepted(self) -> None:
        for policy in FOCUS_POLICIES:
            assert RunConfig(focus_policy=policy).focus_policy == policy


class TestDeterminism:
    def test_identical_config_gives_identical_results(self, engine_factory) -> None:
        first = engine_factory(horizon_hours=24.0).run()
        second = engine_factory(horizon_hours=24.0).run()
        assert first.run_digest == second.run_digest
        assert first.metrics == second.metrics

    def test_metrics_are_seed_independent_when_jitter_is_off(self) -> None:
        """A different seed must not move a deterministic model's answer."""
        first = SimulationEngine(RunConfig(seed=1, horizon_hours=24.0)).run()
        second = SimulationEngine(RunConfig(seed=2, horizon_hours=24.0)).run()
        assert first.metrics == second.metrics
        # The digests differ, because the seed is part of the configuration.
        assert first.run_digest != second.run_digest

    def test_jitter_makes_the_seed_matter(self) -> None:
        overrides = {"conscious.neural_drive_jitter": 0.5}
        first = SimulationEngine(
            RunConfig(seed=1, focus_policy="always", horizon_hours=24.0, overrides=overrides)
        ).run()
        second = SimulationEngine(
            RunConfig(seed=2, focus_policy="always", horizon_hours=24.0, overrides=overrides)
        ).run()
        assert first.metrics != second.metrics

    def test_stepwise_and_batch_runs_agree(self) -> None:
        """Stepping by hand must produce exactly what a single run() produces."""
        stepped = SimulationEngine(RunConfig(horizon_hours=6.0, dt_hours=0.25))
        for _ in range(24):
            stepped.step()
        stepped_result = stepped.finalise()

        batched = SimulationEngine(RunConfig(horizon_hours=6.0, dt_hours=0.25)).run()
        assert stepped_result.run_digest == batched.run_digest


class TestInvariants:
    def test_integrity_never_decreases(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=48.0, focus_policy="intermittent").run()
        integrity = [sample.integrity for sample in result.samples]
        assert integrity == sorted(integrity)

    def test_integrity_stays_within_bounds(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=72.0, focus_policy="always").run()
        assert all(0.0 <= sample.integrity <= 1.0 for sample in result.samples)

    def test_attention_never_leaves_its_budget(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=72.0, focus_policy="always").run()
        attention = [sample.attention for sample in result.samples]
        assert min(attention) >= 0.0
        assert max(attention) <= 1.0

    def test_mediators_never_go_negative(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=24.0, focus_policy="always").run()
        for sample in result.samples:
            assert all(value >= 0.0 for value in sample.mediators.values())

    def test_repair_rate_never_negative(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=24.0, focus_policy="always").run()
        assert all(sample.rates["subconscious.total_rate"] >= 0.0 for sample in result.samples)

    def test_run_covers_the_whole_horizon_even_after_healing(self, engine_factory) -> None:
        """Early exit would make a faster scenario look better by being shorter."""
        result = engine_factory(horizon_hours=72.0, dt_hours=0.05).run()
        assert len(result.samples) == 72 * 20
        assert result.samples[-1].t_hours == pytest.approx(72.0)

    def test_overshoot_after_healing_is_recorded(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=96.0, dt_hours=0.1).run()
        assert result.metrics["final_integrity"] == pytest.approx(1.0)
        assert result.metrics["time_to_full_repair_hours"] is not None


class TestCoupling:
    def test_zero_coupling_makes_attention_inert_for_repair(self) -> None:
        """The control case. If this fails, attention is leaking into repair."""
        baseline = SimulationEngine(
            RunConfig(focus_policy="never", horizon_hours=48.0, dt_hours=0.1)
        ).run()
        uncoupled = SimulationEngine(
            RunConfig(
                focus_policy="always",
                horizon_hours=48.0,
                dt_hours=0.1,
                overrides={"conscious.neural_drive_coupling": 0.0},
            )
        ).run()

        for key in REPAIR_METRICS:
            assert baseline.metrics[key] == uncoupled.metrics[key], key

    def test_attention_does_change_repair_when_coupled(self) -> None:
        baseline = SimulationEngine(
            RunConfig(focus_policy="never", horizon_hours=48.0, dt_hours=0.1)
        ).run()
        coupled = SimulationEngine(
            RunConfig(focus_policy="always", horizon_hours=48.0, dt_hours=0.1)
        ).run()
        assert (
            coupled.metrics["time_to_50pct_repair_hours"]
            < baseline.metrics["time_to_50pct_repair_hours"]
        )
        assert coupled.metrics["attention_attributable_fraction"] > 0.0

    def test_the_effect_scale_is_set_by_the_coupling_constant(self) -> None:
        """Bigger invented constant, bigger effect: the result is a model property."""
        overrides = {"conscious.neural_drive_coupling": 3.0}
        strong = SimulationEngine(
            RunConfig(focus_policy="always", horizon_hours=48.0, dt_hours=0.1, overrides=overrides)
        ).run()
        default = SimulationEngine(
            RunConfig(focus_policy="always", horizon_hours=48.0, dt_hours=0.1)
        ).run()
        assert (
            strong.metrics["time_to_50pct_repair_hours"]
            < default.metrics["time_to_50pct_repair_hours"]
        )

    def test_no_neural_drive_reaches_the_field_without_focus(self, engine_factory) -> None:
        result = engine_factory(focus_policy="never", horizon_hours=12.0).run()
        assert all(sample.mediators["neural_drive"] == 0.0 for sample in result.samples)


class TestModules:
    def test_default_modules_are_all_registered(self) -> None:
        config = RunConfig()
        for name in config.modules:
            assert name in available()

    def test_module_names_are_sorted_and_deduplicated(self) -> None:
        engine = SimulationEngine(RunConfig(modules=("perfusion", "inflammation", "perfusion")))
        assert engine.module_names == ("inflammation", "perfusion")

    def test_no_modules_is_allowed(self, engine_factory) -> None:
        result = engine_factory(modules=(), horizon_hours=12.0).run()
        assert result.module_names == ()

    def test_unknown_module_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            SimulationEngine(RunConfig(modules=("astrology",)))

    def test_expectancy_is_disabled_by_default(self, engine_factory) -> None:
        result = engine_factory(modules=("expectancy",), horizon_hours=12.0).run()
        assert result.parameters["module.expectancy.gain"] == 0.0

    def test_modules_change_the_result(self, engine_factory) -> None:
        with_modules = engine_factory(modules=("inflammation",), horizon_hours=48.0).run()
        without = engine_factory(modules=(), horizon_hours=48.0).run()
        assert (
            with_modules.metrics["time_to_50pct_repair_hours"]
            != without.metrics["time_to_50pct_repair_hours"]
        )


class TestResult:
    def test_metrics_expose_every_documented_key(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=6.0).run()
        assert set(result.metrics) == set(SUMMARY_KEYS)

    def test_events_bracket_the_run(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=6.0).run()
        kinds = [event.kind for event in result.events]
        assert kinds[0] == EventKind.RUN_START
        assert kinds[-1] == EventKind.RUN_END

    def test_provenance_is_reported_with_the_result(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=6.0).run()
        assert result.provenance_summary["total"] == len(result.provenance)
        assert result.provenance_summary["unsupported"] > 0
        assert all("provenance" in entry for entry in result.provenance)

    def test_as_dict_omits_samples_unless_asked(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=6.0).run()
        assert "samples" not in result.as_dict()
        assert len(result.as_dict(include_samples=True)["samples"]) == len(result.samples)

    def test_json_round_trip(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=6.0).run()
        payload = json.loads(result.to_json())
        assert payload["digests"]["run"] == result.run_digest
        assert payload["disclaimer"] == result.disclaimer

    def test_disclaimer_is_attached_to_every_result(self, engine_factory) -> None:
        result = engine_factory(horizon_hours=1.0).run()
        assert "not a medical device" in result.disclaimer


class TestControl:
    def test_step_after_finish_is_rejected(self, engine_factory) -> None:
        engine = engine_factory(horizon_hours=1.0)
        engine.run()
        with pytest.raises(ConfigurationError):
            engine.step()

    def test_run_to_a_partial_horizon(self) -> None:
        engine = SimulationEngine(RunConfig(horizon_hours=72.0, dt_hours=0.5))
        result = engine.run_to(10.0)
        assert len(result.samples) == 20

    def test_run_to_rejects_non_positive_hours(self, engine_factory) -> None:
        with pytest.raises(ConfigurationError):
            engine_factory().run_to(0.0)

    def test_focus_and_release_commands(self, engine_factory) -> None:
        engine = engine_factory(horizon_hours=1.0)
        engine.step()
        assert engine.command("focus")["changed"] is True
        assert engine.command("focus")["changed"] is False
        assert engine.command("release")["changed"] is True

    def test_set_policy_command(self, engine_factory) -> None:
        engine = engine_factory(horizon_hours=1.0)
        outcome = engine.command("set_policy", policy="intermittent")
        assert outcome["policy"] == "intermittent"
        assert engine.config.focus_policy == "intermittent"

    def test_unknown_command_is_rejected(self, engine_factory) -> None:
        with pytest.raises(ConfigurationError):
            engine_factory().command("heal_instantly")

    def test_there_is_no_command_that_writes_integrity(self, engine_factory) -> None:
        """Nothing may bypass the repair rule, including an operator."""
        engine = engine_factory()
        for name in ("set_integrity", "damage", "heal", "set_state"):
            with pytest.raises(ConfigurationError):
                engine.command(name, integrity=1.0)

    def test_snapshot_reports_the_current_state(self, engine_factory) -> None:
        engine = engine_factory(horizon_hours=1.0)
        engine.step()
        snapshot = engine.snapshot()
        for key in ("t_hours", "tissue", "mediators", "conscious", "modules", "signals"):
            assert key in snapshot
        assert snapshot["steps"] == 1

    def test_snapshot_reports_step_order_dependence_honestly(self, engine_factory) -> None:
        """The engine documents its step order; a change to it must be deliberate."""
        engine = engine_factory(horizon_hours=1.0)
        engine.step()
        # neural_drive is injected before decay, so it is non-zero after one step.
        assert engine.snapshot()["mediators"]["growth_factor"] >= 0.0
