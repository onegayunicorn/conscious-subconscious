# Provenance

Every numeric constant in this project carries a grade saying where it came from.
The grades are the reason the project exists: a model whose parameters are all
labelled is one you can argue with, and a model whose parameters are not is one you
can only believe.

> **Boundary.** Grading a parameter is not a medical claim. This project is an
> educational and simulated artefact; see
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## The four grades

Declared in `src/conscious_subconscious/core/params.py` as the `Provenance` enum.
There are four, and there is no fifth "probably fine".

| Grade | Meaning | Support count for a conclusion? |
| --- | --- | --- |
| `measured` | Produced by a measurement inside this project. | Yes |
| `literature` | Supported by a cited source; see [`research/literature-review.md`](https://github.com/onegayunicorn/conscious-subconscious/blob/main/research/literature-review.md). | Yes |
| `assumed` | Chosen for convenience. No empirical support. A free knob. | No |
| `invented` | Taken from the source design document. No empirical support at all. | No |

"Supported" is exactly `measured` or `literature` — the `Provenance.is_supported`
property, which is what `cs-sim parameters --unsupported` filters on.

The distinction between `assumed` and `invented` is worth keeping:

- **`assumed`** means *someone exercising judgement picked this*. It is a guess,
  but it is a guess made deliberately while writing this repository.
- **`invented`** means *this number was already there in the source document and
  nothing backs it*. It is preserved rather than replaced, deliberately, so the
  reader can point at the exact values the project inherited.

Both are equally unsupported. Neither licenses a conclusion about a body.

## The current state of the parameter set

```
$ cs-sim parameters
34 parameter(s); 33 of 34 lack empirical support.
```

| Grade | Count |
| --- | ---: |
| `measured` | 0 |
| `literature` | 1 |
| `assumed` | 26 |
| `invented` | 7 |

The single supported parameter is `module.circadian.period_hours` (24 h), and it
is supported only for the *existence and approximate period* of a human circadian
rhythm. The *depth* of circadian modulation used by the model
(`module.circadian.amplitude`) is `assumed`.

The full table, with each parameter mapped to the symbol it plays in the
equations, is in [model-spec.md](model-spec.md#6-which-parameters-have-empirical-support).

## Why overriding a parameter downgrades it

`ParameterSet.with_overrides` — reached by `cs-sim --set`, by a scenario's
`overrides` map, and by the API's session configuration — replaces the value **and
sets its grade to `assumed`**, attaching a note that names the previous value:

```
runtime override (was 0.75 dimensionless, provenance invented);
overridden values are always treated as unsupported
```

The reasoning is short. A value chosen at runtime is not traceable to whatever
backed the default. If the default was `literature` because a paper supports it,
that paper supports the *published* number, not the number you typed. Keeping the
original, flattering tag would be precisely the dishonesty this module exists to
prevent — a run configured at the command line would inherit the credibility of a
source it no longer uses.

Two practical consequences:

- `cs-sim parameters --unsupported` lists the grades of the **defaults**. A run
  that overrides a supported default has, in effect, one more unsupported
  parameter than that listing suggests. The run's own `provenance` list shows the
  truth for that run.
- A conclusion that only holds when a value is passed with `--set` rests on an
  `assumed` parameter, whatever the default's grade was. That is usually
  fine — experiments are supposed to override things — but it should be said
  out loud.

## How to read a report

`cs-sim run --scenario focused --report` produces Markdown in this shape:

```
# Simulation report — focused

> **Boundary.** This project is an educational and artistic simulation. ...

- **Scenario:** `focused`
- **Seed:** 20260921
- **Time step:** 0.05 h over 72.0 h
- **Tissue model:** muscle tissue, initial integrity 0.2
- **Modules:** circadian, inflammation, perfusion
- **Focus policy:** `always`

## Provenance of the numbers

33 of 34 parameters carry no empirical support (97%). Results that depend on them
describe the model, not a body.

| Parameter | Value | Unit | Provenance |
|---|---:|---|---|
| `conscious.neural_drive_coupling` | 0.75 | dimensionless | invented |
| `conscious.neural_drive_gain` | 1 | field-units/hour | invented |
| `subconscious.base_repair_rate` | 0.02 | integrity/hour | invented |
| `module.inflammation.repair_inhibition` | 0.5 | dimensionless | assumed |
| `module.circadian.period_hours` | 24 | hour | literature |

_Every parameter is tagged measured | literature | assumed | invented. ..._

## Headline result

| Metric | Value |
|---|---:|
| Time to 50% repair | 27.6 h |
| Time to full repair | 50.4 h |
| Area under damage | 21.0902 integrity·h |
| Mean integrity | 0.5184 |
| Final integrity | 1 |
| Attention engaged | 29.45 h |
| Attention spent | 5.3 budget units |
| Repair attributable to attention | 0.1447 |
| Fatigue episodes | 10 |

## What this does not show

- It does not show that attention, visualisation or willpower changes the rate of
  tissue repair in a human body.
- It does not predict healing times for any real injury. No clinical endpoint,
  population or measurement is modelled.
- It does not estimate the size of any real effect. Every constant that carries
  the effect is tagged `invented` or `assumed`.

## Reproduce this run

cs-sim run --scenario focused --seed 20260921 --dt 0.05 --horizon 72.0 --modules circadian,inflammation,perfusion

Digests — parameters <16 hex chars>, config <16 hex chars>, run <16 hex chars>. A
matching run digest means byte-identical results.
```

Reading it in order:

1. **The boundary note comes first**, before any number.
2. **The provenance paragraph and table come before the results.** A number never
   appears without its provenance nearby; the summary sits above the headline
   table, not in an appendix.
3. **The "what this does not show" section is part of every report**, not optional
   boilerplate.
4. **The reproduction command is exact**, so the reader can check you.
5. **Missing values are an em dash.** "Never reached 50% repair in 72 hours" and
   "reached it in zero hours" are opposite statements and must not render
   identically, so `sim/report.py` never prints a missing value as `0`.
6. **The digests at the bottom** cover the parameters, the config and the
   completed run. If two runs report the same run digest, they are byte-identical.

`cs-sim compare` adds one honesty line of its own: a negative percentage means the
model repaired faster, and that is a property of the coupling constant, not
evidence about people.

## How a report can be wrong

Not cynically — concretely, so the failure modes are visible:

- **A caveat may have been edited out.** Scenarios carry a `caveat` string, and the
  report injects it above the "what this does not show" section. If you fork a
  scenario and drop the caveat, the number survives and the warning does not.
- **A sweep can be monotone inside a range and reverse outside it.**
  `render_sweep_markdown` says whether the headline metric is monotone *across the
  range tested*, and says nothing about outside it.
- **A sensitivity ranking measures model dependence, not real importance.** A large
  relative change means the output depends on a guess. It does not mean the
  parameter matters in reality.
- **A digest mismatch means a bug, not a finding.** Two runs with identical
  parameters and config cannot legitimately differ; if they do, something upstream
  is non-deterministic.
