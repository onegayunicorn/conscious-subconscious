# Data pipelines

Declarative DAG definitions for processing **recorded telemetry**. The Python
implementation lives in `src/conscious_subconscious/pipelines/`.

These are not the CI workflows. Continuous integration lives in
[`.github/workflows/`](../.github/workflows/).

## Definitions

| File | Purpose |
|---|---|
| `telemetry_features.yaml` | Validate a recording, resample the heart-rate channel, extract descriptive and spectral features per channel. |
| `session_export.yaml` | Minimal validate-then-summarise pass, cheap enough to run on every recorded session. |

## Input format

A CSV with exactly these columns, which is the shape the serial and BLE adapters
emit, so live hardware recordings need no conversion:

```text
t_seconds,channel,value
0.000000,heart_rate,62.400000
0.000000,hrv_index,0.550000
1.000000,heart_rate,61.900000
```

Device time (`t_seconds`) is not simulation time. The two must never be mixed:
one is a sensor's clock, the other is a virtual clock with a fixed step, and
conflating them is how a pipeline result gets attributed to the wrong interval.

## Step types

| `uses` | What it does |
|---|---|
| `load_csv` | Read a recording into memory. |
| `validate` | Quality gate: row count, non-finite values, duplicate `(t, channel)` pairs. Fails the pipeline rather than passing junk downstream. |
| `resample` | Collapse duplicate timestamps and interpolate one channel onto a uniform grid. |
| `features` | Per-channel count, mean, standard deviation, min, max, duration, estimated rate, plus band powers from the configured bands. |
| `summarise` | Merge upstream outputs, refusing to overwrite an existing key. |
| `write_json` | Write selected keys of an upstream output to a JSON file. |

## Running one

```python
from conscious_subconscious.pipelines import PipelineRunner, load_pipeline

spec = load_pipeline("pipelines/session_export.yaml")
run = PipelineRunner(spec).run(workdir=".")
print(run.as_dict(include_outputs=False))
print(run.log)
```

YAML needs PyYAML (`pip install PyYAML`). A pipeline can also be written as JSON,
in which case only the standard library is required.

## Boundaries

- A pipeline result describes a **recording**. A recording describes a **sensor**.
  Neither is a statement about a person, and no pipeline here produces a clinical
  interpretation.
- Spectral bands in these definitions are **labels for demonstration**, not
  clinical HRV bands. Nothing downstream should treat them as standard.
- A missing value is written as `null`, never as `0`. Zero is a measurement; an
  absent measurement is not.
