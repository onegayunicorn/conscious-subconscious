# Roadmap

**This is direction, not a commitment.** There are no dates, no version-bound
promises, no staffing estimates and no "coming soon". Anything listed here may
change, shrink or disappear. Nothing here is scheduled, and nothing should be
quoted as a plan.

Two things are not on the roadmap in any form, at any horizon:

- **Medical capability.** No diagnostic, therapeutic, clinical or device function.
  The project is an educational and artistic simulation and stays one.
- **Payments.** No pricing, tiers, checkout, subscriptions or payment integrations.
  They are not implemented today and are not planned.

> **Boundary.** Even if every item below were finished, the model would still
> encode an unvalidated assumption and would still not be clinical evidence. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Current state (0.1.0)

Implemented and usable today:

- the deterministic simulation engine, tissue, mediator field, conscious and
  subconscious systems
- five optional modules (inflammation, perfusion, circadian, autonomic, expectancy)
- nine built-in scenarios with caveats, including the `focused-uncoupled` control
- the full `cs-sim` CLI: `run`, `compare`, `sweep`, `sensitivity`, `scenarios`,
  `parameters`, `modules`, `version`
- the parameter provenance system and its four grades
- the protocol layer: envelope, NDJSON codec, JSON-RPC, MQTT topic helpers,
  in-process transport, five JSON Schema files
- five device adapters, including the pure parsing functions for serial and BLE
- the "magic" Markdown report renderer

Scaffolded or referenced but **not** present in the repository: the API service
(`services/api`), the session manager, data-pipeline definitions (`pipelines/*.yaml`
and `pipelines/runner.py`), the data-pipeline runner, the hardening self-audit
(`hardening/cli.py`, the `cs-hardening` entry point), the helper scripts under
`tools/`, the test suite under `tests/`, the locale catalogs under `i18n/locales/`,
the web workspaces under `apps/`, the firmware under `hardware/firmware/`, and the
`services` adapters that would carry the protocol over a real network.

Honest summary: the Python simulation is real; the surrounding service and web
scaffolding is currently a set of manifests, schemas and configuration contracts
with no code behind them.

## Near term

Small things that make the existing artefact more trustworthy, in rough order of
value:

- **Finish the test suite.** `tests/` is declared in `pyproject.toml` and does not
  exist. Golden reference runs are the highest-value part: they are what turn "the
  model is deterministic" from a claim into a check.
- **Add the missing `i18n/locales/en.json`.** `i18n.py`, the `locale-parity`
  pre-commit hook, `tools/check_locales.py` and the container's `COPY i18n` all
  assume it exists. Right now the container cannot build.
- **Ship the helper scripts** that the `Makefile` already calls:
  `tools/preflight.py`, `tools/build_platforms.py`, `tools/gen_sbom.py`,
  `tools/check_locales.py`. A `Makefile` target that cannot run is worse than a
  missing one.
- **Implement `hardening/cli.py`** so that the declared `cs-hardening` entry point
  and `make audit` work, covering the checks in `security/hardening-checklist.md`.
- **Add property-based tests** for the untrusted-input parsers:
  `Envelope.from_json`, `NdjsonDecoder.feed`, `parse_topic`, `parse_line` and
  `parse_heart_rate_measurement`. These are the functions that face data the project
  did not produce.
- **Write the root `.dockerignore`**, mirroring `deploy/docker/.dockerignore`, so
  the exclusions there actually take effect.
- **Make the `pipelines/` DAG runner real.** Root `pipelines/*.yaml` are intended to
  be data-pipeline definitions executed by
  `conscious_subconscious/pipelines/runner.py`; neither exists yet. They are not CI
  workflows and should not be confused with the `.github/workflows/` files.

## Mid term

- **Build the API service and session manager** as described in
  [api.md](api.md), honouring the configuration contract in `.env.example` (API key,
  CORS allow-list, per-client rate limit, body-size cap) and the health endpoints the
  deployment manifests already probe. Until this exists, the Docker image, the
  Compose stack and the Kubernetes manifests describe a service that cannot start.
- **Add a real network transport.** Today the only concrete `Transport` is
  in-process. A WebSocket transport for `sim.tick` streaming and an MQTT binding for
  the topic scheme would make the protocol layer useful outside a test.
- **Bring up the web workspaces**: `apps/console` (React + TypeScript + Vite, with
  `npm run build` and `npm test`) and `apps/site`. The protocol schemas already
  reference `apps/console/src/api/types.ts` as the TypeScript side of the contract.
- **Automate SBOM generation and signing** in the release path —
  `tools/gen_sbom.py`, CycloneDX or SPDX output attached to the GitHub release, and
  provenance already enabled on the container build.
- **Publish a validation notebook that is honest about what it cannot do.** The
  useful version of this is not "here is a fit to real healing data"; it is a
  demonstration that the model's behaviour is dominated by unsupported constants,
  which `cs-sim sensitivity` already shows in a table.

## Long term

Long-horizon items are the most likely to change. All are direction only.

- **Extend the model in ways that add honesty, not resolution.** Geometry, cell
  populations or scar formation would each add many new `assumed` parameters, which
  would make the model *look* more scientific while being no better supported. A
  documented decision about that trade — including a decision not to do it — is more
  valuable than the extra variables. See `research/open-questions.md`.
- **Make external replication easy.** The interesting version of this project for a
  third party is one where an independent group can re-run a published sweep and
  check the digest. That is a packaging and documentation problem more than a
  modelling one.
- **Federation and multi-session operation**, if and only if a session manager
  exists with the bounds described in [api.md](api.md) (identifier validation,
  bounded sessions, single writer per session).
- **Platform breadth** beyond the matrix in `deploy/platforms.yaml`, driven by
  actual demand rather than by ambition. The core has no dependencies, so the
  constraint is testing capacity, not portability.

## Deliberately not planned

Stated so that their absence is a decision rather than an oversight:

| Not planned | Why |
| --- | --- |
| Clinical validation or trials | Out of scope for a simulation sandbox; the project has no clinical partners, data or regulatory intent. |
| Any medical, diagnostic or therapeutic function | The project would cease to be what it is. |
| A "healing app", wearable integration that writes to a body, or any stimulation path | Adapters are read-only with respect to the wearer as a safety boundary, not as a temporary limitation. |
| Calibrating the model to real healing data | It would require human data collection and a claim the project cannot support, and calibrating invented constants does not make them measured. |
| A hosted instance, accounts, or any data collection | No hosted service exists. The project collects nothing. |
| Payments of any kind | Not implemented and not planned. |
| A model leaderboard or benchmark | There is nothing to rank until there is a measurable target, which there is not. |
