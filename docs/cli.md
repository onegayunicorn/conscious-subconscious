# Command line

`cs-sim` is the command-line front end (`sim/cli.py`). Everything the package does
is reachable from it, and nothing it prints is a medical claim.

> **Boundary.** Every run is an educational simulation. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Invocation

After installation the console script is on the path:

```bash
cs-sim <subcommand> [options]
```

Without installing, run it as a module from a checkout:

```bash
PYTHONPATH=src python3 -m conscious_subconscious.sim.cli <subcommand> [options]
```

Both forms take the same arguments. Output goes to stdout unless `--out PATH` is
given, so the tool composes with pipes. `--json` emits machine-readable output on
the *same* channel rather than switching streams.

### Global option

```bash
cs-sim --version     # prints: cs-sim 0.1.0
```

### Exit codes

| Code | Meaning |
| ---: | --- |
| 0 | Success. |
| 1 | A user-input problem: unknown scenario, malformed `--set`, bad sweep range. |
| 2 | A configuration error surfaced from the model layer. |

Note that `argparse` also exits 2 on an argument-parsing error, so a `2` can mean
either "the model rejected the configuration" or "the shell passed an argument the
parser did not understand". Both messages go to stderr and name the problem.

### Options shared by the simulation subcommands

`run`, `compare`, `sweep` and `sensitivity` accept:

| Option | Default | Meaning |
| --- | --- | --- |
| `--seed INT` | 20260921 | Root seed for the deterministic RNG. |
| `--dt FLOAT` | 0.05 | Time step in hours. |
| `--horizon FLOAT` | 72.0 | Run length in hours. |
| `--policy {never,always,intermittent}` | scenario's own | Focus policy. Overrides the scenario's. |
| `--modules LIST` | scenario's own | Comma-separated module list, or `none`. |
| `--set KEY=VALUE` | — | Parameter override. Repeatable. |
| `--out PATH` | stdout | Write output to a file, creating parent directories. |
| `--json` | off | Emit JSON instead of the rendered form. |
| `--samples` | off | Include the full time series (with `--json`). |
| `--scenarios-file PATH` | — | Extra scenarios from a JSON file. Repeatable. |

`--set` is the sharpest tool here, so its behaviour matters: an overridden
parameter is always recorded with the provenance grade `assumed`, whatever the
default's grade was. See [provenance.md](provenance.md).

## `run`

Run one scenario. Without flags it prints a short digest block:

```console
$ cs-sim run --scenario focused
scenario=focused seed=20260921 modules=circadian,inflammation,perfusion
  time_to_50pct_repair_hours = 27.6
  time_to_full_repair_hours = 50.4
  area_under_damage_integrity_hours = 21.090225538
  attention_attributable_fraction = 0.144677131
  focus_hours = 29.45
  fatigue_episodes = 10
  run_digest = c0989928adcbcfad
```

With `--report`, it emits a Markdown report beginning with the boundary note and
the provenance of the parameters *before* any result. The shape is documented in
[provenance.md](provenance.md#how-to-read-a-report). If the scenario declares a
`caveat`, it is injected as its own section above "What this does not show".

```bash
cs-sim run --scenario intermittent --report --out out/report.md
```

With `--json`, it emits `SimulationResult.as_dict()`: `scenario`, `seed`,
`config`, `modules`, `final_integrity`, `metrics`, `provenance_summary`,
`digests` (parameters / config / run), `disclaimer`, plus `events` and — if
`--samples` is passed — `samples` and the per-parameter `provenance` list.
`--samples` is off by default because a 72 h run at `dt = 0.05` produces 1440
samples.

## `compare`

Runs several scenarios with identical parameters and seed, and prints a
side-by-side table with deltas against the first one. Default set:
`baseline focused intermittent`.

```console
$ cs-sim compare
# Scenario comparison

3 runs, identical parameters and seed unless a scenario overrides them. Deltas are relative to `baseline`.

| Metric | `baseline` | `focused` | `intermittent` |
|---|---:|---:|---:|
| Time to 50% repair (h) | 33.95 | 27.6 | 27.6 |
| Time to full repair (h) | 62.05 | 50.4 | 52.3 |
| Area under damage | 26.6894 | 21.0902 | 21.2807 |
| Attributable to attention | 0 | 0.1447 | 0.1191 |
| Attention engaged (h) | 0 | 29.45 | 23.85 |
| Fatigue episodes | 0 | 10 | 8 |

### Change relative to baseline

| Scenario | Time to 50% repair | Area under damage | Attention engaged |
|---|---:|---:|---:|
| `baseline` | — | — | 0 h |
| `focused` | -18.7% | -21.0% | 29.45 h |
| `intermittent` | -18.7% | -20.3% | 23.85 h |

A negative percentage is a shorter time or a smaller area, i.e. the model repaired faster. It is a property of the coupling constant, not evidence about people.

### Scenario notes

- **`baseline`** — seed 20260921, digest `3d432c144d7f8a5c`
- **`focused`** — seed 20260921, digest `c0989928adcbcfad`
- **`intermittent`** — seed 20260921, digest `1c035a34f869ccae`
```

```bash
cs-sim compare --scenarios baseline focused focused-uncoupled --json --out out/control.json
```

Choosing your own set is how the control is exercised: `focused-uncoupled` sets
`conscious.neural_drive_coupling` to `0.0` and CI asserts that every **repair**
metric matches `baseline` exactly. The attention-accounting measures
(`focus_hours`, `attention_spent`, `min_attention`, `fatigue_episodes`,
`peak_neural_drive`) do differ, because the control genuinely holds attention — it
just has no route into the repair path. See
[testing.md](testing.md#golden-tests-and-the-determinism-contract).

## `sweep`

Re-runs one scenario once per value of a single parameter, and prints the headline
metrics plus a verdict on monotonicity.

```bash
cs-sim sweep --param conscious.neural_drive_coupling --values 0:2:0.5
```

`--values` accepts a comma list or `start:stop[:step]` ranges; a range without a
step gets five intervals, and a range implying fewer than 2 or more than 500 points
is rejected. `--param` and `--values` are both required. `--scenario` defaults to
`focused` here, unlike `run`.

```console
$ cs-sim sweep --param conscious.neural_drive_coupling --values 0:2:0.5
# Parameter sweep — `conscious.neural_drive_coupling`

- **Scenario:** `focused`
- **Seed:** 20260921
- **Declared provenance of this parameter:** `invented`
- **Default value:** 0.75

> This parameter has **no empirical support**. Everything below is a consequence of that choice, not a measurement.

| conscious.neural_drive_coupling | Time to 50% repair (h) | Time to full repair (h) | Area under damage | Attributable to attention |
|---:|---:|---:|---:|---:|
| 0 | 33.95 | 62.05 | 26.69 | 0 |
| 0.5 | 29.3 | 53.5 | 22.72 | 0.1126 |
| 1 | 26 | 47.25 | 19.64 | 0.1796 |
| 1.5 | 22.9 | 41.35 | 17.25 | 0.2204 |
| 2 | 20.05 | 36.65 | 15.39 | 0.2535 |

The headline metric is **monotone** across this sweep, so the conclusion keeps its direction over the range tested.
```

If the metric reverses direction inside the range, that sentence changes: the
range contains a turning point, and the direction of the effect is not a property
of the model. A flat sweep counts as monotone too — a parameter that does nothing
in the range tested is worth knowing about.

The provenance line and the warning are generated from the parameter's declared
grade, not written by hand, so sweeping a `literature`-graded parameter does not
produce the "no empirical support" banner.

## `sensitivity`

Ranks parameters by how much the headline metric moves when each is perturbed.
By default it covers every parameter with **no empirical support**, which is the
interesting set: a large number here means the model's output depends on a guess.

```bash
cs-sim sensitivity --scenario focused --baseline baseline --factor 0.5 \
  --metric time_to_50pct_repair_hours
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--scenario` | `focused` | Scenario to perturb. |
| `--baseline` | `baseline` | Scenario providing the reference metric. |
| `--factor` | 0.5 | Perturb by `×(1−factor)` and `×(1+factor)`. Must be strictly between 0 and 1. |
| `--metric` | `time_to_50pct_repair_hours` | Metric to rank by. Must be non-zero in the reference run. |

```console
$ cs-sim sensitivity
# One-factor sensitivity

Each parameter below was multiplied by 0.5 and by 1.5 and the run repeated against scenario `focused`. The table ranks parameters by the largest relative move they produced in the reference metric.

> Parameters with `assumed` or `invented` provenance are free knobs. A large number here does not mean the parameter matters in reality — it means the model's output depends on a guess.

| Parameter | Provenance | Default | Max relative change |
|---|---|---:|---:|
| `tissue.max_integrity` | assumed | 1 | -73.20% |
| `subconscious.base_repair_rate` | invented | 0.02 | +59.50% |
| `module.inflammation.repair_inhibition` | assumed | 0.5 | -34.61% |
| `mediator.neural_drive.decay_per_hour` | assumed | 0.9 | -31.52% |
...
```

(A shortened table; the command prints every unsupported parameter.)

Two details that affect how the numbers should be read:

- A parameter whose default is `0.0` cannot be moved by a multiplicative
  perturbation, so it is probed by nudging upward from zero instead.
- Each probe is clamped to the parameter's declared `minimum`/`maximum` rather
  than discarded. A parameter capped at 1.0 would otherwise be silently untestable
  in the upward direction, which is the direction that usually matters.

## `scenarios`

Lists the built-in scenarios, each with its summary and its caveat.

```console
$ cs-sim scenarios
Available scenarios:

  baseline               Subconscious repair alone. Attention is never engaged.
                         caveat: This is the reference condition. ...
  focused                Attention held as long as the budget allows, releasing only to recover.
                         caveat: The speed-up depends entirely on conscious.neural_drive_coupling, ...
  ...
```

The nine built-ins are `baseline`, `focused`, `intermittent`, `focused-uncoupled`,
`expectancy-on`, `inflammation-heavy`, `unmodulated`, `autonomic-coupled` and
`week-long`. Two are worth calling out: `focused-uncoupled` is the control in which
the central assumption is switched off, and `expectancy-on` is explicitly marked
**PURELY ILLUSTRATIVE** because both of its gains are invented and default to zero.

`--json` emits `[{name, summary, caveat, config}, ...]`.

## `parameters`

Lists parameters with their value, unit and provenance.

```console
$ cs-sim parameters
34 parameter(s); 33 of 34 lack empirical support.

key                                               value  unit               provenance
------------------------------------------------------------------------------------------------
conscious.attention_budget                            1  fraction           assumed
conscious.attention_drain_per_hour                 0.18  1/hour             assumed
...
```

`--unsupported` restricts the listing to parameters with no empirical support —
useful as a shortlist of everything that could be wrong. `--json` emits the full
`Parameter.as_dict()` per entry, including `supported`, `rationale`, `note`,
`minimum` and `maximum`.

```bash
cs-sim parameters --unsupported --json --out out/unsupported.json
```

## `modules`

Lists registered modules and the parameter keys each reads.

```console
$ cs-sim modules
Registered modules:

  autonomic        Maps an external HRV-style index onto modelled parasympathetic tone.
      module.autonomic.parasympathetic_gain
      module.autonomic.perfusion_gain
  circadian        Sinusoidal circadian factor, phase-locked to the virtual clock.
      module.circadian.amplitude
      module.circadian.period_hours
  expectancy       Expectancy-driven perception bias, with an opt-in physical channel.
...
```

Modules are listed in sorted order, which is also the order they are constructed
and stepped, so the listing is stable whatever order a scenario lists them in.

## `version`

```console
$ cs-sim version
conscious-subconscious 0.1.0

EDUCATIONAL AND ARTISTIC SIMULATION ONLY. This project is not a medical device. It does not diagnose, treat, cure or prevent any condition, and it provides no medical advice. The model encodes an UNVALIDATED assumption — that conscious attention can modulate a modelled tissue-repair rate. That assumption is not established clinical fact. Do not use any output of this project to make a decision about a human body.
```

`--json` emits `{"version": ..., "disclaimer": ...}`. The release workflow uses
this command as its smoke test: a wheel that installs but cannot print its version
is a broken artefact.

## Related commands

| Command | What it wraps |
| --- | --- |
| `make simulate` | `cs-sim compare` |
| `make demo` | `cs-sim run --scenario focused --report` |
| `make report` | `cs-sim run --scenario intermittent --report --out out/report.md` |
| `make verify` | lint, typecheck, tests, web tests, build, audit, locale check |

`cs-hardening` is declared in `pyproject.toml` as
`conscious_subconscious.hardening.cli:main` and is referenced by `make audit`,
but that subpackage does not exist in this repository yet, so the command will
fail with an import error until it lands.
