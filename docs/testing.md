# Testing

Two things are being protected here: that the code does what it says, and that
**the same configuration always produces the same numbers**. The second is the
project's central engineering claim, so it is enforced by CI rather than asserted
in a README.

> **Boundary.** A passing test suite says the simulation is self-consistent. It says
> nothing about biology. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Running the tests

```bash
make test            # .venv/bin/python -m pytest
make test-golden     # only the golden reference-run comparisons
make coverage        # pytest with a term-missing coverage report
make verify          # lint + typecheck + tests + web tests + build + audit + locales
```

Without a virtualenv:

```bash
PYTHONPATH=src python3 -m pytest
```

Pytest is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q --strict-markers"
markers = [
    "golden: compares engine output against a committed reference run",
    "slow: takes more than a couple of seconds",
]
filterwarnings = ["error::DeprecationWarning:conscious_subconscious.*"]
```

Two of those settings do real work:

- `--strict-markers` means an unregistered marker is an error, so a typo in
  `@pytest.mark.slwo` fails instead of silently running.
- `filterwarnings = ["error::DeprecationWarning:conscious_subconscious.*"]`
  promotes deprecation warnings **raised by this package** into errors. A
  dependency's deprecation warning does not fail the suite; the project's own does.
  That is what keeps the code from accumulating warnings that nobody reads.

Coverage is measured with branch coverage over the package
(`[tool.coverage.run] source = ["conscious_subconscious"]`, `branch = true`). No
coverage **threshold** is enforced. That is deliberate: a threshold invites tests
written to move a number, and this project would rather have a small honest suite
than a padded one. Coverage is reported on the 3.12 job and uploaded as an
artefact.

## Test layout

`tests/` does not exist in this repository yet. When it lands, the intended
split — and the reason for each part — is:

| Path | Covers |
| --- | --- |
| `tests/core/` | `VirtualClock`, `DeterministicRng`, `EventBus`, `ParameterSet` |
| `tests/model/` | Engine step order, tissue, mediator field, conscious, subconscious, metrics |
| `tests/modules/` | Each module in isolation, including the registry's dedupe-and-sort contract |
| `tests/protocols/` | Envelope validation, NDJSON framing, JSON-RPC, topic identifiers |
| `tests/devices/` | The pure parsing functions, plus `DeviceUnavailable` behaviour |
| `tests/sim/` | Scenarios, `--set` parsing, sweep ranges, report rendering |
| `tests/conformance/` | The Python implementation against `protocols/schemas/*.json` |
| `tests/golden/` | The committed reference runs (marked `golden`) |

## Golden tests and the determinism contract

### What the contract says

1. **The same `RunConfig` and the same `ParameterSet` produce the same result,
   byte for byte.** `RunConfig` is frozen metadata; `SimulationResult` carries three
   digests (`parameter_digest`, `config_digest`, `run_digest`) so a claim of
   reproducibility is checkable.
2. **Randomness is named, not global.** `DeterministicRng` derives one independent
   substream per consumer from the root seed with SHA-256. Adding a module cannot
   perturb a previously reproduced run, because unrelated code does not share a
   stream. `hash()` is avoided precisely because it is salted per process.
3. **The virtual clock never reads the wall clock.** `t_hours` is recomputed as
   `steps × dt` on every tick rather than accumulated, which removes floating-point
   drift over long runs.
4. **The only source of non-determinism is `conscious.neural_drive_jitter`**, the
   width of the uniform jitter added to the neural-drive gain. It is `0.0` by
   default, so a default run draws no random numbers at all.
5. **The control is clean in the repair path.** The scenario `focused-uncoupled`
   sets `conscious.neural_drive_coupling` to `0.0`, so attention is held but has no
   route into repair. Every **repair** metric must then be identical to `baseline`:
   `final_integrity`, `time_to_50pct_repair_hours`, `time_to_full_repair_hours`,
   `area_under_damage_integrity_hours`, `mean_integrity`, `total_repair`,
   `attention_attributable_repair`, `attention_attributable_fraction` and
   `peak_growth_factor`. If any of those differs, something in the attention path
   is leaking into repair — a bug, not a finding.

   The comparison is deliberately restricted to those keys. Attention *accounting*
   legitimately differs: `focus_hours`, `attention_spent`, `min_attention`,
   `fatigue_episodes` and `peak_neural_drive` all differ between `baseline` and the
   control, because the control really does hold attention — it just cannot act on
   the tissue. Asserting that the whole metrics mapping is equal would fail on those
   five keys, and asserting nothing would miss the leak this check exists to catch.

### What golden tests protect

A golden test runs a scenario with fixed parameters and compares the result against
a **committed reference run**. Two things follow:

- It catches unintended behaviour changes. Anything that alters the numbers — a
  changed default, a reordered step, an altered equation — fails the golden test,
  even if every unit test still passes. Unit tests check that a function does what
  its author expected; a golden test checks that the *result* did not move.
- It makes an intentional change an explicit act. To change the model you have to
  regenerate the reference and say so in the pull request. That is the point: the
  diff of a reference run is a machine-readable statement of what the change did.

What golden tests do **not** protect: they cannot fail because the model is wrong,
only because it changed. A wrong model with a stable reference is perfectly green.
That is why every report carries the provenance of the parameters, and why
`docs/model-spec.md` exists.

### The CI jobs that enforce this

`.github/workflows/ci.yml`:

- **`determinism`** runs `cs-sim compare --out out/compare-a.md` and again into
  `compare-b.md`, then `diff -u` them. It repeats the run in JSON and asserts the
  `run_digest` lists are equal. It then runs `baseline` and `focused-uncoupled`
  and asserts their metrics dictionaries are identical.
- **`python`** runs ruff, `ruff format --check`, `mypy` (strict) and pytest with
  coverage across the interpreter matrix, so a Python-version-dependent numerical
  difference is caught rather than assumed away.

Both jobs run with `fail-fast: false`: a platform-specific failure must not hide
the others.

## Working with golden tests

Regenerating a reference run is a deliberate, reviewable act:

1. Run the failing golden test and read the diff. Do not regenerate until you can
   explain every changed number.
2. If the change is intended, regenerate the reference **in the same commit** as the
   model change, and explain in the pull request which parameters or equations
   changed. The
   [model change template](https://github.com/onegayunicorn/conscious-subconscious/blob/main/.github/ISSUE_TEMPLATE/model_change.yml)
   lists what is expected.
3. If the change is a `--set` override, note that the affected parameter's
   provenance becomes `assumed` (see [provenance.md](provenance.md)) — a golden
   reference generated from an override is a reference in which that parameter has
   no support.

Never regenerate a golden reference to make CI green without reading the diff.
That turns the strongest test in the suite into a rubber stamp.

## What is not tested

- **No test has any hardware behind it.** CI has no serial port, no radio and no
  LSL network. The pure parsing functions (`parse_line`,
  `parse_heart_rate_measurement`, `rmssd_ms`, `hrv_index_from_rmssd`) are testable
  without hardware and are the intended coverage; the I/O paths are not covered.
- **No property-based or fuzz testing is present.** Input fuzzing would be
  valuable for `Envelope.from_json`, `NdjsonDecoder` and the topic parser, all of
  which accept untrusted input. It is not implemented.
- **No performance benchmarks exist.** No throughput, latency or memory
  measurements have been taken, and no regression-gate on runtime exists.
- **No end-to-end test of a deployed service exists**, because the service does not
  exist.
- **No mutation testing.** Line coverage is not evidence that an assertion would
  notice a change.
- **The accessibility and visual behaviour of the web workspaces are untested**,
  and those workspaces are not present in this repository yet.
