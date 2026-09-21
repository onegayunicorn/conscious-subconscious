"""The model layer: tissue, mediator field, subsystems, metrics."""

from __future__ import annotations

import pytest

from conscious_subconscious.core.errors import ConfigurationError
from conscious_subconscious.core.events import EventBus, EventKind
from conscious_subconscious.core.params import ParameterSet
from conscious_subconscious.core.rng import DeterministicRng
from conscious_subconscious.model.conscious import (
    AlwaysFocus,
    ConsciousSystem,
    IntermittentFocus,
    NeverFocus,
)
from conscious_subconscious.model.context import StepContext
from conscious_subconscious.model.mediators import CHANNELS, MediatorField
from conscious_subconscious.model.metrics import MetricsRecorder, Sample
from conscious_subconscious.model.subconscious import SubconsciousSystem
from conscious_subconscious.model.tissue import Tissue
from conscious_subconscious.parameters import default_parameters


def _decay(params: ParameterSet) -> dict[str, float]:
    return {channel: params.value(f"mediator.{channel}.decay_per_hour") for channel in CHANNELS}


def _context(
    tissue: Tissue,
    field: MediatorField,
    params: ParameterSet | None = None,
    *,
    t_hours: float = 0.0,
    dt_hours: float = 0.1,
) -> StepContext:
    resolved = params or default_parameters()
    return StepContext(
        t_hours=t_hours,
        dt_hours=dt_hours,
        tissue=tissue,
        field=field,
        params=resolved,
        bus=EventBus(),
        rng=DeterministicRng(1),
    )


# --------------------------------------------------------------------- tissue
class TestTissue:
    def test_damage_is_the_complement_of_integrity(self) -> None:
        tissue = Tissue(integrity=0.25, max_integrity=1.0)
        assert tissue.damage == pytest.approx(0.75)

    def test_repair_is_clamped_at_the_ceiling(self) -> None:
        tissue = Tissue(integrity=0.9)
        applied = tissue.apply_repair(5.0)
        assert applied == pytest.approx(0.1)
        assert tissue.integrity == pytest.approx(1.0)
        assert tissue.is_healed

    def test_overshooting_repair_is_recorded_not_hidden(self) -> None:
        """Wasted repair must be counted, or a wasteful rule looks efficient."""
        tissue = Tissue(integrity=0.9)
        tissue.apply_repair(5.0)
        assert tissue.wasted_repair == pytest.approx(4.9)

    def test_total_repair_tracks_only_what_was_applied(self) -> None:
        tissue = Tissue(integrity=0.5)
        tissue.apply_repair(0.25)
        tissue.apply_repair(5.0)
        assert tissue.total_repair == pytest.approx(0.5)

    def test_rejects_negative_repair(self) -> None:
        with pytest.raises(ValueError):
            Tissue().apply_repair(-0.1)

    def test_rejects_integrity_above_the_ceiling(self) -> None:
        with pytest.raises(ConfigurationError):
            Tissue(integrity=1.5, max_integrity=1.0)

    def test_rejects_repairing_a_healed_tissue_loudly(self) -> None:
        """A dead tissue must not silently absorb work without saying so."""
        tissue = Tissue(integrity=1.0)
        assert tissue.apply_repair(0.5) == 0.0
        assert tissue.wasted_repair == pytest.approx(0.5)

    def test_snapshot_rounds_for_stable_reports(self) -> None:
        assert Tissue(integrity=0.2).snapshot()["integrity"] == 0.2


# ------------------------------------------------------------- mediator field
class TestMediatorField:
    def test_starts_empty(self) -> None:
        field = MediatorField(_decay(default_parameters()))
        assert all(value == 0.0 for value in field.snapshot().values())

    def test_production_accumulates(self) -> None:
        field = MediatorField(_decay(default_parameters()))
        field.add("growth_factor", 0.5)
        field.add("growth_factor", 0.25)
        assert field.value("growth_factor") == pytest.approx(0.75)

    def test_decay_reduces_without_going_negative(self) -> None:
        params = default_parameters()
        field = MediatorField(_decay(params))
        field.add("neural_drive", 1.0)
        for _ in range(500):
            field.step(0.1)
        assert field.value("neural_drive") == 0.0

    def test_decay_matches_the_exponential_form(self) -> None:
        params = default_parameters()
        field = MediatorField(_decay(params))
        field.add("cytokine", 1.0)
        rate = params.value("mediator.cytokine.decay_per_hour")
        field.step(2.0)
        assert field.value("cytokine") == pytest.approx(
            2.718281828459045 ** (-2.0 * rate), rel=1e-9
        )

    def test_rejects_negative_production(self) -> None:
        field = MediatorField(_decay(default_parameters()))
        with pytest.raises(ValueError):
            field.add("atp", -0.1)

    def test_rejects_unknown_channel(self) -> None:
        field = MediatorField(_decay(default_parameters()))
        with pytest.raises(ValueError):
            field.value("serotonin")

    def test_requires_a_decay_constant_for_every_channel(self) -> None:
        with pytest.raises(ValueError):
            MediatorField({"atp": 0.1})

    def test_rejects_negative_decay(self) -> None:
        decay = _decay(default_parameters())
        decay["atp"] = -1.0
        with pytest.raises(ValueError):
            MediatorField(decay)

    def test_audit_conserves_production(self) -> None:
        field = MediatorField(_decay(default_parameters()))
        field.add("atp", 2.0)
        field.step(0.5)
        audit = field.audit()["atp"]
        assert audit["produced"] == pytest.approx(2.0)
        assert audit["current"] + audit["dissipated"] == pytest.approx(2.0)

    def test_reset_clears_everything(self) -> None:
        field = MediatorField(_decay(default_parameters()))
        field.add("atp", 1.0)
        field.step(0.1)
        field.reset()
        assert field.snapshot()["atp"] == 0.0
        assert field.audit()["atp"]["produced"] == 0.0


# -------------------------------------------------------- subconscious system
class TestSubconsciousSystem:
    def test_produces_growth_factor_and_repairs(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        system = SubconsciousSystem(params)
        context = _context(tissue, field, params)

        system.produce(context)
        assert field.value("growth_factor") > 0.0
        assert field.value("cytokine") > 0.0

        report = system.step(context)
        assert report.applied > 0.0
        assert tissue.integrity > 0.2

    def test_coupling_of_zero_makes_attention_irrelevant(self) -> None:
        """The central assumption, exercised directly: setting it to 0 kills the effect."""
        params = default_parameters().with_overrides({"conscious.neural_drive_coupling": 0.0})
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        field.set("neural_drive", 100.0)
        context = _context(tissue, field, params)

        report = SubconsciousSystem(params).step(context)
        assert report.coupling_multiplier == pytest.approx(1.0)
        assert report.total_rate == pytest.approx(report.base_rate)

    def test_neural_drive_increases_the_repair_rate_when_coupled(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        # Growth factor must be present, or saturation is zero and there is no
        # base rate for the coupling to multiply.
        field.set("growth_factor", 5.0)
        field.set("neural_drive", 1.0)
        context = _context(tissue, field, params)

        report = SubconsciousSystem(params).step(context)
        assert report.base_rate > 0.0
        assert report.total_rate > report.base_rate
        assert context.signal("subconscious.attention_attributable_rate") > 0.0

    def test_repair_is_impossible_when_inflammation_is_total(self) -> None:
        params = default_parameters().with_overrides(
            {
                "module.inflammation.repair_inhibition": 1.0,
                "module.inflammation.baseline": 1.0,
            }
        )
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        field.set("growth_factor", 10.0)
        context = _context(tissue, field, params)
        context.set_signal("inflammation", 1.0)

        report = SubconsciousSystem(params).step(context)
        assert report.total_rate == 0.0
        assert report.applied == 0.0

    def test_emits_a_repair_event(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        field.set("growth_factor", 5.0)
        context = _context(tissue, field, params)

        SubconsciousSystem(params).step(context)
        assert len(context.bus.of_kind(EventKind.TISSUE_REPAIR)) == 1

    def test_never_writes_integrity_directly(self) -> None:
        """Only apply_repair may move integrity; check the report matches the delta."""
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)

        before = tissue.integrity
        report = SubconsciousSystem(params).step(context)
        assert tissue.integrity - before == pytest.approx(report.applied)


# ----------------------------------------------------------- conscious system
class TestConsciousSystem:
    def test_starts_unfocused_with_a_full_budget(self) -> None:
        system = ConsciousSystem(default_parameters())
        assert not system.is_focused
        assert system.attention == pytest.approx(1.0)

    def test_focus_and_release_are_idempotent(self) -> None:
        params = default_parameters()
        tissue = Tissue()
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)
        system = ConsciousSystem(params)

        assert system.focus("muscle", context) is True
        assert system.focus("muscle", context) is False
        assert system.release(context) is True
        assert system.release(context) is False

    def test_rejects_an_empty_focus_target(self) -> None:
        params = default_parameters()
        context = _context(Tissue(), MediatorField(_decay(params)), params)
        with pytest.raises(ValueError):
            ConsciousSystem(params).focus("", context)

    def test_attention_drains_while_focused_and_recovers_while_not(self) -> None:
        params = default_parameters()
        tissue = Tissue()
        field = MediatorField(_decay(params))
        system = ConsciousSystem(params)

        system.focus(tissue.name, _context(tissue, field, params))
        for _ in range(10):
            system.step(_context(tissue, field, params))
        drained = system.attention
        assert drained < 1.0

        system.release(_context(tissue, field, params))
        for _ in range(10):
            system.step(_context(tissue, field, params))
        assert system.attention > drained

    def test_attention_never_leaves_zero_or_one(self) -> None:
        params = default_parameters()
        tissue = Tissue()
        field = MediatorField(_decay(params))
        system = ConsciousSystem(params)
        system.focus(tissue.name, _context(tissue, field, params))
        for _ in range(500):
            system.step(_context(tissue, field, params, dt_hours=0.5))
        assert 0.0 <= system.attention <= params.value("conscious.attention_budget")

    def test_fatigue_is_flagged_once_per_episode(self) -> None:
        params = default_parameters()
        tissue = Tissue()
        field = MediatorField(_decay(params))
        system = ConsciousSystem(params)
        system.focus(tissue.name, _context(tissue, field, params))
        for _ in range(200):
            system.step(_context(tissue, field, params, dt_hours=0.5))
        assert system.fatigued
        assert system.fatigue_episodes >= 1

    def test_focus_injects_neural_drive_only_when_focused(self) -> None:
        params = default_parameters()
        tissue = Tissue()
        field = MediatorField(_decay(params))
        system = ConsciousSystem(params)

        system.step(_context(tissue, field, params))
        assert field.value("neural_drive") == 0.0

        system.focus(tissue.name, _context(tissue, field, params))
        system.step(_context(tissue, field, params))
        assert field.value("neural_drive") > 0.0

    def test_perceived_progress_is_distinct_from_actual_integrity(self) -> None:
        params = default_parameters().with_overrides({"conscious.perceived_bias": 0.3})
        tissue = Tissue(integrity=0.4)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)

        report = ConsciousSystem(params).step(context)
        assert report.actual_progress == pytest.approx(0.4)
        assert report.perceived_progress > report.actual_progress
        assert report.perception_gap == pytest.approx(
            report.perceived_progress - report.actual_progress
        )

    def test_perceived_progress_is_clamped_to_the_unit_interval(self) -> None:
        params = default_parameters().with_overrides({"conscious.perceived_bias": 1.0})
        tissue = Tissue(integrity=0.9)
        field = MediatorField(_decay(params))
        report = ConsciousSystem(params).step(_context(tissue, field, params))
        assert report.perceived_progress == pytest.approx(1.0)

    def test_jitter_is_off_by_default(self) -> None:
        params = default_parameters()
        tissue = Tissue()
        reports = []
        for _ in range(3):
            field = MediatorField(_decay(params))
            system = ConsciousSystem(params)
            system.focus(tissue.name, _context(tissue, field, params))
            reports.append(system.step(_context(tissue, field, params)).drive_injected)
        assert len(set(reports)) == 1


class TestFocusPolicies:
    def test_never_focus_never_focuses(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)
        assert NeverFocus().should_focus(context, ConsciousSystem(params)) is False

    def test_always_focus_engages_when_rested(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)
        assert AlwaysFocus().should_focus(context, ConsciousSystem(params)) is True

    def test_always_focus_releases_a_fatigued_mind(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.2)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)
        system = ConsciousSystem(params)
        system.attention = 0.1
        assert AlwaysFocus().should_focus(context, system) is False

    def test_always_focus_stops_when_the_tissue_is_healed(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=1.0)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)
        assert AlwaysFocus().should_focus(context, ConsciousSystem(params)) is False

    def test_intermittent_focus_ignores_damage_outside_the_band(self) -> None:
        params = default_parameters()
        system = ConsciousSystem(params)
        policy = IntermittentFocus(enter_damage=0.80, exit_damage=0.20)

        healed_tissue = Tissue(integrity=0.95)
        field = MediatorField(_decay(params))
        assert policy.should_focus(_context(healed_tissue, field, params), system) is False

    def test_intermittent_focus_engages_inside_the_band(self) -> None:
        params = default_parameters()
        tissue = Tissue(integrity=0.4)
        field = MediatorField(_decay(params))
        policy = IntermittentFocus(enter_damage=0.80, exit_damage=0.20)
        assert policy.should_focus(_context(tissue, field, params), ConsciousSystem(params)) is True

    def test_intermittent_focus_requires_attention_to_recover_before_re_engaging(self) -> None:
        """Hysteresis: without it the policy flaps against the threshold."""
        params = default_parameters()
        tissue = Tissue(integrity=0.4)
        field = MediatorField(_decay(params))
        context = _context(tissue, field, params)
        system = ConsciousSystem(params)
        policy = IntermittentFocus()

        system.attention = params.value("conscious.fatigue_threshold") - 0.01
        assert policy.should_focus(context, system) is False

        system.attention = params.value("conscious.resume_attention") + 0.01
        assert policy.should_focus(context, system) is True

    def test_intermittent_focus_rejects_an_inverted_band(self) -> None:
        with pytest.raises(ValueError):
            IntermittentFocus(enter_damage=0.2, exit_damage=0.8)


# -------------------------------------------------------------------- metrics
class TestMetrics:
    def _sample(self, t: float, integrity: float, **kwargs: object) -> Sample:
        """Build a sample with sensible defaults, overriding by keyword."""
        mediators = kwargs.pop("mediators", {"neural_drive": 0.0, "growth_factor": 0.0})
        rates = kwargs.pop("rates", {})
        return Sample(
            t_hours=t,
            integrity=integrity,
            damage=1.0 - integrity,
            attention=float(kwargs.pop("attention", 1.0)),  # type: ignore[arg-type]
            focused=bool(kwargs.pop("focused", False)),
            fatigued=bool(kwargs.pop("fatigued", False)),
            perceived_progress=float(kwargs.pop("perceived_progress", integrity)),
            mediators=mediators,  # type: ignore[arg-type]
            rates=rates,  # type: ignore[arg-type]
        )

    def test_threshold_time_is_measured_on_recovered_fraction(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, max_integrity=1.0, dt_hours=1.0)
        for step in range(5):
            recorder.record(self._sample(float(step), 0.2 + step * 0.1))
        # Recovered fraction hits 0.5 at integrity 0.6, which is step 4.
        assert recorder.threshold_time(0.5) == 4.0

    def test_threshold_time_is_none_when_never_reached(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, max_integrity=1.0, dt_hours=1.0)
        recorder.record(self._sample(0.0, 0.2))
        assert recorder.threshold_time(1.0) is None

    def test_rejects_out_of_range_fraction(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, dt_hours=1.0)
        with pytest.raises(ValueError):
            recorder.threshold_time(1.5)

    def test_summary_requires_samples(self) -> None:
        with pytest.raises(ValueError):
            MetricsRecorder(initial_integrity=0.2).summary()

    def test_area_under_damage_uses_the_trapezoid_rule_from_zero(self) -> None:
        """The integral starts at t=0 in the initial state, not at the first sample.

        That implicit first interval is deliberate: damage exists from the moment
        the run starts, and dropping it would make a scenario that samples
        coarsely look like it healed faster.
        """
        recorder = MetricsRecorder(initial_integrity=0.0, max_integrity=1.0, dt_hours=1.0)
        recorder.record(self._sample(1.0, 0.0))
        recorder.record(self._sample(2.0, 1.0))
        # 0->1 h: damage 1.0 -> 1.0 => 1.0
        # 1->2 h: damage 1.0 -> 0.0 => 0.5
        assert recorder.area_under_damage == pytest.approx(1.5)

    def test_summary_exposes_every_documented_key(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, max_integrity=1.0, dt_hours=1.0)
        recorder.record(self._sample(1.0, 0.5))
        from conscious_subconscious.model.metrics import SUMMARY_KEYS

        assert set(recorder.summary()) == set(SUMMARY_KEYS)

    def test_attention_attributable_fraction_guards_against_zero_repair(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, max_integrity=1.0, dt_hours=1.0)
        recorder.record(self._sample(1.0, 0.2, rates={"subconscious.total_rate": 0.0}))
        assert recorder.summary()["attention_attributable_fraction"] == 0.0

    def test_fatigue_episodes_are_counted(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, max_integrity=1.0, dt_hours=1.0)
        recorder.record(self._sample(1.0, 0.3), fatigue_episode=True)
        recorder.record(self._sample(2.0, 0.4))
        assert recorder.summary()["fatigue_episodes"] == 1

    def test_rejects_negative_attention_spend(self) -> None:
        recorder = MetricsRecorder(initial_integrity=0.2, dt_hours=1.0)
        with pytest.raises(ValueError):
            recorder.record(self._sample(1.0, 0.3), attention_spent_delta=-1.0)

    def test_rejects_a_ceiling_below_the_starting_integrity(self) -> None:
        with pytest.raises(ValueError):
            MetricsRecorder(initial_integrity=0.9, max_integrity=0.5)
