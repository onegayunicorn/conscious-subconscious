"""The pipeline runner: a tiny DAG executor.

Scope is deliberate. This is not Airflow and it is not trying to be. It
executes a handful of in-process steps in dependency order, refuses to run a
graph with a cycle, and reports honestly which steps failed.

YAML is used because the DAG definitions are meant to be read and edited by
people; ``PyYAML`` is imported lazily so the core package keeps its
zero-dependency property.
"""

from __future__ import annotations

import dataclasses
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from ..core.errors import PipelineError
from .steps import PipelineContext, available_steps, get_step

__all__ = ["StepSpec", "PipelineSpec", "PipelineRun", "PipelineRunner", "load_pipeline"]

_KNOWN_KEYS = {"name", "description", "version", "steps"}


@dataclass(frozen=True, slots=True)
class StepSpec:
    """One node in the DAG."""

    name: str
    uses: str
    needs: tuple[str, ...] = ()
    params: Mapping[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise PipelineError("a step needs a name")
        if not self.uses:
            raise PipelineError(f"step {self.name!r} needs a 'uses'")

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> StepSpec:
        allowed = {"name", "uses", "needs", "params"}
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise PipelineError(f"step has unknown key(s): {unknown}")
        needs = data.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        return cls(
            name=str(data.get("name", "")),
            uses=str(data.get("uses", "")),
            needs=tuple(str(item) for item in needs),
            params=dict(data.get("params", {})),
        )


@dataclass(frozen=True, slots=True)
class PipelineSpec:
    """A named DAG."""

    name: str
    description: str = ""
    version: str = "1"
    steps: tuple[StepSpec, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> PipelineSpec:
        unknown = sorted(set(data) - _KNOWN_KEYS)
        if unknown:
            raise PipelineError(f"pipeline has unknown key(s): {unknown}")
        name = data.get("name")
        if not name:
            raise PipelineError("a pipeline needs a name")
        raw_steps = data.get("steps")
        if not isinstance(raw_steps, Sequence) or not raw_steps:
            raise PipelineError("a pipeline needs a non-empty 'steps' list")

        steps = tuple(StepSpec.from_dict(entry) for entry in raw_steps)
        seen: set[str] = set()
        for step in steps:
            if step.name in seen:
                raise PipelineError(f"duplicate step name {step.name!r}")
            seen.add(step.name)
        for step in steps:
            for dependency in step.needs:
                if dependency not in seen:
                    raise PipelineError(f"step {step.name!r} needs unknown step {dependency!r}")
        spec = cls(
            name=str(name),
            description=str(data.get("description", "")),
            version=str(data.get("version", "1")),
            steps=steps,
        )
        spec.order()  # fail early on a cycle, before anything else is considered

        # Validate parameters at load time, not part-way through a run. This runs
        # after the cycle check so that a cyclic DAG reports the cycle rather than
        # whichever unrelated parameter happens to be missing.
        for step in steps:
            missing = sorted(set(get_step(step.uses).required_params()) - set(step.params))
            if missing:
                raise PipelineError(
                    f"step {step.name!r} ({step.uses}) is missing required parameter(s): "
                    + ", ".join(missing)
                )
        return spec

    def order(self) -> tuple[str, ...]:
        """Return step names in a valid execution order (topological).

        Ties are broken alphabetically so the order is stable across runs. An
        unstable order would make a pipeline's output depend on hash seeding,
        which is precisely the kind of non-determinism this project exists to
        avoid.
        """
        remaining = {step.name: set(step.needs) for step in self.steps}
        ordered: list[str] = []
        while remaining:
            ready = sorted(name for name, needs in remaining.items() if not needs)
            if not ready:
                raise PipelineError(
                    "the pipeline contains a dependency cycle among: "
                    + ", ".join(sorted(remaining))
                )
            for name in ready:
                ordered.append(name)
                del remaining[name]
            for needs in remaining.values():
                needs.difference_update(ready)
        return tuple(ordered)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "steps": [
                {
                    "name": step.name,
                    "uses": step.uses,
                    "needs": list(step.needs),
                    "params": dict(step.params),
                }
                for step in self.steps
            ],
            "order": list(self.order()),
        }


@dataclass(slots=True)
class PipelineRun:
    """The result of one pipeline execution."""

    pipeline: str
    outputs: dict[str, dict[str, Any]]
    log: list[str]
    durations_seconds: dict[str, float]

    @property
    def final(self) -> dict[str, Any]:
        """Output of the last step in execution order."""
        if not self.outputs:
            raise PipelineError("the pipeline produced no outputs")
        return self.outputs[list(self.outputs)[-1]]

    def as_dict(self, *, include_outputs: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "pipeline": self.pipeline,
            "steps": list(self.outputs),
            "durations_seconds": dict(self.durations_seconds),
            "log": list(self.log),
        }
        if include_outputs:
            payload["outputs"] = {k: v for k, v in self.outputs.items()}
        return payload


class PipelineRunner:
    """Executes a :class:`PipelineSpec`."""

    #: Hard ceiling on steps, so a generated DAG cannot become a denial of service.
    MAX_STEPS: ClassVar[int] = 128

    def __init__(self, spec: PipelineSpec) -> None:
        if len(spec.steps) > self.MAX_STEPS:
            raise PipelineError(
                f"pipeline has {len(spec.steps)} steps; the limit is {self.MAX_STEPS}"
            )
        self.spec = spec

    def run(
        self,
        *,
        inputs: Mapping[str, Any] | None = None,
        workdir: str | Path | None = None,
    ) -> PipelineRun:
        context = PipelineContext(
            inputs=inputs,
            workdir=Path(workdir) if workdir is not None else Path(),
        )
        durations: dict[str, float] = {}
        outputs: dict[str, dict[str, Any]] = {}

        for name in self.spec.order():
            step_spec = next(step for step in self.spec.steps if step.name == name)
            step = get_step(step_spec.uses)(name, step_spec.params)
            started = time.perf_counter()
            try:
                result = step.run(context)
            except PipelineError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                raise PipelineError(f"step {name!r} ({step_spec.uses}) failed: {exc}") from exc
            finally:
                durations[name] = round(time.perf_counter() - started, 6)
            if not isinstance(result, dict):
                raise PipelineError(f"step {name!r} returned {type(result).__name__}, not a dict")
            context.outputs[name] = result
            outputs[name] = result

        return PipelineRun(
            pipeline=self.spec.name,
            outputs=outputs,
            log=list(context.log),
            durations_seconds=durations,
        )


def load_pipeline(path: str | Path) -> PipelineSpec:
    """Load a pipeline definition from YAML, or from JSON if the suffix says so."""
    location = Path(path)
    if not location.is_file():
        raise PipelineError(f"pipeline file not found: {location}")

    text = location.read_text(encoding="utf-8")
    if location.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PipelineError(f"{location} is not valid JSON: {exc}") from exc
    else:
        try:
            import yaml  # noqa: PLC0415
        except ImportError as exc:
            raise PipelineError(
                "reading YAML pipelines needs PyYAML: pip install PyYAML "
                "(or write the pipeline as JSON)"
            ) from exc
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise PipelineError(f"{location} is not valid YAML: {exc}") from exc

    if not isinstance(data, dict):
        raise PipelineError(f"{location} must contain a mapping at the top level")
    return PipelineSpec.from_dict(data)


def describe_steps() -> list[dict[str, Any]]:
    """Machine-readable list of available step types."""
    described: list[dict[str, Any]] = []
    for uses in available_steps():
        cls = get_step(uses)
        described.append(
            {
                "uses": uses,
                "class": cls.__name__,
                "doc": (cls.__doc__ or "").strip().splitlines()[0] if cls.__doc__ else "",
            }
        )
    return described
