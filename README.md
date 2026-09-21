# conscious-subconscious

A reproducible simulation sandbox for modelling an autonomous *subconscious*
repair process and a deliberate *conscious* attentional process acting on the
same damaged tissue model.

> **Boundary — read this before anything else.**
> This is an educational and artistic simulation. It is **not a medical device**,
> it does not diagnose, treat, cure or prevent anything, and it provides no
> medical advice. The model encodes an **unvalidated assumption**: that conscious
> attention can modulate a modelled tissue-repair rate. That assumption is not
> established clinical fact. Do not use any output of this project to make a
> decision about a human body. See [`DISCLAIMER.md`](DISCLAIMER.md).

[![CI](https://github.com/onegayunicorn/conscious-subconscious/actions/workflows/ci.yml/badge.svg)](https://github.com/onegayunicorn/conscious-subconscious/actions/workflows/ci.yml)

---

## What this is

A small, deterministic Python engine that models a damaged region as a scalar
`integrity`, a set of signalling channels between a "subconscious" homeostatic
process and a "conscious" attentional process, and a repair rule that is the
**only** code path allowed to change that scalar.

What makes it worth looking at is not the model — the model is a caricature of a
caricature. It is what the project does with the numbers:

- **Every constant carries a provenance tag.** Of 34 parameters, **33 are
  `assumed` or `invented`** and exactly one is `literature`. The reports say so
  above the results table, not in an appendix.
- **There is a control scenario that switches the central claim off.** Set
  `conscious.neural_drive_coupling` to `0.0` and attention becomes inert. A test
  asserts this: the repair metrics must be *identical* to the no-attention
  baseline. If that test fails, attention is leaking into repair through a path
  nobody documented.
- **A sensitivity analysis ranks the guesses.** `cs-sim sensitivity` perturbs
  every unsupported parameter and ranks them by how far the headline metric
  moves. The top of that list is a list of things nobody has measured.
- **The source material is graded, not laundered.** The design conversation this
  project grew out of claimed, among other things, a `1.0–3.0` random "conscious
  boost". `research/evidence-grading.md` grades that claim — and every other
  numeric claim in the source — as grade D.

## What this is not

- Not a medical device, a clinical tool, or evidence of anything about bodies.
- Not a brain model. There are no neurons, no networks and no learning rule.
- Not calibrated. Nothing here was fitted to data, because there was no data to
  fit it to.
- Not a claim that visualisation, willpower or attention changes the rate at
  which a real wound heals. The model makes the assumption explicit so you can
  explore its consequences, and labels it as an assumption every time it prints.

## Quickstart

The core has **no third-party runtime dependencies**.

```bash
git clone https://github.com/onegayunicorn/conscious-subconscious.git
cd conscious-subconscious
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[api,dev]"

cs-sim compare                 # baseline vs focused vs intermittent
cs-sim run --scenario focused --report
cs-sim parameters --unsupported
cs-sim sensitivity
cs-sim sweep --param conscious.neural_drive_coupling --values 0:3:0.75
```

Typical output from `cs-sim compare` (seed `20260921`, `dt = 0.05 h`, 72 h):

| Metric | `baseline` | `focused` | `intermittent` | `focused-uncoupled` |
|---|---:|---:|---:|---:|
| Time to 50% repair (h) | 33.95 | 27.6 | 27.6 | 33.95 |
| Area under damage | 26.69 | 21.09 | 21.28 | 26.69 |
| Attention engaged (h) | 0 | 29.45 | 23.85 | 36.8 |
| Repair attributable to attention | 0 | 0.145 | 0.119 | 0 |

The last column is the point. With the coupling constant set to zero, held
attention changes **nothing** about repair — and the run still spends its
attention budget. The speed-up in the middle columns is a property of one
invented number.

## The model in one page

Repair rate for one step:

$$
R_{\text{base}} = k_{\text{repair}} \; S(G) \; (1 - \rho I) \; C(t),
\qquad
S(G) = \frac{G}{G + K_{gf}},
\qquad
R_{\text{total}} = R_{\text{base}} \,(1 + \lambda N)
$$

| Symbol | Parameter | Provenance |
|---|---|---|
| $k_{\text{repair}}$ | `subconscious.base_repair_rate` | `invented` |
| $K_{gf}$ | `subconscious.gf_half_saturation` | `assumed` |
| $\rho$ | `module.inflammation.repair_inhibition` | `assumed` |
| $I$ | inflammation level (module signal) | derived |
| $C(t)$ | circadian factor (module signal, defaults to 1.0) | `assumed` (period is `literature`) |
| $N$ | modelled `neural_drive` produced by attention | derived |
| $\lambda$ | `conscious.neural_drive_coupling` | **`invented` — the whole claim** |

Attention is a finite budget: focusing spends it, resting restores it, and there
is hysteresis so a fatigued mind does not flap against the threshold. Perceived
progress is tracked **separately** from actual integrity, because the source
document conflated the two and that conflation is exactly how a toy simulation
starts to look like evidence.

Full derivation, units and every symbol mapped to a parameter:
[`docs/model-spec.md`](docs/model-spec.md).

## Where the numbers came from

The project began as a user-supplied design conversation containing several toy
simulations — Python, Java and JavaScript — that subtracted a constant from a
`damage_level` each tick and added a random "conscious boost". `research/` grades
that material claim by claim:

- `research/evidence-grading.md` — an A–D rubric, applied. Every numeric claim in
  the source is graded **D (invented)**.
- `research/literature-review.md` — what is actually known in adjacent areas:
  placebo and open-label placebo effects, expectancy, psychoneuroimmunology,
  stress and wound healing, interoception, HRV biofeedback. 28 verified
  references, each with a DOI or PMID.
- `research/experimental-design.md` — what a study capable of testing the
  assumption would need, and why this sandbox cannot be that study.

The literature supports effects on *subjective* outcomes and on *stress*
physiology. It does not establish that attention changes tissue-repair rate. The
model's job is to keep that distinction visible.

## Repository map

| Path | Contents |
|---|---|
| `src/conscious_subconscious/core/` | Parameters with provenance, deterministic RNG, virtual clock, event bus. Zero dependencies. |
| `src/conscious_subconscious/model/` | Tissue, mediator field, subconscious and conscious systems, metrics, engine. |
| `src/conscious_subconscious/modules/` | Opt-in physiology-ish modules: inflammation, perfusion, circadian, autonomic, expectancy. |
| `src/conscious_subconscious/devices/` | Hardware adapters: simulated, serial, LSL, BLE heart rate, replay. All read-only. |
| `src/conscious_subconscious/protocols/` | Envelope, JSON-RPC control, MQTT topics, NDJSON framing, in-process transport. |
| `src/conscious_subconscious/services/` | Session manager, API-key auth, rate limiting, redaction, Prometheus metrics, FastAPI app. |
| `src/conscious_subconscious/pipelines/` | DAG runner and signal-processing steps for recorded telemetry. |
| `src/conscious_subconscious/sim/` | Scenarios, sweeps, sensitivity analysis, reports, CLI. |
| `src/conscious_subconscious/hardening/` | A short self-audit, applied to this repository in CI. |
| `hardware/` | ESP32 reference firmware, wiring notes, BOM. |
| `protocols/schemas/` | JSON Schema — the contract the TypeScript console also implements. |
| `pipelines/` | Declarative data-pipeline DAGs. |
| `apps/console/` | React + TypeScript console. |
| `apps/site/` | Marketing and documentation site. |
| `deploy/` | Docker, Kubernetes, systemd, platform matrix. |
| `security/` | Threat model, hardening checklist, incident response, dependency policy. |
| `research/`, `marketing/`, `media/`, `i18n/` | Evidence, positioning, brand assets, locales. |
| `tools/` | Preflight, SBOM generation, platform builds, locale parity, golden-file update. |

## Determinism

Every run is driven by a seeded generator with **named substreams**, so adding a
module cannot perturb an unrelated component's draws, and a virtual clock with
no wall-clock reads. Runs emit a `run_digest`; equal digests mean byte-identical
results.

```bash
cs-sim run --scenario intermittent --json | python3 -c "import json,sys; print(json.load(sys.stdin)['digests']['run'])"
```

Irreproducibility in the source material came from `random.uniform(1.0, 3.0)`
drawn every tick. Here that variability is a parameter
(`conscious.neural_drive_jitter`) that defaults to **zero**, and when you raise
it, it draws from its own named stream.

`tests/golden/golden_runs.json` pins the numbers for the shipped scenarios. Any
diff there means the model's numerical behaviour moved.

## Interfaces

**CLI** — `run`, `compare`, `sweep`, `sensitivity`, `scenarios`, `parameters`,
`modules`, `version`. See [`docs/cli.md`](docs/cli.md).

**HTTP API** — session lifecycle, stepping, streaming over WebSocket, Prometheus
metrics. Authentication is required off loopback; `assert_safe_bind` refuses to
start an unauthenticated service on a public interface. See
[`docs/api.md`](docs/api.md).

**Protocol** — one envelope for every message, versioned, with unknown fields
rejected rather than ignored. Control is JSON-RPC; samples are fire-and-forget;
telemetry moves over NDJSON or MQTT. See [`docs/protocol.md`](docs/protocol.md).

**Hardware** — read-only adapters only. There is no stimulation path, and the
threat model treats that as a boundary worth protecting. See
[`hardware/README.md`](hardware/README.md).

## Testing

```bash
make test          # 551 tests
make typecheck     # mypy, strict on the dependency-free core
make lint          # ruff
make audit         # this repository's own hardening rules, applied to itself
make verify        # everything CI runs
```

The suite covers the invariants that matter: integrity never decreases,
attention stays inside its budget, the same configuration always gives the same
answer, the uncoupled control equals the baseline, and a truncated protocol
frame is refused rather than guessed at. Coverage is 89%.

## Deployment

Local, Docker, Kubernetes and systemd paths, plus an honest note on what has not
been verified (no load testing has been done): [`docs/deployment.md`](docs/deployment.md)
and [`deploy/`](deploy/).

## Contributing

Read [`CONTRIBUTING.md`](CONTRIBUTING.md). Two rules matter more than the rest:

1. **A new number needs a provenance tag.** If you cannot say where a constant
   came from, tag it `assumed` and say so in the report.
2. **No new medical claims.** Ever. Including in a comment, a docstring, an
   example or a chart label.

## Licence and disclaimer

MIT — see [`LICENSE`](LICENSE).

Read [`DISCLAIMER.md`](DISCLAIMER.md). It is short, and it is the most important
file in the repository.
