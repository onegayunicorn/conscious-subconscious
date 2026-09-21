# Contributing

Thanks for considering it. This project is small and its bar is specific: the code
has to work, and the claims have to stay honest. The second requirement is the one
that gets pull requests rejected, so read the two rules below before anything else.

> **Boundary.** This is an educational and artistic simulation, not a medical
> device. See [DISCLAIMER.md](DISCLAIMER.md), which is the canonical version.

## Two rules that are not negotiable

### 1. The provenance rule for new parameters

Every numeric constant in the model is declared **once**, in
`src/conscious_subconscious/parameters.py`, with:

- a dotted `key`
- a `value`
- a `unit` — including `dimensionless` when it is one
- a `provenance` grade: `measured`, `literature`, `assumed` or `invented`
- `minimum` and `maximum` bounds
- a `note` explaining where the number came from

**Nothing else in the codebase may hold a bare magic number.** If your change needs
a constant, it goes in that file and is read through `ParameterSet.value(key)`.

Grading rules:

- `measured` means **produced by a measurement inside this repository**. There are
  currently zero of these. Do not add one unless you actually took the measurement
  and can describe the procedure.
- `literature` requires a **cited source** in `research/` that supports *this value*,
  not merely the existence of the phenomenon. `module.circadian.period_hours` is the
  only current example, and its note says exactly what the source supports.
- `assumed` means you chose it for convenience. That is a fine answer.
- `invented` means it came from the source design document. Do not label a new
  number `invented` unless it is genuinely inherited.

**Do not upgrade a grade without evidence.** That includes moving something from
`assumed` to `literature` because a plausible paper exists. A model whose parameters
are all labelled is one people can argue with; a model whose labels are optimistic is
worse than one with no labels at all.

Remember that `ParameterSet.with_overrides` **downgrades any overridden parameter to
`assumed`** automatically, with a note naming the previous value. That is intended,
and it means a value chosen at runtime can never inherit the credibility of a
default it replaced.

If your change alters an equation, a parameter, a module or the step order in
`model/engine.py`, [open a model change issue](.github/ISSUE_TEMPLATE/model_change.yml)
first — the template asks for the provenance information up front.

### 2. No medical claims

Nothing merged into this repository may imply that:

- attention, focus, visualisation, willpower or expectancy affects real tissue
  repair, healing rate or any clinical outcome;
- the project is, or is becoming, a medical device, a therapy, a treatment, a
  diagnostic or a clinical decision aid;
- the model is validated, calibrated, or produces clinical evidence;
- the numbers constitute a prediction, a prognosis or medical advice.

This applies to code, comments, docstrings, documentation, examples, test names,
commit messages, issue templates and asset descriptions. It applies to metaphors
and to jokes. The honesty of the framing *is* the project.

If you are unsure whether a sentence crosses the line, read
[`research/evidence-grading.md`](research/evidence-grading.md) and
[`research/literature-review.md`](research/literature-review.md). The project's own
assumption is graded **D**; anything you write should be consistent with that.

Two further constraints that follow from the same reasoning:

- **No payments.** Pricing, tiers, checkout, subscriptions, sponsored placements and
  payment integrations are not implemented and are not planned. Do not add them, and
  do not describe them as existing.
- **Hardware stays read-only.** No adapter may gain a write, send, stimulate or
  actuate method. That boundary is a safety property, not a backlog item.

## Development setup

Requires Python 3.10–3.13. The core has **no third-party runtime dependencies**.

```bash
git clone https://github.com/onegayunicorn/conscious-subconscious
cd conscious-subconscious

make install-dev          # .venv with core + api + dev extras
make install-devices      # optional: pyserial, pylsl, bleak
make install-science      # optional: numpy, matplotlib

pre-commit install        # optional but recommended: same hooks CI runs
```

Without a virtualenv, the CLI runs straight from a checkout:

```bash
PYTHONPATH=src python3 -m conscious_subconscious.sim.cli compare
```

## Make targets

`make` with no arguments prints the annotated list. The ones you will use:

| Target | What it does |
| --- | --- |
| `make help` | List every target (the default goal). |
| `make venv` | Create `.venv` and upgrade pip. |
| `make install` | Install the core package, no extras. |
| `make install-dev` | Install core + `api` + `dev` extras. |
| `make install-devices` / `make install-science` | Optional extras. |
| `make lint` | `ruff check src tests tools`. |
| `make fmt` | `ruff check --fix` then `ruff format`. |
| `make typecheck` | `mypy` in strict mode. |
| `make test` | `pytest`. |
| `make test-golden` | Only the golden reference-run tests (`-m golden`). |
| `make coverage` | `pytest --cov --cov-report=term-missing`. |
| `make simulate` | `cs-sim compare`. |
| `make demo` | `cs-sim run --scenario focused --report`. |
| `make report` | Write a Markdown report to `out/report.md`. |
| `make audit` | The hardening self-audit. |
| `make sbom` | Generate a CycloneDX-style SBOM. |
| `make locales-sync` | Validate locale key parity. |
| `make build` | Build sdist + wheel into `dist/`. |
| `make verify` | **Everything CI runs locally.** Run this before opening a pull request. |
| `make docker` / `make docker-compose-up` | Container build and local stack. |
| `make k8s-validate` | Dry-run the Kubernetes manifests. |
| `make preflight` | Show tool availability on this machine. |
| `make clean` | Remove build and cache artefacts. |

**`make verify` is the one that matters.** It runs lint, typecheck, tests, web
tests, web build, audit and locale parity — the same set CI runs.

Some targets currently cannot succeed, because the files they call do not exist in
the tree yet: `make audit` (`hardening/cli.py`), `make sbom`, `make locales-sync`,
`make preflight` and `make build-all` (the `tools/` scripts), plus `make test`
until `tests/` exists. Fixing those is welcome work; if you do, keep the target
names.

## Tests

- Add tests for new behaviour. A pull request that changes the model without a test
  will be asked for one.
- **Golden tests are the strongest tests in the suite.** They compare a run against
  a committed reference. If yours fails, read the diff and explain every changed
  number before regenerating — never regenerate to make CI green.
- Mark a slow test `@pytest.mark.slow`; markers are strict, so an unregistered
  marker is an error.
- Deprecation warnings **raised by this package** are errors
  (`filterwarnings` in `pyproject.toml`). Warnings from dependencies are not.
- CI covers Linux (3.10–3.13), macOS (3.11, 3.13) and Windows (3.11, 3.13). New
  tests must pass on all of them; do not assume a POSIX path, a shell or a
  filesystem case rule.

## Code style

- **Formatter and linter:** ruff, line length 100, target `py310`. Selected rules
  include `E`, `F`, `W`, `I`, `UP`, `B`, `C4`, `SIM`, `PTH`, `RET`, `ARG`. `B008` is
  ignored deliberately (FastAPI-style default arguments).
- **Types:** mypy runs in **strict** mode over the package. `from __future__ import
  annotations` at the top of new modules. The optional-integration modules listed in
  `[tool.mypy.overrides]` are relaxed because their dependencies may be absent; do
  not add to that list without a reason.
- **Public API additions** need a docstring, an entry in `__all__`, and a mention in
  the relevant `docs/` page.
- **Comments explain why, not what.** The existing code says things like *"Refusing
  is the honest behaviour. Silently dropping samples is how a monitoring system ends
  up reporting a healthy average over an unhealthy window."* Match that register:
  state the reason a decision was made, especially when the alternative was
  tempting.
- **No new core dependency.** The core stays dependency-free; a new dependency goes
  in an optional extra, imported inside the module that needs it. See
  `security/dependency-policy.md`.
- **Errors** derive from `ConsciousSubconsciousError` and use the existing
  hierarchy. "Not available here" is `DeviceUnavailable`, not `DeviceError`.

## Documentation

- **If the model changed, `docs/model-spec.md` changes in the same commit** —
  equations, the symbol-to-parameter-key table and the provenance table.
- If a deployment path changed, update `deploy/README.md` and
  `docs/deployment.md`.
- If you add a CLI flag, update `docs/cli.md` with a real example.
- **Say when something is not implemented or not verified.** The existing docs do
  this explicitly and it is a feature. "Not tested" is a useful sentence; a
  confident description of an untested thing is not.
- Do not invent benchmarks, user counts, latency figures or roadmap dates.

## Commit style

Conventional Commits, loosely enforced by review rather than tooling:

```text
<type>(<scope>): <subject>

<body: what changed and why>

<footer: references>
```

Types used here: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `ci`,
`chore`, `deps`.

Scopes that match the layout: `core`, `model`, `modules`, `protocols`, `devices`,
`sim`, `api`, `cli`, `i18n`, `params`, `deploy`, `k8s`, `docker`, `systemd`, `docs`,
`security`, `ci`, `console`, `site`, `tools`.

- Subject in the imperative mood, lower case, no trailing period, ideally under 72
  characters.
- One logical change per commit. A model change and its `docs/model-spec.md` update
  belong together; a formatting sweep does not belong with either.
- Reference the issue in the footer (`Refs: #12`).
- Dependabot uses `deps(python)`, `deps(console)`, `deps(site)`, `deps(docker)` and
  `deps(actions)`.

Examples:

```text
feat(model): add a scar-formation term behind an invented parameter

The tissue abstraction had no post-repair state, so a healed run and a
partially healed one were indistinguishable afterwards. Adds
`tissue.scar_fraction` as `invented`, defaulting to 0.0 so existing runs are
unchanged and golden fixtures do not move.

Refs: #31
```

```text
fix(protocols): reject device ids containing a topic wildcard

validate_identifier already rejected '+', but only on session ids. A device id
of 'a/+/b' could therefore publish outside its namespace.

Refs: #44
```

## Pull requests

1. Run `make verify` and fix what it reports.
2. Fill in the pull request template, **including the provenance / honesty
   checklist**. That section is not decorative; it is how the two rules above are
   enforced at review time.
3. Keep the change focused. Unrelated cleanups belong in their own pull request.
4. Explain any golden-file change: what moved, in which direction, and why.
5. Be explicit about what you did **not** do. "I did not add a test for the
   hardware path because CI has no hardware" is a useful sentence.
6. Expect questions about claims and provenance. They are not hostility; they are
   the review.

Review will ask for a change if a claim outruns the evidence, if a parameter lacks a
grade, if a document describes an unimplemented thing as working, or if anything
reads like it is edging towards a medical use.

## Reporting problems

- Bugs and documentation errors: the issue templates (the bug template has an area
  for exactly this).
- Security issues: **do not open a public issue.** See [SECURITY.md](SECURITY.md).
- Model changes: the model change template, which asks for the parameters affected
  and their provenance.
- Feature requests that require a medical, clinical or stimulation capability will
  be closed. That is not a judgement on the idea; it is the boundary of the project.

## Licence

Contributions are accepted under the MIT licence in [LICENSE](LICENSE). By opening a
pull request you confirm you have the right to submit the work under those terms.
