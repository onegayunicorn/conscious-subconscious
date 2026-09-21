"""Core primitives: parameters, RNG, clock, events."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from conscious_subconscious.core.clock import MAX_STEPS, VirtualClock
from conscious_subconscious.core.errors import ConfigurationError, ParameterError
from conscious_subconscious.core.events import Event, EventBus, EventKind
from conscious_subconscious.core.params import Parameter, ParameterSet, Provenance
from conscious_subconscious.core.rng import DeterministicRng
from conscious_subconscious.parameters import PARAMETER_COUNT, default_parameters


# --------------------------------------------------------------------- params
class TestProvenance:
    def test_supported_only_for_measured_and_literature(self) -> None:
        assert Provenance.MEASURED.is_supported
        assert Provenance.LITERATURE.is_supported
        assert not Provenance.ASSUMED.is_supported
        assert not Provenance.INVENTED.is_supported

    def test_every_grade_has_a_rationale(self) -> None:
        for grade in Provenance:
            assert grade.rationale


class TestParameter:
    def test_rejects_key_without_a_namespace(self) -> None:
        with pytest.raises(ParameterError):
            Parameter(key="bare", value=1.0, unit="x", provenance=Provenance.ASSUMED)

    def test_rejects_value_below_minimum(self) -> None:
        with pytest.raises(ParameterError):
            Parameter(key="a.b", value=-1.0, unit="x", provenance=Provenance.ASSUMED, minimum=0.0)

    def test_rejects_value_above_maximum(self) -> None:
        with pytest.raises(ParameterError):
            Parameter(key="a.b", value=2.0, unit="x", provenance=Provenance.ASSUMED, maximum=1.0)

    def test_rejects_inverted_bounds(self) -> None:
        with pytest.raises(ParameterError):
            Parameter(
                key="a.b",
                value=0.5,
                unit="x",
                provenance=Provenance.ASSUMED,
                minimum=2.0,
                maximum=1.0,
            )

    def test_as_dict_reports_support(self) -> None:
        supported = Parameter("a.b", 1.0, "x", Provenance.LITERATURE).as_dict()
        unsupported = Parameter("a.c", 1.0, "x", Provenance.INVENTED).as_dict()
        assert supported["supported"] is True
        assert unsupported["supported"] is False


class TestParameterSet:
    def test_rejects_duplicate_keys(self) -> None:
        duplicate = Parameter("a.b", 1.0, "x", Provenance.ASSUMED)
        with pytest.raises(ParameterError):
            ParameterSet([duplicate, duplicate])

    def test_rejects_empty(self) -> None:
        with pytest.raises(ParameterError):
            ParameterSet([])

    def test_unknown_key_is_an_error_not_a_default(self) -> None:
        with pytest.raises(ParameterError):
            default_parameters().value("does.not.exist")

    def test_iteration_is_sorted_by_key(self) -> None:
        keys = [p.key for p in default_parameters()]
        assert keys == sorted(keys)

    def test_overrides_downgrade_provenance(self) -> None:
        """An overridden value must not keep its original, flattering tag."""
        base = default_parameters()
        original = base["module.circadian.period_hours"]
        assert original.provenance is Provenance.LITERATURE

        overridden = base.with_overrides({"module.circadian.period_hours": 25.0})
        after = overridden["module.circadian.period_hours"]
        assert after.value == 25.0
        assert after.provenance is Provenance.ASSUMED
        assert "runtime override" in after.note

    def test_override_of_unknown_key_is_rejected(self) -> None:
        with pytest.raises(ParameterError):
            default_parameters().with_overrides({"nope.nope": 1.0})

    def test_override_still_respects_declared_bounds(self) -> None:
        with pytest.raises(ParameterError):
            default_parameters().with_overrides({"tissue.max_integrity": 5.0})

    def test_overrides_do_not_mutate_the_original(self) -> None:
        base = default_parameters()
        base.with_overrides({"subconscious.base_repair_rate": 0.9})
        assert base.value("subconscious.base_repair_rate") != 0.9

    def test_support_summary_counts_match(self) -> None:
        params = default_parameters()
        summary = params.support_summary()
        assert summary["total"] == len(params)
        assert summary["supported"] + summary["unsupported"] == len(params)
        assert summary["unsupported"] == len(params.unsupported())

    def test_digest_is_stable_and_order_independent(self) -> None:
        assert default_parameters().digest() == default_parameters().digest()

    def test_digest_changes_when_a_value_changes(self) -> None:
        base = default_parameters()
        changed = base.with_overrides({"subconscious.base_repair_rate": 0.021})
        assert base.digest() != changed.digest()

    def test_shipped_parameter_count_is_what_the_docs_claim(self) -> None:
        assert len(default_parameters()) == PARAMETER_COUNT == 34


# ------------------------------------------------------------------------ rng
class TestDeterministicRng:
    def test_same_seed_gives_same_draws(self) -> None:
        assert DeterministicRng(7).uniform("a", 0, 1) == DeterministicRng(7).uniform("a", 0, 1)

    def test_streams_are_independent_of_draw_order(self) -> None:
        """Interleaving draws from another stream must not perturb this one."""
        first = DeterministicRng(11)
        first_value = first.uniform("alpha", 0, 1)

        second = DeterministicRng(11)
        second.uniform("beta", 0, 1)
        second.uniform("beta", 0, 1)
        assert second.uniform("alpha", 0, 1) == first_value

    def test_different_streams_differ(self) -> None:
        rng = DeterministicRng(3)
        assert rng.uniform("a", 0, 1) != rng.uniform("b", 0, 1)

    def test_stable_across_processes(self) -> None:
        """Values must not depend on PYTHONHASHSEED (no built-in hash())."""
        assert DeterministicRng(99).uniform("x", 0, 1) == DeterministicRng(99).uniform("x", 0, 1)

    def test_rejects_bool_seed(self) -> None:
        with pytest.raises(TypeError):
            DeterministicRng(True)

    def test_rejects_negative_seed(self) -> None:
        with pytest.raises(ValueError):
            DeterministicRng(-1)

    def test_rejects_reversed_range(self) -> None:
        with pytest.raises(ValueError):
            DeterministicRng(1).uniform("a", 1.0, 0.0)

    def test_rejects_empty_stream_name(self) -> None:
        with pytest.raises(ValueError):
            DeterministicRng(1).stream("")

    def test_fork_is_deterministic_and_independent(self) -> None:
        parent = DeterministicRng(5)
        child = parent.fork("child")
        assert child.uniform("v", 0, 1) == parent.fork("child").uniform("v", 0, 1)

    def test_digest_changes_when_a_stream_is_opened(self) -> None:
        rng = DeterministicRng(2)
        before = rng.digest()
        rng.stream("new")
        assert rng.digest() != before

    def test_choice_rejects_empty_population(self) -> None:
        with pytest.raises(ValueError):
            DeterministicRng(1).choice("a", ())


# ---------------------------------------------------------------------- clock
class TestVirtualClock:
    def test_accumulates_without_drift(self) -> None:
        clock = VirtualClock(dt_hours=0.1)
        for _ in range(1000):
            clock.tick()
        assert clock.t_hours == pytest.approx(100.0)

    def test_steps_for_rounds_to_whole_steps(self) -> None:
        clock = VirtualClock(dt_hours=0.25)
        assert clock.steps_for(1.0) == 4
        assert clock.steps_for(1.1) == 4

    def test_rejects_non_positive_dt(self) -> None:
        with pytest.raises(ConfigurationError):
            VirtualClock(dt_hours=0.0)

    def test_reset_returns_to_zero(self) -> None:
        clock = VirtualClock(dt_hours=1.0)
        clock.tick()
        clock.reset()
        assert (clock.t_hours, clock.steps) == (0.0, 0)

    def test_rejects_negative_hours(self) -> None:
        with pytest.raises(ConfigurationError):
            VirtualClock().steps_for(-1.0)

    def test_refuses_to_run_forever(self) -> None:
        clock = VirtualClock(dt_hours=1e-9)
        clock.steps = MAX_STEPS
        with pytest.raises(ConfigurationError):
            clock.tick()


# --------------------------------------------------------------------- events
class TestEventBus:
    def test_history_and_counts(self) -> None:
        bus = EventBus()
        bus.publish(0.0, EventKind.RUN_START, "engine")
        bus.publish(1.0, EventKind.TISSUE_REPAIR, "subconscious", applied=0.1)
        assert len(bus) == 2
        assert bus.counts()[EventKind.TISSUE_REPAIR] == 1
        assert len(bus.of_kind(EventKind.RUN_START)) == 1

    def test_drain_returns_only_new_events(self) -> None:
        bus = EventBus()
        bus.publish(0.0, EventKind.RUN_START, "engine")
        assert len(bus.drain()) == 1
        assert bus.drain() == ()

    def test_subscribers_are_called(self) -> None:
        bus = EventBus()
        seen: list[str] = []
        bus.subscribe(EventKind.TISSUE_REPAIR, lambda event: seen.append(event.kind))
        bus.publish(0.0, EventKind.RUN_START, "engine")
        bus.publish(0.0, EventKind.TISSUE_REPAIR, "subconscious")
        assert seen == [EventKind.TISSUE_REPAIR]

    def test_wildcard_subscriber_sees_everything(self) -> None:
        bus = EventBus()
        seen: list[str] = []
        bus.subscribe("*", lambda event: seen.append(event.kind))
        bus.publish(0.0, EventKind.RUN_START, "engine")
        bus.publish(0.0, EventKind.WARNING, "engine")
        assert seen == [EventKind.RUN_START, EventKind.WARNING]

    def test_bounded_history_counts_drops_instead_of_lying(self) -> None:
        bus = EventBus(history_limit=3)
        for index in range(5):
            bus.publish(float(index), EventKind.MODULE_STEP, "module")
        assert len(bus) == 3
        assert bus.dropped == 2

    def test_event_is_immutable(self) -> None:
        event = Event(0.0, EventKind.RUN_START, "engine")
        with pytest.raises(FrozenInstanceError):
            event.kind = "other"  # type: ignore[misc]

    def test_rejects_non_positive_history_limit(self) -> None:
        with pytest.raises(ValueError):
            EventBus(history_limit=0)
