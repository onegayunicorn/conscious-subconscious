"""The simulation engine: ordering, reproducibility and result packaging.

Deterministic step order
------------------------
Each step runs exactly this sequence, and the order is part of the model:

1. **Modules** — publish derived signals and add channel production
   (inflammation, perfusion, circadian, autonomic, expectancy).
2. **Focus decision** — the policy reads current damage and attention.
3. **Conscious system** — injects ``neural_drive``, spends or restores
   attention, computes perceived progress.
4. **Subconscious production** — secretes growth factors and cytokines.
5. **Subconscious repair** — the only code path that changes tissue integrity.
6. **Field decay** — every channel decays exponentially over one ``dt``.
7. **Recording** — sample the state and fold it into the metrics.

Changing the order changes results, so the order is covered by tests.

Runs always execute the full horizon even after the tissue is repaired. That
keeps area-under-damage and time-to-threshold comparable across scenarios; an
early exit would make the focused run look better simply by being shorter.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .. import DISCLAIMER
from ..core.clock import VirtualClock
from ..core.errors import ConfigurationError
from ..core.events import Event, EventBus, EventKind
from ..core.params import ParameterSet
from ..core.rng import DeterministicRng
from ..modules.registry import build_modules
from .conscious import (
    AlwaysFocus,
    ConsciousSystem,
    FocusPolicy,
    IntermittentFocus,
    NeverFocus,
)
from .context import StepContext
from .mediators import CHANNELS, MediatorField
from .metrics import MetricsRecorder, Sample
from .subconscious import SubconsciousSystem
from .tissue import Tissue

__all__ = ["RunConfig", "SimulationResult", "SimulationEngine", "FOCUS_POLICIES"]

FOCUS_POLICIES: tuple[str, ...] = ("never", "always", "intermittent")


@dataclass(slots=True)
class RunConfig:
    """Everything that identifies a run. Two equal configs must give equal results."""

    scenario: str = "baseline"
    seed: int = 20260921
    dt_hours: float = 0.05
    horizon_hours: float = 72.0
    tissue_name: str = "muscle tissue"
    initial_integrity: float = 0.20
    focus_policy: str = "never"
    focus_enter_damage: float = 0.80
    focus_exit_damage: float = 0.20
    modules: tuple[str, ...] = ("inflammation", "perfusion", "circadian")
    overrides: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.dt_hours <= 0:
            raise ConfigurationError("dt_hours must be positive")
        if self.horizon_hours <= 0:
            raise ConfigurationError("horizon_hours must be positive")
        if self.seed < 0:
            raise ConfigurationError("seed must be non-negative")
        if not 0.0 <= self.initial_integrity < 1.0:
            raise ConfigurationError("initial_integrity must lie in [0, 1)")
        if self.focus_policy not in FOCUS_POLICIES:
            raise ConfigurationError(
                f"focus_policy must be one of {FOCUS_POLICIES}, got {self.focus_policy!r}"
            )
        if not 0.0 <= self.focus_exit_damage < self.focus_enter_damage <= 1.0:
            raise ConfigurationError("require 0 <= focus_exit_damage < focus_enter_damage <= 1")
        if self.dt_hours > self.horizon_hours:
            raise ConfigurationError("dt_hours must not exceed horizon_hours")
        if not self.tissue_name:
            raise ConfigurationError("tissue_name must be non-empty")

    def as_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "seed": self.seed,
            "dt_hours": self.dt_hours,
            "horizon_hours": self.horizon_hours,
            "tissue_name": self.tissue_name,
            "initial_integrity": self.initial_integrity,
            "focus_policy": self.focus_policy,
            "focus_enter_damage": self.focus_enter_damage,
            "focus_exit_damage": self.focus_exit_damage,
            "modules": list(self.modules),
            "overrides": dict(sorted(self.overrides.items())),
        }

    def digest(self) -> str:
        canonical = json.dumps(self.as_dict(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class SimulationResult:
    """A completed run, with everything needed to audit or reproduce it."""

    config: RunConfig
    metrics: dict[str, Any]
    samples: tuple[Sample, ...]
    events: tuple[Event, ...]
    parameters: dict[str, float]
    provenance: list[dict[str, Any]]
    provenance_summary: dict[str, Any]
    module_names: tuple[str, ...]
    parameter_digest: str
    config_digest: str
    run_digest: str
    final_integrity: float
    disclaimer: str = DISCLAIMER

    @property
    def scenario(self) -> str:
        return self.config.scenario

    @property
    def seed(self) -> int:
        return self.config.seed

    def as_dict(
        self, *, include_samples: bool = False, include_events: bool = True
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "scenario": self.config.scenario,
            "seed": self.config.seed,
            "config": self.config.as_dict(),
            "modules": list(self.module_names),
            "final_integrity": self.final_integrity,
            "metrics": dict(self.metrics),
            "provenance_summary": dict(self.provenance_summary),
            "digests": {
                "parameters": self.parameter_digest,
                "config": self.config_digest,
                "run": self.run_digest,
            },
            "disclaimer": self.disclaimer,
        }
        if include_samples:
            payload["samples"] = [s.as_dict() for s in self.samples]
            payload["parameters"] = dict(self.parameters)
            payload["provenance"] = list(self.provenance)
        if include_events:
            payload["events"] = [e.as_dict() for e in self.events]
        return payload

    def to_json(self, *, include_samples: bool = False, indent: int | None = 2) -> str:
        return json.dumps(
            self.as_dict(include_samples=include_samples),
            indent=indent,
            sort_keys=True,
        )


def _make_policy(config: RunConfig) -> FocusPolicy:
    if config.focus_policy == "never":
        return NeverFocus()
    if config.focus_policy == "always":
        return AlwaysFocus()
    return IntermittentFocus(
        enter_damage=config.focus_enter_damage,
        exit_damage=config.focus_exit_damage,
    )


class SimulationEngine:
    """Runs one configuration, deterministically."""

    def __init__(
        self,
        config: RunConfig | None = None,
        parameters: ParameterSet | None = None,
    ) -> None:
        from ..parameters import default_parameters

        self.config = config if config is not None else RunConfig()
        self.config.validate()

        base = parameters if parameters is not None else default_parameters()
        self.params = base.with_overrides(self.config.overrides) if self.config.overrides else base

        self.clock = VirtualClock(dt_hours=self.config.dt_hours)
        self.rng = DeterministicRng(self.config.seed)
        self.bus = EventBus()

        self.tissue = Tissue(
            name=self.config.tissue_name,
            integrity=self.config.initial_integrity,
            max_integrity=self.params.value("tissue.max_integrity"),
        )
        self.field = MediatorField(
            decay_per_hour={
                channel: self.params.value(f"mediator.{channel}.decay_per_hour")
                for channel in CHANNELS
            }
        )
        self.subconscious = SubconsciousSystem(self.params)
        self.conscious = ConsciousSystem(self.params)
        self.policy = _make_policy(self.config)
        self.modules = build_modules(self.config.modules, self.params)
        self.metrics = MetricsRecorder(
            initial_integrity=self.config.initial_integrity,
            max_integrity=self.params.value("tissue.max_integrity"),
            dt_hours=self.config.dt_hours,
        )

        self._finished = False
        self._result: SimulationResult | None = None
        self._started = False

    # -- introspection -----------------------------------------------------
    @property
    def module_names(self) -> tuple[str, ...]:
        return tuple(m.name for m in self.modules)

    @property
    def finished(self) -> bool:
        return self._finished

    @property
    def result(self) -> SimulationResult | None:
        return self._result

    # -- stepping ----------------------------------------------------------
    def _context(self) -> StepContext:
        return StepContext(
            t_hours=self.clock.t_hours,
            dt_hours=self.clock.dt_hours,
            tissue=self.tissue,
            field=self.field,
            params=self.params,
            bus=self.bus,
            rng=self.rng,
        )

    def step(self) -> dict[str, Any]:
        """Advance one step and return a compact snapshot of the new state."""
        if self._finished:
            raise ConfigurationError("this run has already finished; construct a new engine")

        t_hours = self.clock.tick()
        ctx = self._context()

        attention_before = self.conscious.attention
        fatigue_before = self.conscious.fatigue_episodes

        # 1. modules publish signals and production
        for module in self.modules:
            module.step(ctx)
        # 2./3. focus decision then the conscious system
        if self.policy.should_focus(ctx, self.conscious):
            self.conscious.focus(self.tissue.name, ctx)
        else:
            self.conscious.release(ctx)
        conscious_report = self.conscious.step(ctx)
        # 4./5. production then the only integrity-changing call
        self.subconscious.produce(ctx)
        repair = self.subconscious.step(ctx)
        # 6. decay
        self.field.step(self.clock.dt_hours)
        # 7. record
        spent = max(0.0, attention_before - self.conscious.attention)
        self.metrics.record(
            Sample(
                t_hours=t_hours,
                integrity=self.tissue.integrity,
                damage=self.tissue.damage,
                attention=self.conscious.attention,
                focused=self.conscious.is_focused,
                fatigued=self.conscious.fatigued,
                perceived_progress=conscious_report.perceived_progress,
                mediators=self.field.snapshot(),
                rates={
                    "subconscious.base_rate": ctx.signal("subconscious.base_rate"),
                    "subconscious.total_rate": ctx.signal("subconscious.total_rate"),
                    "subconscious.attention_attributable_rate": ctx.signal(
                        "subconscious.attention_attributable_rate"
                    ),
                    "subconscious.attention_multiplier": ctx.signal(
                        "subconscious.attention_multiplier", 1.0
                    ),
                },
            ),
            attention_spent_delta=spent,
            fatigue_episode=self.conscious.fatigue_episodes > fatigue_before,
        )

        return {
            "t_hours": t_hours,
            "integrity": round(self.tissue.integrity, 9),
            "damage": round(self.tissue.damage, 9),
            "attention": round(self.conscious.attention, 9),
            "focused": self.conscious.is_focused,
            "fatigued": self.conscious.fatigued,
            "applied_repair": round(repair.applied, 12),
        }

    def _announce_start(self) -> None:
        if self._started:
            return
        self._started = True
        self.bus.publish(
            0.0,
            EventKind.RUN_START,
            "engine",
            scenario=self.config.scenario,
            seed=self.config.seed,
            modules=list(self.module_names),
            parameter_digest=self.params.digest(),
        )

    def run_to(self, hours: float) -> SimulationResult:
        """Run until ``hours`` total elapsed time, then finalise."""
        if hours <= 0:
            raise ConfigurationError("hours must be positive")
        self._announce_start()
        target_steps = self.clock.steps_for(hours)
        while self.clock.steps < target_steps and not self._finished:
            self.step()
        return self.finalise()

    def run(self) -> SimulationResult:
        """Run the configured horizon to completion."""
        return self.run_to(self.config.horizon_hours)

    # -- finalisation ------------------------------------------------------
    def finalise(self) -> SimulationResult:
        if self._result is not None:
            return self._result
        if not self.metrics.samples:
            raise ConfigurationError("cannot finalise a run with no steps")

        self.bus.publish(
            self.clock.t_hours,
            EventKind.RUN_END,
            "engine",
            integrity=self.tissue.integrity,
            steps=self.clock.steps,
        )
        summary = self.metrics.summary()
        parameter_digest = self.params.digest()
        config_digest = self.config.digest()
        run_digest = _run_digest(
            parameter_digest=parameter_digest,
            config_digest=config_digest,
            metrics=summary,
            final_integrity=self.tissue.integrity,
        )

        self._finished = True
        self._result = SimulationResult(
            config=self.config,
            metrics=summary,
            samples=self.metrics.samples,
            events=self.bus.history,
            parameters=self.params.to_dict(),
            provenance=self.params.provenance_table(),
            provenance_summary=self.params.support_summary(),
            module_names=self.module_names,
            parameter_digest=parameter_digest,
            config_digest=config_digest,
            run_digest=run_digest,
            final_integrity=self.tissue.integrity,
        )
        return self._result

    # -- interactive control ----------------------------------------------
    def command(self, name: str, **kwargs: Any) -> dict[str, Any]:
        """Apply an out-of-band command, for the API and the console.

        Only focus control is exposed. There is deliberately no command that
        writes tissue integrity directly: nothing may bypass the repair rule.
        """
        ctx = self._context()
        if name == "focus":
            target = str(kwargs.get("target") or self.tissue.name)
            changed = self.conscious.focus(target, ctx)
            return {"command": "focus", "changed": changed, "target": target}
        if name == "release":
            changed = self.conscious.release(ctx)
            return {"command": "release", "changed": changed}
        if name == "set_policy":
            policy = str(kwargs.get("policy", ""))
            if policy not in FOCUS_POLICIES:
                raise ConfigurationError(f"unknown policy {policy!r}")
            self.config.focus_policy = policy
            self.policy = _make_policy(self.config)
            return {"command": "set_policy", "policy": policy}
        raise ConfigurationError(f"unknown command {name!r}")

    def snapshot(self) -> dict[str, Any]:
        """Current state, without advancing time."""
        return {
            "t_hours": self.clock.t_hours,
            "steps": self.clock.steps,
            "finished": self._finished,
            "scenario": self.config.scenario,
            "seed": self.config.seed,
            "focus_policy": self.config.focus_policy,
            "modules": list(self.module_names),
            "tissue": self.tissue.snapshot(),
            "mediators": {k: round(v, 9) for k, v in self.field.snapshot().items()},
            "conscious": {
                "focused": self.conscious.is_focused,
                "focus_target": self.conscious.focus_target,
                "attention": round(self.conscious.attention, 9),
                "fatigued": self.conscious.fatigued,
                "attention_spent": round(self.conscious.total_attention_spent, 9),
                "focus_hours": round(self.conscious.focus_hours, 9),
            },
            "signals": {k: round(v, 9) for k, v in sorted(ctx_signals(self).items())},
            "provided_samples": len(self.metrics),
        }


def ctx_signals(engine: SimulationEngine) -> dict[str, float]:
    """Last published signal values, for the snapshot view.

    Signals are produced per step inside the context, which the engine does not
    retain; the values that matter for inspection are re-derived from the last
    sample instead of reaching into a discarded context.
    """
    if not engine.metrics.samples:
        return {}
    last = engine.metrics.samples[-1]
    return dict(last.rates)


def _run_digest(
    *, parameter_digest: str, config_digest: str, metrics: Mapping[str, Any], final_integrity: float
) -> str:
    """Fingerprint a *completed* run.

    Two runs with identical parameters and config but different results cannot
    happen; if the digest ever disagrees, something upstream is non-deterministic
    and that is a bug worth failing loudly.
    """
    canonical = json.dumps(
        {
            "parameter_digest": parameter_digest,
            "config_digest": config_digest,
            "metrics": metrics,
            "final_integrity": round(final_integrity, 12),
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
