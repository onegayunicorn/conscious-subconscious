"""conscious-subconscious — a reproducible simulation sandbox.

The project models the interaction between an autonomous *subconscious*
homeostatic repair process and a deliberate *conscious* attentional process
applied to a damaged tissue model.

Two ideas shape every module in this package:

1. **Reproducibility is a feature, not a hope.** Every run is driven by a
   seeded random-number generator and a virtual clock, so the same
   configuration always produces the same result, byte for byte, and emits a
   digest that proves it.

2. **Provenance is mandatory.** Every numeric constant carries a
   :class:`~conscious_subconscious.core.params.Provenance` tag saying where it
   came from. Most constants in this model are *assumed* or *invented*; the
   sandbox says so out loud rather than implying empirical support.
"""

from __future__ import annotations

__all__ = ["__version__", "DISCLAIMER", "PROVENANCE_POLICY"]

__version__ = "0.1.0"

DISCLAIMER = (
    "EDUCATIONAL AND ARTISTIC SIMULATION ONLY. This project is not a medical "
    "device. It does not diagnose, treat, cure or prevent any condition, and it "
    "provides no medical advice. The model encodes an UNVALIDATED assumption — "
    "that conscious attention can modulate a modelled tissue-repair rate. That "
    "assumption is not established clinical fact. Do not use any output of this "
    "project to make a decision about a human body."
)

PROVENANCE_POLICY = (
    "Every parameter is tagged measured | literature | assumed | invented. "
    "'assumed' and 'invented' parameters are free knobs with no empirical "
    "support: conclusions that depend on them are properties of the model, "
    "not findings about biology. Run 'cs-sim parameters' to list them."
)
