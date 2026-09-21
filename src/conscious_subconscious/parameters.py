"""The canonical default parameter set.

Every number in the model is declared once, here, with its provenance. Modules
read parameters through :class:`ParameterSet`; nothing else in the codebase is
allowed to hold a bare magic number.

Read the ``provenance`` column before believing any result this project
produces. The overwhelming majority of these values are ``assumed`` or
``invented``.
"""

from __future__ import annotations

from .core.params import Parameter, ParameterSet
from .core.params import Provenance as P

__all__ = ["default_parameters", "PARAMETER_COUNT"]

_PARAMETERS: tuple[Parameter, ...] = (
    # ------------------------------------------------------------------ tissue
    Parameter(
        key="tissue.initial_integrity",
        value=0.20,
        unit="fraction",
        provenance=P.INVENTED,
        note=(
            "The source document starts at either 100% or 80% damage in different "
            "snippets. 0.20 integrity is the 80%-damage case, expressed as integrity."
        ),
        minimum=0.0,
        maximum=0.99,
    ),
    Parameter(
        key="tissue.max_integrity",
        value=1.0,
        unit="fraction",
        provenance=P.ASSUMED,
        note="Normalised ceiling. No tissue is modelled below this abstraction.",
        minimum=0.01,
        maximum=1.0,
    ),
    # ------------------------------------------------------------- subconscious
    Parameter(
        key="subconscious.base_repair_rate",
        value=0.02,
        unit="integrity/hour",
        provenance=P.INVENTED,
        note=(
            "Rescaled from the source document's '0.5 per tick' constant. The "
            "source never states a tick duration, so the per-hour value is a choice."
        ),
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="subconscious.growth_factor_production",
        value=0.45,
        unit="field-units/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="subconscious.damage_signal_gain",
        value=0.80,
        unit="dimensionless",
        provenance=P.ASSUMED,
        note="Damaged tissue emits more repair signal. Direction is well founded, magnitude is not.",
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="subconscious.gf_half_saturation",
        value=0.50,
        unit="field-units",
        provenance=P.ASSUMED,
        note="Half-saturation constant for the Michaelis-Menten repair response.",
        minimum=1e-06,
        maximum=100.0,
    ),
    Parameter(
        key="subconscious.cytokine_production",
        value=0.30,
        unit="field-units/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    # ---------------------------------------------------------- mediator field
    Parameter(
        key="mediator.growth_factor.decay_per_hour",
        value=0.12,
        unit="1/hour",
        provenance=P.ASSUMED,
        note="Channels are leaky integrators; the source document had no decay at all.",
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="mediator.cytokine.decay_per_hour",
        value=0.25,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="mediator.atp.decay_per_hour",
        value=0.35,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="mediator.perfusion.decay_per_hour",
        value=0.50,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="mediator.neural_drive.decay_per_hour",
        value=0.90,
        unit="1/hour",
        provenance=P.ASSUMED,
        note="Fast decay: modelled neural drive does not persist without attention.",
        minimum=0.0,
        maximum=10.0,
    ),
    # ----------------------------------------------------------------- conscious
    Parameter(
        key="conscious.neural_drive_gain",
        value=1.0,
        unit="field-units/hour",
        provenance=P.INVENTED,
        note=(
            "The source document's random '1.0-3.0 boost', turned into an explicit, "
            "inspectable constant. It has no empirical basis."
        ),
        minimum=0.0,
        maximum=100.0,
    ),
    Parameter(
        key="conscious.neural_drive_jitter",
        value=0.0,
        unit="field-units/hour",
        provenance=P.INVENTED,
        note=(
            "The source drew uniform(1.0, 3.0) every tick, which makes runs "
            "irreproducible. Default is 0; raise it to model trial-to-trial variability."
        ),
        minimum=0.0,
        maximum=100.0,
    ),
    Parameter(
        key="conscious.neural_drive_coupling",
        value=0.75,
        unit="dimensionless",
        provenance=P.INVENTED,
        note=(
            "THE CENTRAL UNVALIDATED ASSUMPTION: how strongly the modelled neural "
            "drive multiplies the repair rate. Set this to 0.0 to switch the entire "
            "mind-over-tissue claim off and recover baseline-only behaviour."
        ),
        minimum=0.0,
        maximum=100.0,
    ),
    Parameter(
        key="conscious.attention_budget",
        value=1.0,
        unit="fraction",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="conscious.attention_drain_per_hour",
        value=0.18,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="conscious.attention_recovery_per_hour",
        value=0.24,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="conscious.fatigue_threshold",
        value=0.25,
        unit="fraction",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="conscious.resume_attention",
        value=0.75,
        unit="fraction",
        provenance=P.ASSUMED,
        note=(
            "Attention must recover to this level before focus is re-engaged. "
            "The gap to fatigue_threshold is controller hysteresis, not biology."
        ),
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="conscious.perceived_gain",
        value=1.0,
        unit="dimensionless",
        provenance=P.ASSUMED,
        note="Maps actual integrity onto 'how it feels'. The source document conflated the two.",
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="conscious.perceived_bias",
        value=0.0,
        unit="fraction",
        provenance=P.ASSUMED,
        note="Optimism/pessimism offset in felt progress. Zero by default.",
        minimum=-1.0,
        maximum=1.0,
    ),
    # ------------------------------------------------------------------ modules
    Parameter(
        key="module.inflammation.baseline",
        value=0.25,
        unit="fraction",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="module.inflammation.repair_inhibition",
        value=0.50,
        unit="dimensionless",
        provenance=P.ASSUMED,
        note="Fraction of repair capacity that inflammation can suppress at full level.",
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="module.inflammation.settling_rate",
        value=0.50,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=100.0,
    ),
    Parameter(
        key="module.perfusion.baseline",
        value=0.55,
        unit="fraction",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="module.perfusion.vasodilation_gain",
        value=0.40,
        unit="fraction",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="module.perfusion.response_rate",
        value=0.60,
        unit="1/hour",
        provenance=P.ASSUMED,
        minimum=0.0,
        maximum=100.0,
    ),
    Parameter(
        key="module.circadian.amplitude",
        value=0.15,
        unit="fraction",
        provenance=P.ASSUMED,
        note="Circadian variation in repair signalling is documented; this depth is a guess.",
        minimum=0.0,
        maximum=1.0,
    ),
    Parameter(
        key="module.circadian.period_hours",
        value=24.0,
        unit="hour",
        provenance=P.LITERATURE,
        note=(
            "Human circadian period is approximately 24 h (endogenous period is "
            "slightly longer than 24 h, entrained to 24 h by light). See "
            "research/literature-review.md."
        ),
        minimum=1.0,
        maximum=168.0,
    ),
    Parameter(
        key="module.autonomic.parasympathetic_gain",
        value=0.30,
        unit="dimensionless",
        provenance=P.ASSUMED,
        note="Maps a normalised HRV-style index onto modelled parasympathetic tone.",
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="module.autonomic.perfusion_gain",
        value=0.25,
        unit="fraction",
        provenance=P.ASSUMED,
        note=(
            "Modelled vasodilation attributable to parasympathetic tone. The "
            "direction is plausible; the size is invented for this model."
        ),
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="module.expectancy.gain",
        value=0.0,
        unit="dimensionless",
        provenance=P.INVENTED,
        note=(
            "DISABLED BY DEFAULT (0.0). Placebo/expectancy effects are real for "
            "symptom reporting; the size of any effect on tissue repair is not "
            "knowable from the source document, so the model refuses to guess."
        ),
        minimum=0.0,
        maximum=10.0,
    ),
    Parameter(
        key="module.expectancy.perception_gain",
        value=0.0,
        unit="dimensionless",
        provenance=P.INVENTED,
        note=(
            "DISABLED BY DEFAULT (0.0). Would let expectancy bias *felt* progress "
            "(perception) without touching actual integrity."
        ),
        minimum=0.0,
        maximum=10.0,
    ),
)

PARAMETER_COUNT = len(_PARAMETERS)


def default_parameters() -> ParameterSet:
    """Return a fresh copy of the canonical parameter set."""
    return ParameterSet(_PARAMETERS)
