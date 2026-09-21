"""The conscious system: deliberate, costly, finite attention.

Three things distinguish this from the source document's ``ConsciousMind``:

1. **Attention is a budget, not a switch.** Focus spends it, rest restores it,
   and below a threshold the mind is flagged as fatigued. The source's focus was
   binary and free.
2. **Perceived progress is separate from actual integrity.** The source printed
   one number and treated it as both what the body is doing and what the mind
   sees. Those are different quantities, and conflating them is how a
   simulation starts to look like evidence. Both are tracked here.
3. **The effect is a parameter, not a premise.** Attention raises the
   ``neural_drive`` channel. Whether that changes repair at all is decided by
   ``conscious.neural_drive_coupling`` in the subconscious rule, which defaults
   to a deliberately visible, obviously invented number.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..core.events import EventKind
from ..core.params import ParameterSet
from .context import StepContext

__all__ = [
    "ConsciousSystem",
    "ConsciousReport",
    "FocusPolicy",
    "NeverFocus",
    "AlwaysFocus",
    "IntermittentFocus",
]


@dataclass(frozen=True, slots=True)
class ConsciousReport:
    """What the conscious system did this step."""

    focused: bool
    attention: float
    fatigued: bool
    drive_injected: float
    perceived_progress: float
    actual_progress: float
    perception_gap: float

    def as_dict(self) -> dict[str, float | bool]:
        return {
            "focused": self.focused,
            "attention": self.attention,
            "fatigued": self.fatigued,
            "drive_injected": self.drive_injected,
            "perceived_progress": self.perceived_progress,
            "actual_progress": self.actual_progress,
            "perception_gap": self.perception_gap,
        }


class FocusPolicy(Protocol):
    """Decides, each step, whether attention should be engaged."""

    name: str

    def should_focus(self, ctx: StepContext, conscious: ConsciousSystem) -> bool:
        """Return True to hold attention on the target this step."""
        ...


class NeverFocus:
    """Attention is never engaged. The baseline condition."""

    name = "never"

    def should_focus(self, ctx: StepContext, conscious: ConsciousSystem) -> bool:
        return False


def _hysteretic_focus(
    ctx: StepContext,
    conscious: ConsciousSystem,
    policy: Any,
    band: tuple[float, float] | None,
) -> bool:
    """Shared engage/release logic for the two focusing policies.

    Attention is released when it falls to the fatigue threshold and only
    re-engaged once it has recovered to ``conscious.resume_attention``. The gap
    between those two levels is hysteresis: without it, a policy that re-engages
    the instant it recovers will flap against the threshold dozens of times an
    hour, and the fatigue counter becomes a measure of the controller rather
    than of anything modelled.
    """
    if ctx.tissue.is_healed:
        policy._engaged = False
        return False

    if policy._engaged and conscious.attention <= ctx.params.value("conscious.fatigue_threshold"):
        policy._engaged = False

    if not policy._engaged:
        if conscious.attention < ctx.params.value("conscious.resume_attention"):
            return False
        if band is not None:
            enter, exit_ = band
            damage = ctx.tissue.damage
            if not exit_ < damage <= enter:
                return False
        policy._engaged = True
    return True


class AlwaysFocus:
    """Hold attention for as long as the budget allows, releasing only to recover.

    This is "trying as hard as you can, continuously" — not "succeeding". The
    run shows what forced sustained attention costs, which is the interesting
    part: attention is spent far faster than it returns, so the duty cycle is
    well below one.
    """

    name = "always"

    def __init__(self) -> None:
        self._engaged = False

    def should_focus(self, ctx: StepContext, conscious: ConsciousSystem) -> bool:
        return _hysteretic_focus(ctx, conscious, self, band=None)


class IntermittentFocus:
    """Focus on a middle band of damage only, and rest when fatigued.

    Mirrors the source document's hand-written rule ("focus once damage drops
    below 80%, release below 20%"), but takes the band from configuration and
    respects the attention budget.
    """

    name = "intermittent"

    def __init__(self, enter_damage: float = 0.80, exit_damage: float = 0.20) -> None:
        if exit_damage >= enter_damage:
            raise ValueError("exit_damage must be below enter_damage")
        self.enter_damage = enter_damage
        self.exit_damage = exit_damage
        self._engaged = False

    def should_focus(self, ctx: StepContext, conscious: ConsciousSystem) -> bool:
        return _hysteretic_focus(ctx, conscious, self, band=(self.enter_damage, self.exit_damage))


class ConsciousSystem:
    """Deliberate attention with a finite budget and an honest perception channel."""

    name = "conscious"

    def __init__(self, params: ParameterSet) -> None:
        self.params = params
        self.focus_target: str | None = None
        self.attention = params.value("conscious.attention_budget")
        self.fatigued = False
        self.total_attention_spent = 0.0
        self.focus_hours = 0.0
        #: Number of times attention has dropped below the fatigue threshold.
        self.fatigue_episodes = 0
        self._recovered_after_fatigue = True
        self._last: ConsciousReport | None = None

    # -- intent ------------------------------------------------------------
    def focus(self, target: str, ctx: StepContext) -> bool:
        """Direct attention at ``target``. Returns True if state changed."""
        if not target:
            raise ValueError("focus target must be non-empty")
        if self.focus_target == target:
            return False
        self.focus_target = target
        ctx.bus.publish(
            ctx.t_hours,
            EventKind.CONSCIOUS_FOCUS,
            self.name,
            target=target,
            attention=self.attention,
        )
        return True

    def release(self, ctx: StepContext) -> bool:
        """Withdraw attention. Returns True if state changed."""
        if self.focus_target is None:
            return False
        previous = self.focus_target
        self.focus_target = None
        ctx.bus.publish(
            ctx.t_hours,
            EventKind.CONSCIOUS_RELEASE,
            self.name,
            target=previous,
            attention=self.attention,
        )
        return True

    @property
    def is_focused(self) -> bool:
        return self.focus_target is not None

    # -- dynamics ----------------------------------------------------------
    def step(self, ctx: StepContext) -> ConsciousReport:
        params = self.params
        dt = ctx.dt_hours
        drive_injected = 0.0

        if self.is_focused:
            gain = params.value("conscious.neural_drive_gain") * self.attention
            jitter = params.value("conscious.neural_drive_jitter")
            if jitter > 0.0:
                # Jitter is the ONLY reason this project can produce two
                # different numbers from the same configuration. It is off by
                # default and is drawn from a named substream so that raising it
                # does not perturb any other component.
                gain += ctx.rng.uniform("conscious.jitter", 0.0, jitter)
            gain = max(0.0, gain)
            drive_injected = gain * dt
            ctx.field.add("neural_drive", drive_injected)

            spent = min(self.attention, params.value("conscious.attention_drain_per_hour") * dt)
            self.attention -= spent
            self.total_attention_spent += spent
            self.focus_hours += dt

            if not self.fatigued and self.attention <= params.value("conscious.fatigue_threshold"):
                self.fatigued = True
                self.fatigue_episodes += 1
                self._recovered_after_fatigue = False
                ctx.bus.publish(
                    ctx.t_hours, EventKind.ATTENTION_FATIGUE, self.name, attention=self.attention
                )
        else:
            restored = params.value("conscious.attention_recovery_per_hour") * dt
            self.attention = min(
                params.value("conscious.attention_budget"), self.attention + restored
            )
            if self.fatigued and not self._recovered_after_fatigue:
                if self.attention > params.value("conscious.fatigue_threshold"):
                    self.fatigued = False
                    self._recovered_after_fatigue = True
                    ctx.bus.publish(
                        ctx.t_hours,
                        EventKind.ATTENTION_RECOVERED,
                        self.name,
                        attention=self.attention,
                    )

        # Perception. Actual progress comes from the tissue; felt progress adds
        # an optimism/pessimism bias plus any expectancy contribution. The gap
        # between them is reported rather than hidden.
        actual = ctx.tissue.integrity
        expectancy = ctx.signal("expectancy", 0.0)
        perceived = (
            params.value("conscious.perceived_gain") * actual
            + params.value("conscious.perceived_bias")
            + expectancy
        )
        perceived = max(0.0, min(1.0, perceived))

        ctx.set_signal("attention", self.attention)
        ctx.set_signal("focused", 1.0 if self.is_focused else 0.0)
        ctx.set_signal("perceived_progress", perceived)

        report = ConsciousReport(
            focused=self.is_focused,
            attention=self.attention,
            fatigued=self.fatigued,
            drive_injected=drive_injected,
            perceived_progress=perceived,
            actual_progress=actual,
            perception_gap=perceived - actual,
        )
        self._last = report
        return report

    @property
    def last_report(self) -> ConsciousReport | None:
        return self._last

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role": "deliberate attention with a finite budget",
            "parameters": [
                "conscious.neural_drive_gain",
                "conscious.neural_drive_jitter",
                "conscious.attention_budget",
                "conscious.attention_drain_per_hour",
                "conscious.attention_recovery_per_hour",
                "conscious.fatigue_threshold",
                "conscious.perceived_gain",
                "conscious.perceived_bias",
            ],
        }
