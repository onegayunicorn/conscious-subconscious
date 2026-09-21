"""Shared fixtures.

The ``src`` directory is put on ``sys.path`` here so the suite runs from a clean
checkout without requiring an editable install. That matters: CI installs the
package, but a contributor who just cloned the repo should be able to type
``pytest`` and get a real answer.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conscious_subconscious.model.engine import RunConfig, SimulationEngine  # noqa: E402

#: Deterministic seed used by every test that needs one, so a failure reproduces.
TEST_SEED = 424242


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def engine_factory() -> Callable[..., SimulationEngine]:
    """Build an engine from keyword arguments, with test-friendly defaults."""

    def make(**kwargs: object) -> SimulationEngine:
        kwargs.setdefault("seed", TEST_SEED)
        kwargs.setdefault("dt_hours", 0.1)
        kwargs.setdefault("horizon_hours", 48.0)
        return SimulationEngine(RunConfig(**kwargs))  # type: ignore[arg-type]

    return make


@pytest.fixture
def sample_recording(tmp_path: Path) -> Path:
    """A small, well-formed telemetry recording."""
    path = tmp_path / "session.csv"
    lines = ["t_seconds,channel,value"]
    for index in range(40):
        t = index * 0.25
        lines.append(f"{t:.3f},heart_rate,{62.0 + (index % 7) * 0.5:.3f}")
        lines.append(f"{t:.3f},hrv_index,{0.50 + (index % 5) * 0.01:.3f}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
