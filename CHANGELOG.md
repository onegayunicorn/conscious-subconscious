# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
Versions are not committed to dates, and nothing in this file is a roadmap.

## [Unreleased]

Nothing yet.

## [0.1.0] — initial public scaffold

The first public version. It is a scaffold, and this entry says exactly what that
means: what works, what is a stub, and what is referenced but absent.

### Added

**Simulation core — implemented and usable**

- `conscious_subconscious` package, `src/` layout, Python 3.10–3.13, **no
  third-party runtime dependencies**.
- `core/`: `VirtualClock` (fixed step, no wall-clock reads, `MAX_STEPS` guard),
  `DeterministicRng` (SHA-256-derived named substreams), `EventBus` (bounded
  history, subscriber dispatch), `Parameter` / `ParameterSet` with provenance, and
  the typed error hierarchy rooted at `ConsciousSubconsciousError`.
- `model/`: `SimulationEngine` with a documented seven-step order, `Tissue` (scalar
  integrity with a ceiling and `wasted_repair` accounting), `MediatorField` (five
  channels, exponential decay, production/dissipation audit), `SubconsciousSystem`
  (the only path that changes integrity), `ConsciousSystem` (attention budget,
  fatigue, hysteresis, perception separate from reality), `MetricsRecorder`
  (trapezoid area-under-damage, recovered-fraction thresholds), and `StepContext`.
- `modules/`: `inflammation`, `perfusion`, `circadian`, `autonomic` and
  `expectancy`, all registered by name, built in sorted order, and forbidden by
  contract from touching tissue integrity.
- `parameters.py`: all 34 default parameters declared once with a unit, bounds, a
  provenance grade and a note. 1 `literature`, 26 `assumed`, 7 `invented`,
  0 `measured`.
- Nine built-in scenarios with caveats, including the `focused-uncoupled` control
  in which the central coupling constant is set to `0.0`.
- `sim/`: `sweep` and `sensitivity` (`one_factor_sensitivity` ranks unsupported
  parameters by influence on a chosen metric), a Markdown report renderer that
  never prints a missing value as `0`, and the `cs-sim` CLI.

**Protocol layer — implemented**

- `protocols/envelope.py`: the closed envelope (`v`, `id`, `ts`, `type`, `source`,
  optional `session`, `payload`), a validator that reports every problem rather
  than the first, and hard payload/id/source ceilings.
- `protocols/codec.py`: NDJSON framing with a maximum line length that **raises**
  rather than truncating.
- `protocols/jsonrpc.py`: JSON-RPC 2.0 builders, validators and an application
  error-code range (`SESSION_NOT_FOUND`, `SIMULATION_FINISHED`,
  `DEVICE_UNAVAILABLE`, `RATE_LIMITED`, `UNAUTHORISED`).
- `protocols/topics.py`: the `cs/v1/sessions/...` topic scheme with identifier
  validation against `^[A-Za-z0-9._-]{1,64}$`, and wildcard helpers for operators.
- `protocols/transport.py`: the abstract `Transport` and `InProcessTransport` with
  a finite queue that refuses rather than dropping.
- Five JSON Schema files under `protocols/schemas/`, which are the tie-breaker
  between the Python and TypeScript implementations.

**Device layer — implemented, read-only**

- The `DeviceDriver` contract with `open` / `read` / `close` / `capabilities`, and
  the deliberate separation of `DeviceUnavailable` from `DeviceError`.
- Five adapters: `simulated` (no hardware), `serial` (`CS,<channel>,<value>` line
  parsing), `lsl`, `ble-heart-rate` (pure parsing separated from the radio, RR
  intervals in 1/1024 s) and `replay` (deterministic CSV playback plus
  `write_recording`).
- **No adapter has a write, send or stimulate method.** `bidirectional` defaults to
  `False`. This is a safety boundary, not a missing feature.

**CLI**

- `cs-sim` with `run`, `compare`, `sweep`, `sensitivity`, `scenarios`,
  `parameters`, `modules` and `version`; `--json`, `--out`, `--samples`,
  `--scenarios-file`, `--set`, `--seed`, `--dt`, `--horizon`, `--policy`,
  `--modules`; exit codes 0 / 1 / 2 by cause.

**Internationalisation**

- `i18n.py`: locale lookup by probing `CS_LOCALES_DIR`, a `locales/` directory
  beside the module, then `i18n/locales` in ancestor directories; a locale fallback
  chain; and a translate function that returns the key rather than raising when a
  catalog is missing.

**Documentation**

- `docs/`: index, model-spec (equations, symbol-to-key table, full provenance
  table), provenance, architecture, protocol, hardware, cli, api, testing,
  deployment, faq, roadmap.
- `mkdocs.yml` with Material, a nav covering the pages above, and Mermaid diagram
  support.
- Root: `DISCLAIMER.md` (canonical), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  (Contributor Covenant 2.1), `SECURITY.md`, this changelog.

**Security governance**

- `security/threat-model.md`: STRIDE over the API service, session manager, device
  adapters, MQTT/WS transports, pipelines, web console and supply chain, with the
  read-only-device boundary and the "never a medical device" boundary treated as
  assets in their own right.
- `security/hardening-checklist.md`: what is done in this repository versus what is
  operator responsibility.
- `security/incident-response.md`: roles, severity levels, the first hour, and
  concrete procedures for a leaked credential and a leaked sensor recording.
- `security/dependency-policy.md`: core-dependency-free rule, extra isolation,
  pinning, update cadence, SBOM.

**Deployment**

- `deploy/docker/`: multi-stage `Dockerfile` (`python:3.12-slim`, non-root UID/GID
  10001, `.[api]`, `CS_LOCALES_DIR=/app/i18n/locales`, `HEALTHCHECK` on
  `/healthz`), `docker-compose.yml` with a named data volume and an `env_file` that
  fails safe when `.env` is absent, and a `.dockerignore`.
- `deploy/k8s/`: namespace, ConfigMap, example Secret, Deployment (non-root,
  read-only root filesystem, dropped capabilities, probes, resource bounds), Service,
  HPA, default-deny NetworkPolicy, Ingress and a kustomization.
- `deploy/systemd/`: hardened `oneshot` service plus a daily timer, and a README.
- `deploy/platforms.yaml`: the honest supported/best-effort/unsupported matrix.
- `deploy/README.md`.

**CI/CD**

- `.github/workflows/ci.yml`: ruff, `ruff format --check`, strict mypy and pytest
  with coverage across Linux 3.10–3.13 plus macOS and Windows at 3.11 and 3.13; a
  Node 20 job for the web workspaces; and a determinism job that runs
  `cs-sim compare` twice and diffs the output, checks the run digests, and asserts
  the `focused-uncoupled` control still equals `baseline`. `fail-fast: false`
  throughout.
- `.github/workflows/security.yml`: `gitleaks` over full history, `pip-audit` on the
  built wheel and separately on each extra, and dependency review on pull requests.
- `.github/workflows/codeql.yml`: CodeQL for Python and JavaScript/TypeScript on
  push, pull request and a weekly schedule.
- `.github/workflows/docker.yml`: buildx multi-arch (`linux/amd64`,
  `linux/arm64`) to `ghcr.io/onegayunicorn/conscious-subconscious`, published only
  on `v*` tags, with `provenance: true` and `sbom: true`.
- `.github/workflows/release.yml`: sdist and wheel, `twine check`, a clean-venv
  install with a `cs-sim version` smoke test, artefacts attached to a GitHub
  release, and PyPI publication via OIDC Trusted Publishing.
- `.github/workflows/docs.yml`: `mkdocs build --strict` and deployment to GitHub
  Pages.
- Issue templates (bug report, feature request, model change — the last one
  requiring the parameters affected and their provenance), a pull request template
  with a provenance/honesty checklist, and Dependabot for pip, both npm workspaces,
  docker and github-actions.

### Stubbed, planned or referenced but not present

Listed together and plainly, because the repository references these in
`pyproject.toml`, the `Makefile`, `.pre-commit-config.yaml`, the deployment
manifests or the docs, and it should be obvious which of those references currently
lead nowhere.

- **`conscious_subconscious.services.api`** — the FastAPI service. Referenced by
  `pyproject.toml`, `.env.example`, the Dockerfile and the Kubernetes manifests. Not
  implemented, so `/healthz`, `/readyz` and every `/v1` route return nothing.
- **The session manager** — not implemented.
- **`conscious_subconscious.hardening.cli`** — the `cs-hardening` console script and
  `make audit`. Declared in `pyproject.toml`; the subpackage does not exist, so the
  command fails with an import error.
- **`conscious_subconscious.pipelines`** — the data-pipeline runner, and the root
  `pipelines/*.yaml` DAG definitions it would execute. Neither exists. These are
  data pipelines, **not** CI.
- **`tools/`** — `preflight.py`, `build_platforms.py`, `gen_sbom.py` and
  `check_locales.py`. Referenced by `make preflight`, `make build-all`, `make sbom`,
  `make locales-sync` and the `locale-parity` pre-commit hook. Not implemented, so
  those targets cannot succeed.
- **`tests/`** — declared as `testpaths` in `pyproject.toml` and run by `make test`
  and CI. The directory does not exist.
- **`i18n/locales/`** — the locale catalogs. `i18n.py`, the pre-commit hook,
  `tools/check_locales.py` and the container's `COPY i18n ./i18n` all assume it
  exists. As a result the container image cannot currently be built.
- **`apps/console`** — React + TypeScript + Vite web console (`npm run build`,
  `npm test`). Referenced by `protocols/__init__.py` as
  `apps/console/src/api/types.ts` and by the CI web job. Not present.
- **`apps/site`** — the marketing and documentation site (`npm run build`). Not
  present.
- **`hardware/firmware/`** — the microcontroller firmware that would speak the
  `CS,<channel>,<value>` line format. Referenced by the serial adapter's
  documentation. Not present.
- **Real network transports** — WebSocket and MQTT bindings for the protocol layer.
  Only the in-process transport exists.
- **`deploy/k8s/` persistence** — the Deployment uses an `emptyDir` for `/data`, so
  data does not survive a pod restart.
- **A root `.dockerignore`** — the exclusions live in `deploy/docker/.dockerignore`,
  which Docker does not read, because the build context is the repository root.

### Notes on this release

- Every parameter is graded. 33 of the 34 defaults have **no empirical support**
  (26 `assumed`, 7 `invented`); the only supported value is
  `module.circadian.period_hours`.
- Any parameter overridden at runtime has its provenance downgraded to `assumed`
  automatically, with a note naming the previous value.
- Runs are deterministic and `conscious.neural_drive_jitter` defaults to `0.0`, so a
  default run draws no random numbers.
- **Nothing in this release has been validated against any data.** No benchmark, no
  user count and no performance figure is claimed anywhere in this repository.
- **Not a medical device.** Educational and artistic simulation only. See
  `DISCLAIMER.md`.

[Unreleased]: https://github.com/onegayunicorn/conscious-subconscious/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/onegayunicorn/conscious-subconscious/releases/tag/v0.1.0
