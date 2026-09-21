# Hardening checklist

Split into two lists: things this repository does, and things the operator must do.
An item belongs in the first list only if it is actually present in the tree — a
checkbox that is ticked because the intent was good is worse than an unticked one.

Related: [`threat-model.md`](threat-model.md) for the reasoning,
[`incident-response.md`](incident-response.md) for what to do when something goes
wrong, [`dependency-policy.md`](dependency-policy.md) for the supply-chain rules.

> **Boundary.** Hardening a simulation service does not make it a medical device and
> does not make its output clinical information. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Part 1 — done in this repository

### Repository and secrets

- [x] `.gitignore` excludes `.env`, `.env.local`, `.env.*.local`, `*.pem`, `*.key`,
      `credentials.json`, `*.sqlite3`, `*.db`, `runs/`, `out/`, `sbom.json` — with
      `!.env.example` so the template is committed and the real file is not.
- [x] `.env.example` contains **no real values**; every variable has a safe default
      in code.
- [x] `gitleaks` runs on full history in CI (`.github/workflows/security.yml`,
      `fetch-depth: 0`) and as a pre-commit hook.
- [x] `detect-private-key` and `check-added-large-files` (`--maxkb=2048`) in
      `.pre-commit-config.yaml`.
- [x] No credential, token, key or password is committed anywhere in the tree,
      including this directory. `security/` deliberately names no real value.
- [x] The Docker build excludes secrets from image layers (`.env*`, `*.pem`,
      `*.key`, `credentials.json` in `deploy/docker/.dockerignore`).

### Supply chain

- [x] The core package declares **zero** third-party runtime dependencies
      (`dependencies = []` in `pyproject.toml`).
- [x] Optional dependencies are isolated into `api`, `devices`, `science`, `dev`
      extras, so a finding is attributable to one extra.
- [x] Optional imports live inside each driver (`pyserial`, `pylsl`, `bleak`), so
      importing the package never requires them.
- [x] `pip-audit --strict` on the built wheel and separately on each of `api`,
      `devices` and `science` (`security.yml`).
- [x] `actions/dependency-review-action` with `fail-on-severity: moderate`, scoped
      to `pull_request` events with `contents: read` and `pull-requests: write`.
- [x] Dependabot for pip, both npm workspaces, docker and github-actions, with
      version updates grouped and security updates left ungrouped.
- [x] Container build sets `provenance: true` and `sbom: true`, so published images
      carry an SBOM and build attestation.
- [ ] **SHA-pinned GitHub Actions.** Actions are pinned to current major tags, not
      commit SHAs. This is an accepted, documented risk in the threat model, not an
      oversight.
- [ ] **Python lockfile.** Deliberate: a library-shaped package uses lower bounds
      only. Revisit if a service is deployed from this repository.
- [ ] **`tools/gen_sbom.py`.** Referenced by `make sbom` and not implemented, so no
      SBOM is generated for the Python artefacts yet.

### CI/CD and release integrity

- [x] Minimal `permissions:` per workflow and per job; the default is
      `contents: read`.
- [x] PyPI publishing uses **OIDC Trusted Publishing** (`id-token: write`, no stored
      API token) with the operator step documented in the workflow.
- [x] Container images publish **only on `v*` tags**; all other runs are build-only.
- [x] Release workflow verifies the wheel installs into a clean virtualenv and that
      `cs-sim version` runs before anything is published.
- [x] `twine check` on the built artefacts.
- [x] `concurrency` groups on CI and docs, with `cancel-in-progress` on CI.
- [x] Determinism gate: `cs-sim compare` is run twice and diffed, and the
      `focused-uncoupled` control is asserted equal to `baseline`.
- [x] CodeQL for `python` and `javascript-typescript`, with
      `security-and-quality` queries, on push, PR and a weekly schedule.
- [x] `fail-fast: false` throughout, so one failing platform cannot mask others.
- [ ] **Branch protection and required reviews** are repository settings, not files
      in the tree; they cannot be asserted from here.
- [ ] **Artifact attestation for the Python distributions** (`actions/attest-build-provenance`)
      is not configured. Only the container image has provenance.

### Runtime and code

- [x] No network access is required by the core: the engine uses only the standard
      library, a virtual clock and a seeded RNG.
- [x] The only path that writes tissue integrity is
      `SubconsciousSystem.step`; `SimulationEngine.command` exposes three verbs and
      none of them sets integrity.
- [x] **No device adapter has a write, send or stimulate method**, and
      `DeviceCapabilities.bidirectional` defaults to `False`.
- [x] Untrusted input is bounded at every layer: envelope payload 262 144 bytes,
      NDJSON line 1 048 576 bytes, serial line 512 bytes, serial drain of 256 lines
      per call, LSL `MAX_CHUNK` per pull, event history 20 000 events,
      `MAX_STEPS = 10_000_000`.
- [x] Topic and session identifiers validated against
      `^[A-Za-z0-9._-]{1,64}$` before a topic string is built, so `/`, `+` and `#`
      cannot be smuggled in.
- [x] The in-process transport queue is finite and **raises** when full rather than
      dropping samples silently.
- [x] Malformed device input raises; unknown channels are marked `invalid` and
      cannot be fed to a module (`Sample.usable`).
- [x] Errors are a typed hierarchy rooted at `ConsciousSubconsciousError`
      (`ParameterError`, `ConfigurationError`, `ProtocolError`, `DeviceError`,
      `DeviceUnavailable`, `PipelineError`), so a caller can distinguish "not
      available here" from "misbehaved".
- [x] `cs-sim` exits 0 / 1 / 2 by cause, and every diagnostic goes to stderr.
- [x] mypy runs in **strict** mode.
- [x] Ruff selects `B` (bugbear), `SIM`, `RET`, `ARG`, `PTH`, `UP` — including the
      rules that catch mutable-default and exception-swallowing mistakes.
- [x] The disclaimer is attached to every `SimulationResult` and printed by the CLI
      epilog and the report footer.

### Container and manifests

- [x] Multi-stage `Dockerfile`: build tooling and compilers are absent from the
      final image.
- [x] Non-root: fixed UID/GID 10001, declared `USER 10001:10001`.
- [x] `HEALTHCHECK` on `/healthz` using the standard library, so no `curl` or `wget`
      is added to the image.
- [x] Python minor version pinned (`python:3.12-slim`).
- [x] Kubernetes: `runAsNonRoot`, `readOnlyRootFilesystem`, all capabilities
      dropped, `allowPrivilegeEscalation: false`, `seccompProfile: RuntimeDefault`,
      `automountServiceAccountToken: false`.
- [x] Kubernetes: liveness `/healthz`, readiness `/readyz`, plus a startup probe.
- [x] Kubernetes: resource requests and limits on the container.
- [x] Kubernetes: default-deny NetworkPolicy for **ingress and egress**, with
      ingress limited to the ingress-controller namespace and the same namespace, and
      egress limited to DNS.
- [x] Kubernetes: the example Secret is placeholders only, is annotated
      `do-not-apply`, and is **excluded from `kustomization.yaml`**.
- [x] Compose: `env_file` with `required: false` so a missing `.env` fails safe
      rather than erroring or defaulting to something insecure; host port bound to
      `127.0.0.1`; `no-new-privileges`.
- [x] systemd: `ProtectSystem=strict` with one `ReadWritePaths` entry,
      `RestrictAddressFamilies=AF_UNIX`, empty `CapabilityBoundingSet`,
      `SystemCallFilter=@system-service`, `NoNewPrivileges`, `MemoryDenyWriteExecute`.
- [ ] **Root `.dockerignore`.** The exclusions live in `deploy/docker/.dockerignore`,
      which Docker does **not** read, because the build context is the repository
      root. The file has to be mirrored to the root to take effect.
- [ ] **`COPY i18n ./i18n` currently fails**, because `i18n/locales/` does not exist
      in the tree yet. The image cannot be built until it does.

### Documentation honesty

- [x] `DISCLAIMER.md` is the canonical medical/health disclaimer and is linked from
      the other documents rather than paraphrased.
- [x] "No payments, pricing, subscriptions or checkout" is stated wherever the
      question could arise, and no such feature is described as existing.
- [x] "Not implemented" and "not verified" are stated explicitly for the API
      service, the pipelines, the web workspaces, load testing, the Kubernetes
      manifests, the systemd units and every hardware adapter.
- [x] The operator steps that this repository does **not** perform are stated inline
      where they are needed — the PyPI Trusted Publishing registration in
      `release.yml`, the missing `i18n/locales/` directory and the mislocated
      `.dockerignore` in `deploy/README.md` — rather than left as a surprise.
- [x] Every parameter carries a provenance grade, and any override downgrades it to
      `assumed`.
- [x] No document invents benchmarks, user counts or roadmap dates.

## Part 2 — operator responsibility

Nothing below is done by this repository, and none of it can be asserted from a
file in the tree.

### Identity and access

- [ ] Generate `CS_API_KEY` with a CSPRNG (`openssl rand -hex 32`), store it in a
      secret manager, and never commit it.
- [ ] Rotate the API key on a schedule and after any suspected exposure.
- [ ] Do **not** inline the API key into a front-end build. Vite bakes `VITE_*`
      values into the bundle; a key there is public. Use a same-origin proxy or a
      short-lived token.
- [ ] If more than one party uses the service, replace the shared key with
      per-client credentials. A shared key has no revocation, no attribution and no
      rate-limit isolation.
- [ ] Restrict who may push to `main`, deploy, or run the release workflow, and
      enable branch protection with required reviews.
- [ ] Review what the release workflow does before configuring PyPI Trusted
      Publishing, and scope the trusted publisher to this repository, workflow and
      environment only.

### Network

- [ ] Terminate TLS at the ingress and redirect HTTP. Ship a real certificate; every
      hostname in the manifests is `.example.invalid`.
- [ ] Keep the service off the public internet unless it genuinely needs to be
      there. If it is exposed, require the API key before the request reaches the
      app.
- [ ] Configure per-client authorisation for sessions. Identifier validation
      prevents namespace escape; it does not prevent one client reading another's
      session.
- [ ] If MQTT is used, configure broker ACLs that **deny `cs/v1/#` wildcard
      subscriptions to clients**. The `session_wildcard()` and `device_wildcard()`
      helpers are for operators, and a helper cannot enforce who subscribes.
- [ ] Confirm the CNI actually enforces `NetworkPolicy`. On a cluster whose CNI does
      not, the policy objects are accepted and do nothing.
- [ ] Move rate limiting to a shared store before running more than one replica;
      the in-process token bucket multiplies with the replica count, and the HPA
      scales up under the load that makes the limit matter.
- [ ] Pin the BLE address in `CS_BLE_ADDRESS` anywhere the data matters. A blank
      address takes the first advertiser in radio range.

### Data

- [ ] Treat every sensor recording as personal data. Store recordings on encrypted
      media with filesystem permissions limited to the service account.
- [ ] Keep `CS_DATA_DIR` on a volume that is backed up **and** encrypted, or accept
      that a pod restart destroys it (`emptyDir` is the shipped default).
- [ ] Decide and document a retention period for recordings and run data. Nothing in
      this project deletes them for you.
- [ ] Do not enable telemetry, analytics or crash reporting that transmits session
      content. A heart-rate value in a page view is personal data leaving your
      control.
- [ ] If participant data is involved, get whatever consent and ethics approval your
      jurisdiction requires. This repository provides none of that, and the model's
      output is not a clinical endpoint.

### Platform

- [ ] Apply PodSecurity admission labels (restricted) to the namespace, or enforce
      an equivalent policy. The manifests set the fields; admission is what enforces
      them.
- [ ] Set resource quotas and a `LimitRange` so a runaway sweep cannot exhaust the
      namespace.
- [ ] Add a `PodDisruptionBudget` before running with `replicas: 2` in production.
- [ ] Run `systemd-analyze security` on the systemd unit and act on the result. It
      has not been run by this project.
- [ ] Confirm the `systemd` version supports every directive used
      (`StateDirectory=`, `ProtectProc=invisible`, `RestrictSUIDSGID`,
      `SystemCallFilter=@system-service`). Remove unsupported directives rather than
      the whole hardening block.
- [ ] Pin container images by digest in production, not by tag.
- [ ] Run a vulnerability scanner against the deployed image and the cluster, on a
      schedule, in addition to the CI audits.
- [ ] Set up monitoring and alerting. Nothing ships with it: a failing scheduled job
      is visible only to someone who looks.
- [ ] Patch the base image and rebuild on a cadence. Dependabot will open the pull
      request; someone has to merge it.
- [ ] Consider SHA-pinning GitHub Actions in a fork you deploy from. This repository
      does not.

### Behaviour

- [ ] Never describe a deployment of this project as a medical device, a clinical
      tool, a therapeutic intervention or a diagnostic, in a UI, a README, a slide,
      a store listing or a support reply.
- [ ] Never present simulation output as a prediction, a prognosis or evidence about
      a person.
- [ ] If you publish results, publish the default parameters and their provenance
      alongside them, and regenerate the run from the recorded seed so the digest
      can be checked.
- [ ] Refuse feature requests that would add a clinical endpoint, a stimulation path
      or a user-facing "healing" score. Those change what the project is, not just
      what it does.
