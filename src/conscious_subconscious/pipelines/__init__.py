"""Data pipelines: DAG definitions, signal processing, features.

These operate on *recorded telemetry*, not on the simulation itself. The
distinction matters: a pipeline result is a statement about a recording, and the
recording is a statement about a sensor. Neither is a statement about a person.

DAG definitions live at ``pipelines/*.yaml`` in the repository root.
"""

from __future__ import annotations

from .dsp import band_power, channel_series, mean, moving_average, resample_linear, stdev, zscore
from .runner import (
    PipelineRun,
    PipelineRunner,
    PipelineSpec,
    StepSpec,
    describe_steps,
    load_pipeline,
)
from .steps import (
    FeatureStep,
    LoadCsvStep,
    PipelineContext,
    ResampleStep,
    Step,
    SummariseStep,
    ValidateStep,
    WriteJsonStep,
    available_steps,
    get_step,
    register_step,
)

__all__ = [
    "FeatureStep",
    "LoadCsvStep",
    "PipelineContext",
    "PipelineRun",
    "PipelineRunner",
    "PipelineSpec",
    "ResampleStep",
    "Step",
    "StepSpec",
    "SummariseStep",
    "ValidateStep",
    "WriteJsonStep",
    "available_steps",
    "band_power",
    "channel_series",
    "describe_steps",
    "get_step",
    "load_pipeline",
    "mean",
    "moving_average",
    "register_step",
    "resample_linear",
    "stdev",
    "zscore",
]
