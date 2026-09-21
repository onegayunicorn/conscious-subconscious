# Dependency policy

The rules this project uses to decide what it may depend on, how it pins it, how
often it moves, and how it proves what shipped. The short version: **the core has
no runtime dependencies at all, and everything else is opt-in.**

> **Boundary.** A dependency policy keeps a simulation honest about its supply
> chain. It does not change what the project is: educational and artistic
> simulation only. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## 1. The core stays dependency-free

`pyproject.toml` declares:

```toml
dependencies = []
```

This is not minimalism for its own sake. Four reasons, in order:

1. **The engine must run anywhere.** A locked-down or offline interpreter, a
   classroom machine, a CI runner with no package index — all of them can run the
   simulation today. `core/`, `model/`, `modules/`, `protocols/` and `sim/` import
   nothing beyond the standard library.
2. **Reproducibility is easier to defend with no dependency graph.** A run digest
   means the same thing when the interpreter is the only variable. A floating
   dependency can change numerical results between installs.
3. **The attack surface stays small.** Optional drivers (`pyserial`, `pylsl`,
   `bleak`) bind native code and have commit rights held by few people. Isolating
   them keeps the largest part of the attack surface out of the engine.
4. **It keeps the project's claims simple.** A package with no dependencies cannot
   launder credibility from a well-known library it does not use.

**Practical consequences that are enforced in code, not just stated:**

- Optional imports live **inside** the driver that needs them, so
  `import conscious_subconscious.devices` succeeds on a machine with no extras.
- A missing optional dependency raises `DeviceUnavailable`, which is deliberately
  distinct from `DeviceError`: "this machine cannot do that" and "the device
  misbehaved" need different responses.
- mypy is configured with `ignore_missing_imports` and relaxed typing **only** for
  the modules whose imports are optional (`[tool.mypy.overrides]`), so strict mode
  still applies to everything else.
- The build backend is `setuptools` with no runtime plugins; the only build
  requirements are `setuptools>=68` and `wheel`.

**If you are proposing a new core dependency:** it will be declined unless the
project literally cannot function without it, and the argument has to explain why
the standard library is insufficient. A dependency that only makes code shorter is
not a reason.

## 2. Optional extras are isolated

| Extra | Packages | What it enables | Isolation requirement |
| --- | --- | --- | --- |
| `api` | `fastapi`, `uvicorn[standard]`, `pydantic` | The (planned) HTTP service | Imported only inside `conscious_subconscious.services.*`. The service layer does not exist yet. |
| `devices` | `pyserial`, `pylsl`, `bleak` | Hardware adapters | Imported only inside the individual driver files. |
| `science` | `numpy`, `matplotlib` | Numerical and plotting extras | Not used by the engine. The engine is hand-written precisely so it can run without a numerical stack. |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `mypy`, `build`, `jsonschema` | Lint, typecheck, test, build | Development only; never installed by a user of the library. |
| `all` | everything above except `dev` | Convenience | Same isolation applies; `all` is a union, not a licence to import across boundaries. |

**The rule for a new extra:** each extra must be independently installable,
independently testable, and independently auditable. That is enforced by
`security.yml`, which audits `api`, `devices` and `science` **separately**, so a
finding is attributable to the extra that pulled it in rather than to "the
dependencies".

**Isolation rules:**

- Optional imports belong in the module that needs them, not in `__init__.py`.
- An extra must never become a transitive requirement of another extra. `all`
  exists as an explicit union so that nothing else has to depend on the union.
- A feature that needs an optional package must degrade with a typed error, not
  with an `ImportError` traceback.
- Every extra's absence must be treated as normal. `devices/registry.py` registers
  drivers without importing their third-party packages, so a machine with none of
  them still lists all five adapters.

## 3. Version pinning

| Artefact | Strategy | Rationale |
| --- | --- | --- |
| Optional dependencies | **Lower bounds only** (`>=`) | This is a library-shaped package. An upper bound in a library makes it unresolvable inside a larger application for no benefit. |
| `requires-python` | `>=3.10`, tested to 3.13 | The lower bound is a language-feature requirement (PEP 604 unions, dataclass slots). The upper end is a test-matrix statement, not a prohibition. |
| Base container image | **Minor-pinned** (`python:3.12-slim`), not digest-pinned | Patch updates are picked up on rebuild; the behaviour of the interpreter is fixed across rebuilds. Operators deploying to production should pin by digest — that is a deployment decision, and it is listed in `hardening-checklist.md`. |
| GitHub Actions | **Major tags** (`actions/checkout@v4`) | Current practice, and an accepted risk: a compromised upstream tag executes in this repository's context. SHA pinning is stronger and is not used. |
| npm (both web workspaces) | `package-lock.json`, `npm ci` in CI | The web toolchain is not library-shaped, so a lockfile is appropriate there. |

**No Python lockfile, deliberately.** There is nothing to lock: the core has no
dependencies, and the extras are a handful of well-known packages. A lockfile would
add a moving part and a false sense of control. Revisit if this repository ever
deploys a service whose exact environment needs to be reproducible — at that point
the lock belongs to the deployment, not to the library.

**No vendoring.** No third-party code is copied into this repository.

## 4. Update cadence

| Trigger | Cadence | Who acts |
| --- | --- | --- |
| Security advisories | Immediate, out of band | Maintainer, on notification from Dependabot or a scanner |
| Version updates | Weekly, Monday | Dependabot opens grouped PRs; a human merges them |
| Base image | Weekly (`docker` ecosystem in `dependabot.yml`) | Dependabot opens the PR; the image is rebuilt on merge |
| GitHub Actions | Weekly, grouped | Dependabot |
| Review of this policy | At each minor release | Maintainer |

`dependabot.yml` details, and the reasoning behind them:

- **Version updates are grouped** per ecosystem, so a routine bump produces one
  pull request rather than a dozen. Noise is the main reason Dependabot PRs get
  ignored.
- **Security updates are not grouped.** A single advisory should be visible on its
  own, attributable to one package, and reviewable without reading a diff about
  eleven other things.
- **`mypy` major bumps are ignored.** mypy's target Python version is pinned in
  `[tool.mypy]`; a major bump needs a human to decide whether to change the target.
- **`open-pull-requests-limit`** is 5 for most ecosystems and 3 for docker, so a
  backlog cannot bury real work.
- **Commit prefixes** (`deps(python)`, `deps(console)`, `deps(site)`, `deps(docker)`,
  `deps(actions)`) make the history scannable.

**Every dependency PR still has to pass the provenance checklist** in
`.github/PULL_REQUEST_TEMPLATE.md`. A dependency is not exempt: a new transitive
dependency inside an optional extra is a real change to what the project ships, and
`pip-audit` plus dependency review exist to make that visible.

## 5. What CI proves about the supply chain

| Control | Workflow | What it proves |
| --- | --- | --- |
| `gitleaks` over full history | `security.yml` | No secret is present in the repository's history, including removed commits. |
| `pip-audit --strict` on the built wheel | `security.yml` | No **known** advisory affects the wheel's dependency closure. With no extras that closure is empty, so this is a canary for a future accidental dependency. |
| `pip-audit --strict` per extra | `security.yml` | Findings are attributable to `api`, `devices` or `science` individually. |
| Dependency review | `security.yml`, on `pull_request` with `contents: read` and `pull-requests: write` | A PR that adds a vulnerable or licence-incompatible dependency fails. Threshold: `moderate`. |
| CodeQL (`python`, `javascript-typescript`) | `codeql.yml` | Static analysis for security and quality, on push, PR and weekly. |
| Determinism gate | `ci.yml` | Two identical runs are byte-identical — no hidden state, no unpinned randomness. |
| Clean-venv install + entry-point smoke test | `release.yml` | The published wheel installs and `cs-sim version` runs before anything is published. |
| `twine check` | `release.yml` | Distribution metadata is valid. |
| Provenance + SBOM on the image | `docker.yml` | Published images carry build provenance and an SBOM. |
| Tag-only publishing | `docker.yml`, `release.yml` | An unreviewed commit cannot become a pullable or installable artefact. |

## 6. SBOM

**Current state, honestly:** the container image ships an SBOM because
`docker/build-push-action` is configured with `sbom: true`. **No SBOM is generated
for the Python distributions yet.** `make sbom` calls
`tools/gen_sbom.py --out sbom.json`, and that script does not exist. `sbom.json`
and `sbom.spdx.json` are git-ignored, so no SBOM is committed either.

**Intended behaviour** for `tools/gen_sbom.py`, so the contract is testable:

- Emit **CycloneDX JSON** by default, because it is what the container tooling
  already produces and what most scanners consume. SPDX is a possible second format,
  not an alternative to deciding on one.
- Record the project itself as the root component at `0.1.0`.
- For the core, record **no components** — and say so explicitly in the document
  rather than emitting an empty list that looks like a failure. "This package has no
  runtime dependencies" is a meaningful SBOM entry.
- For each extra, emit a separate component group so that a consumer can tell
  which dependency came from `devices` and which from `api`.
- Record the Python version and platform the SBOM was generated for, since an SBOM
  is a statement about an environment.
- Never talk to the network. An SBOM generator that resolves packages from an index
  at build time is a supply-chain risk wearing a security tool's clothes.

Once that exists, the release workflow should attach the SBOM to the GitHub
release alongside the sdist and wheel, and the container SBOM should stay attached
to the image attestation rather than being copied into the repository.

## 7. What to do when a dependency is problematic

1. **Confirm reachability.** A `CVE` in a package that is not imported on any live
   path is a lower priority than one that is. `pip-audit` names the package, not
   whether this project calls the vulnerable code.
2. **Prefer removal over upgrade.** For an optional extra, deleting the extra is
   sometimes the right answer. This is only possible because the extras are
   isolated, and it is worth taking advantage of.
3. **Pin the fix explicitly** if a lower bound already permits the vulnerable
   version, raise the lower bound — and say why in the commit message, because
   `>=` bounds with no explanation are indistinguishable from arbitrary ones.
4. **If there is no fix, disable the feature and say so.** Removing the device
   extra for a release is a legitimate response; shipping a known-vulnerable code
   path is not.
5. **If a credential was reachable, rotate it.** A vulnerable dependency does not
   by itself mean a secret leaked, but the two travel together often enough that
   checking is cheaper than reasoning about it.

## 8. Licence policy

- The project is **MIT** (`LICENSE`), and incoming contributions are accepted under
  it.
- New dependencies must have a licence that is permissive and compatible with MIT
  distribution. Copyleft licences that would impose obligations on downstream
  users of this package are not acceptable for a dependency, and are flagged by
  dependency review.
- Because the core has no dependencies, the licence question is confined to a
  handful of optional, opt-in packages — which is another reason to keep it that
  way.
- No third-party code, asset or dataset is vendored into this repository. The
  visual assets in `media/` are project-owned SVGs; the typefaces referenced in
  `media/brand.md` are named as recommendations and are not shipped.
