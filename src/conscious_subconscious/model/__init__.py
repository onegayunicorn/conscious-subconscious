"""The simulation model.

Import order note: :mod:`~conscious_subconscious.model.engine` is imported last
on purpose. It pulls in the module registry, whose modules import
:mod:`~conscious_subconscious.model.context`. Importing the engine first would
make that a partially-initialised-package import, which works but is the kind
of thing that breaks later for no visible reason.
"""

from __future__ import annotations

from .conscious import (
    AlwaysFocus,
    ConsciousReport,
    ConsciousSystem,
    FocusPolicy,
    IntermittentFocus,
    NeverFocus,
)
from .context import StepContext

# Must stay last: see the module docstring.
from .engine import FOCUS_POLICIES, RunConfig, SimulationEngine, SimulationResult
from .mediators import CHANNELS, MediatorField
from .metrics import MetricsRecorder, Sample
from .subconscious import RepairReport, SubconsciousSystem
from .tissue import Tissue

__all__ = [
    "AlwaysFocus",
    "CHANNELS",
    "ConsciousReport",
    "ConsciousSystem",
    "FOCUS_POLICIES",
    "FocusPolicy",
    "IntermittentFocus",
    "MediatorField",
    "MetricsRecorder",
    "NeverFocus",
    "RepairReport",
    "RunConfig",
    "Sample",
    "SimulationEngine",
    "SimulationResult",
    "StepContext",
    "SubconsciousSystem",
    "Tissue",
]
