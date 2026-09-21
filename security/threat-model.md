# Threat model

A STRIDE walk over the components that exist, plus the ones that are planned and
scaffolded. Written by the project for the project: **no external security review
has happened.** Where a mitigation is real code, the code is cited. Where a
mitigation is a configuration contract with nothing behind it yet, that is said
instead of implied.

> **Boundary.** This is a threat model for a simulation service. Two properties are
> treated as security assets in their own right, and they are listed first because
> losing either would be the worst outcome in this document:
>
> - **The read-only-device boundary.** No shipped adapter can write to, stimulate or
>   actuate anything on the person wearing a sensor. There is no write path to lose
>   — which is exactly why it must not be added casually.
> - **The "never a medical device" boundary.** Nothing in this project may acquire a
>   clinical function, a clinical claim or a regulatory role. A vulnerability in a
>   simulation is a bug; a simulation that becomes a medical device without a
>   safety case is a different class of problem entirely.

## 1. Scope and assumptions

In scope: the Python package, its device adapters, the protocol layer, the
deployment artefacts, and the (planned) API service and web console.

Out of scope, explicitly: the host operating system, the container runtime, the
Kubernetes control plane, the ingress controller, the MQTT broker (none ships
here), the reader's browser, and the physical safety of sensors. Where those matter,
the operator owns them.

Assumptions:

- The service, if deployed, is reachable over a network the operator controls.
- Sensor data is personal data by default. A heart-rate or EDA recording from an
  identifiable person is sensitive, even when the project itself collects nothing.
- Documents in this repository are served to the public by GitHub; a threat model
  that names a real credential is itself a leak. Nothing here contains one.

## 2. Assets

| ID | Asset | Why it matters | Where it lives |
| --- | --- | --- | --- |
| A1 | **Read-only-device boundary** | The ethical and safety spine of the hardware layer. | `devices/base.py`, every adapter |
| A2 | **"Never a medical device" boundary** | Determines what the project may claim and be used for. | `__init__.py::DISCLAIMER`, every document |
| A3 | **Parameter provenance integrity** | The project's actual differentiator. A silently upgraded grade turns an honest guess into an apparent finding. | `core/params.py`, `parameters.py` |
| A4 | Determinism / run digests | "Reproducible" must be checkable, or the teaching claim is empty. | `model/engine.py` |
| A5 | `CS_API_KEY` | The only credential the project ever asks for. | `.env`, Kubernetes Secret |
| A6 | Session state | Participant/config data in an API session; a cross-session leak is an integrity and privacy failure. | `SessionManager` (planned) |
| A7 | Sensor recordings | Personal health-adjacent data, in the most sensitive category the project can hold. | `devices/replay.py`, `CS_DATA_DIR` |
| A8 | The SQLite data directory | Runs and recordings at rest. | `/data` |
| A9 | Runtime integrity of the package | A trojaned wheel or dependency can do anything the service can. | PyPI, GHCR, `dist/` |
| A10 | The published deployment artefacts | A leaked credential or a weak default in a manifest propagates to every deployment. | `deploy/` |
| A11 | CI/CD and release integrity | Whoever controls the workflow controls what is published under the project's name. | `.github/workflows/` |
| A12 | Documentation honesty | Overstated docs are the failure mode this project exists to avoid. | `docs/`, `research/`, `marketing/` |

## 3. Components and threats

### 3.1 API service (planned, not implemented)

**Assets:** A5 (`CS_API_KEY`), A6 (session state), A2, A4.

**Status: no code exists.** The FastAPI application is not written. The mitigations
below are the documented contract in `.env.example`, `docs/api.md` and the
deployment manifests; none of them is enforced by anything today.

| STRIDE | Threat | Intended mitigation | Residual risk |
| --- | --- | --- | --- |
| **S**poofing | A caller with no key, or a wrong key, drives a session. | `X-API-Key` compared against `CS_API_KEY` on every `/v1` route. | A shared static key is not identity. It cannot be revoked per client, rotated without breaking all clients, or attributed to a user. If the service is ever multi-user, keys must become per-client and hashed at rest. |
| **S**poofing | The service is reached from a spoofed origin via a browser. | CORS allow-list from `CS_ALLOWED_ORIGINS`; never `*` with credentials. | CORS is a browser control, not an authorisation control. Non-browser clients ignore it entirely. The API key is the real gate. |
| **T**ampering | A caller mutates a run in a way the model forbids. | `SimulationEngine.command` accepts only `focus`, `release`, `set_policy`. **There is no command that sets tissue integrity**, so no request can bypass the repair rule. | Low for the model's own invariants; the surface is three verbs. The risk shifts to the session manager, which is not written. |
| **T**ampering | `--set`-style parameter overrides supplied through the API silently flatter the result. | Any override is recorded with provenance `assumed` and a note naming the replaced value (`ParameterSet.with_overrides`). | A client can still override everything and present the output without the provenance table. The report's own honesty is the mitigation, and it is a documentation control, not a technical one. |
| **R**epudiation | A caller denies issuing a state-changing command. | None today. Structured logs are the intent. | **Open.** With a shared key there is nothing to attribute a request to. If this matters, add per-key identity and append-only logging before it does. |
| **I**nformation disclosure | Cross-session access: one caller reads or drives another's session. | Session and device identifiers restricted to `^[A-Za-z0-9._-]{1,64}$` (`protocols/topics.py::validate_identifier`), so an identifier cannot smuggle in `/`, `+` or `#`. | **The restriction prevents namespace escape, not unauthorised access.** With one shared key, any authenticated caller may address any session. A per-session authorisation check is required and is not specified yet. |
| **I**nformation disclosure | Error responses leak paths, stack traces or `CS_API_KEY`. | Documented rule: no stack traces, no file paths, and the key is never echoed, logged or placed in an error payload. | Not implemented, therefore not verified. Framework default error handlers are exactly where this leaks. |
| **I**nformation disclosure | An oversized or deeply nested payload exhausts memory or CPU. | `CS_MAX_BODY_BYTES` body cap, rejected before parsing; `MAX_PAYLOAD_BYTES` (262 144) inside the envelope; NDJSON line cap of 1 048 576 bytes. | JSON depth and parser cost still scale within the cap. A 1 MiB deeply-nested body is still work. |
| **D**enial of service | Request flooding. | In-process token bucket at `CS_RATE_LIMIT_PER_MINUTE`; ingress-level `limit-rps` and `limit-connections` backstops in `deploy/k8s/ingress.yaml`. | **The bucket is per-process.** With more than one replica the effective limit multiplies by the replica count, and the HPA can scale replicas *up* under load — so the limiter gets weaker exactly when it is needed. Moving the bucket to a shared store is an operator decision that must be made explicitly. |
| **D**enial of service | One expensive request — a long horizon at a very small `dt` — occupies a worker. | `RunConfig.validate` bounds `dt > 0` and `horizon > 0`; `VirtualClock` has a hard `MAX_STEPS = 10_000_000` ceiling. | There is **no bound on total compute per request** and no queue, priority or timeout. The step ceiling translates to a very large amount of work. No load test has been run, so the practical cost is unknown. |
| **D**enial of service | A completed run is stepped forever, or a finished engine is reused. | `SimulationEngine.step()` raises `ConfigurationError` once finished; `SIMULATION_FINISHED` (`-32002`) exists as the application error code. | Requires the (unwritten) service to map that error correctly rather than constructing a replacement engine silently. |
| **E**levation of privilege | Malformed input reaches a code path with more capability than intended. | Envelope validation rejects unknown keys and unknown message types; optional third-party imports are isolated per driver, so a broken device dependency cannot be reached from a pure-protocol path. | Standard Python dependency-boundary risk. The core installs with **zero** third-party runtime dependencies, which removes the largest part of the attack surface from the engine itself. |

### 3.2 Session manager (planned, not implemented)

**Assets:** A6, A4.

| STRIDE | Threat | Intended mitigation | Residual risk |
| --- | --- | --- | --- |
| **S**poofing | A guessed or brute-forced session id is used. | Session ids must match the topic identifier class; ids should be generated from a CSPRNG, not a counter. | Not implemented. A predictable id plus a shared API key is full access to that session. |
| **T**ampering | Two concurrent `step` calls on one engine interleave and produce an order-dependent result. | Single writer per session, documented in `docs/api.md`. | **Open and subtle.** Determinism is a property of a run, not of concurrent access. A race produces a plausible-looking number that fails to reproduce — the worst failure mode for this project, because it undermines A4 without raising an error. |
| **R**epudiation | No record of who started or drove a session. | Intended structured logging. | Open, same as 3.1. |
| **I**nformation disclosure | Sessions are retained after use and enumerate each other. | Bounded session count and bounded lifetime are required. | Not implemented. Each session holds an engine, a sample history and an event history of up to 20 000 events (`EventBus(history_limit=20_000)`), so unbounded retention is a memory exhaustion bug that looks like a feature. |
| **D**enial of service | Session churn or leak exhausts memory. | See above. | Open until the bound exists. |

### 3.3 Device adapters

**Assets:** A1, A7, A8. **Implemented** — this is real code.

| STRIDE | Threat | Existing mitigation (in code) | Residual risk |
| --- | --- | --- | --- |
| **E**levation of privilege | An adapter gains a write path and can act on the wearer. | **`devices/base.py` has no `write`, `send` or `stimulate` method.** `DeviceCapabilities.bidirectional` defaults to `False`. Every shipped driver declares its capabilities explicitly. `DeviceDriver` is an ABC whose abstract surface is `open`/`close`/`read`/`capabilities`. | This is a **convention enforced by the base class, not a sandbox.** A contributor can add a write method to a subclass and nothing structurally prevents it. The compensating controls are the pull request checklist ("any new hardware path is read-only") and code review. Treat as a hard review rule. |
| **T**ampering | Malformed input from a device corrupts host state. | `parse_line` raises on malformed `CS,` lines (wrong field count, empty channel, non-numeric, `NaN`, unknown quality code). Unknown channels are marked `SampleQuality.INVALID` rather than rejected; `Sample.usable` is `False` for `invalid`, so the reading cannot reach a module. `MediatorField.add` **raises** on negative production rather than absorbing it. `AutonomicModule.observe` clamps to `[0,1]` and drops `NaN`. | A device can still emit a plausible-but-wrong value in range. Nothing can detect that; it is not a software-solvable problem. |
| **T**ampering | A chatty or hostile device starves the process. | Bounded drain: at most 256 lines per `read()`; lines at or above `MAX_LINE_BYTES` (512) are rejected and counted in `rejected_lines`; serial reads use a finite timeout (`timeout_seconds`, default 0.2); LSL pulls are capped at `MAX_CHUNK`. | Bounded per call, unbounded across calls. No rate limit on a poll loop. |
| **I**nformation disclosure | A recording file leaks a participant's physiological data. | `write_recording` writes plain CSV with **no** participant identifier column and no metadata header. Replay is local-file only. | **Plain text at rest, unencrypted, no access control.** If a recording identifies a person by filename or context, that is the leak. Covered in `incident-response.md`. |
| **I**nformation disclosure | Device names or paths leak host detail into logs. | Device names default to `<kind>.device`, not to a port path. | Serial port paths and BLE addresses can appear in configuration and error messages. They are host detail, not credentials. |
| **D**enial of service | A missing device dependency crashes instead of degrading. | `DeviceUnavailable` is distinct from `DeviceError`, and `build_all` / `build_reported` tolerate it: unavailable devices are skipped (or reported) rather than aborting a session. | A caller that uses `build()` directly gets the exception. That is the intended behaviour for an explicit request. |
| **S**poofing | A rogue BLE advertiser or LSL stream provides data. | `CS_BLE_ADDRESS` pins a specific device when set; LSL resolves a named stream. `device.hello` declares `kind`, and an unknown kind must be ignored rather than interpreted. | **A blank `CS_BLE_ADDRESS` takes the first advertiser**, which is spoofable by anything in radio range. Pin the address in any deployment where the data matters. |

### 3.4 MQTT and WebSocket transports

**Assets:** A6, A4. **Only the in-process transport exists** (`protocols/transport.py`);
a real broker and a WebSocket binding are planned.

| STRIDE | Threat | Existing mitigation (in code) | Residual risk |
| --- | --- | --- | --- |
| **S**poofing | A client publishes into another session's namespace. | Topic identifiers restricted to `^[A-Za-z0-9._-]{1,64}$` (`validate_identifier`), applied to every session and device id before a topic string is built; `parse_topic` rejects wildcards, trailing levels and wrong level counts. | **The identifier rule prevents namespace escape, not authentication.** MQTT access control is the broker's job and no broker configuration ships here. A shared credential with publish rights on `cs/v1/#` defeats the identifier rule entirely. |
| **T**ampering | A forged `sim.command` alters a run. | Commands are typed and validated (`sim-command.schema.json`, `additionalProperties: false`) and the engine's verb set is three items. | Without per-client authorisation, any publisher on the command topic can issue commands. Topic-level ACLs are required and are operator responsibility. |
| **I**nformation disclosure | Anyone subscribed to `cs/v1/sessions/+/events` sees every session. | `session_wildcard()` exists and is documented as "for operators, not clients". | A helper function cannot enforce who may subscribe. **Use ACLs to deny `+/#` to clients**, or the wildcard helper becomes a tenant-crossing bug. |
| **I**nformation disclosure | A payload exceeds a memory bound. | `MAX_PAYLOAD_BYTES` = 262 144 checked in `validate_envelope`; NDJSON decoder enforces a line cap and **raises** rather than truncating. | Truncating was rejected deliberately: a truncated message that still parses is more dangerous than a rejected one. |
| **D**enial of service | A slow consumer is silently dropped, hiding real gaps. | `InProcessTransport` has a finite queue (default 1024) and **raises** when full rather than dropping. | Refusing is the honest behaviour but it is still an availability failure. A real transport needs a documented backpressure policy; dropping samples silently would be worse. |
| **D**enial of service | A peer sends bytes with no newline to grow a buffer unboundedly. | `NdjsonDecoder.feed` discards the buffer and raises past `max_line_bytes` (1 048 576). | The connection is expected to be closed by the caller on that error; the decoder does not close it. |

### 3.5 Data pipelines (planned, not implemented)

**Assets:** A7, A8.

Root `pipelines/*.yaml` are intended to be **data-pipeline DAG definitions**
executed by `conscious_subconscious/pipelines/runner.py`. Neither the DAG files nor
the runner exist in this repository. They are **not** CI workflows, despite living
in a directory whose name reads like CI configuration.

| STRIDE | Threat | Intended mitigation | Residual risk |
| --- | --- | --- | --- |
| **T**ampering | A pipeline definition injects a shell command or a path traversal. | `PipelineError` exists in `core/errors.py` for "a data pipeline failed to validate or execute", implying validation before execution. | **A YAML DAG that can run arbitrary commands is remote code execution by configuration**, and nothing is implemented to prevent it. Any runner must use a closed set of typed steps with no shell interpolation and no free-form paths. This is the highest-severity open design risk in the project. |
| **S**poofing | A pipeline definition is loaded from an untrusted location. | None specified. | Restrict pipelines to repository-owned files, resolved against a fixed root, with no user-supplied paths. |
| **I**nformation disclosure | A pipeline reads or writes files outside the data directory. | None specified. | Confine to `CS_DATA_DIR` with a resolved-path check (`Path.resolve()` plus a prefix test) before any open. |
| **D**enial of service | A DAG with a cycle or unbounded fan-out. | None specified. | The runner must reject cycles at validation time rather than at execution time. |

### 3.6 Web console (planned, not implemented)

**Assets:** A5 (never here), A6, A12.

`apps/console` (React + TypeScript + Vite) and `apps/site` do not exist in this
repository yet. The protocol schemas already reference
`apps/console/src/api/types.ts` as the TypeScript side of the contract.

| STRIDE | Threat | Intended mitigation | Residual risk |
| --- | --- | --- | --- |
| **S**poofing | The console is served from a domain that is not the API origin. | `CS_ALLOWED_ORIGINS` allow-list, exact-match, never `*` with credentials. | A static site plus a wide-open API is a common misconfiguration. Ship a default that fails closed. |
| **I**nformation disclosure | A built bundle embeds a secret. | **The API key must never be shipped in front-end code.** Vite inlines `VITE_*` variables into the bundle at build time, so a key placed there is public the moment the site is served. | This is the single most likely way this project would leak a credential, and it is a build-time mistake rather than a runtime one. The console should hold no long-lived credential: use a short-lived token or a same-origin proxy. |
| **T**ampering | XSS through rendered payload content. | The console is untrusted-input-consuming by design. | React escapes text by default; `dangerouslySetInnerHTML` must not be used for envelope or payload content. Streamed values should be rendered as numbers and labels only. |
| **I**nformation disclosure | Telemetry, analytics or a CDN leaks session data. | None. The project ships no telemetry. | Do not add analytics to the console without a privacy decision; a heart-rate value in a page view is personal data leaving the operator's control. |
| **D**enial of service | The console opens unbounded WebSocket connections or replays streams. | None. | Client-side rate limiting is not a security control. |

### 3.7 Supply chain and release

**Assets:** A9, A11, A10.

| STRIDE | Threat | Existing mitigation | Residual risk |
| --- | --- | --- | --- |
| **T**ampering | A malicious or typosquatted dependency. | Core has **zero** third-party runtime dependencies. `api`, `devices` and `science` extras are isolated so a finding is attributable to one extra. `pip-audit --strict` runs on the built wheel and on each extra separately (`security.yml`); Dependabot covers pip, both npm workspaces, docker and github-actions. `actions/dependency-review-action` runs on pull requests. | Dependabot and `pip-audit` detect **known** advisories. `pylsl`, `bleak` and `pyserial` have small maintainer bases and bind native code, which is where an unnoticed compromise would be quietest. |
| **S**poofing | A dependency-confusion package is installed instead of the internal one. | No internal package index is used. | Would become relevant if the project ever publishes private packages. |
| **T**ampering | A compromised GitHub Action or workflow run publishes a backdoored artefact. | Actions are pinned to major tags (not SHAs); `permissions:` blocks are minimal per job; PyPI publishing uses OIDC Trusted Publishing with `id-token: write` and no stored long-lived token; container publishing happens **only** on `v*` tags (`push: startsWith(github.ref, 'refs/tags/v')`). | **Major-tag pinning is a real, accepted risk**: a compromised upstream action tag executes in this repository's context. SHA pinning is the stronger control and is not used. Tag-only container publishing limits blast radius but does not eliminate it. |
| **T**ampering | A secret is committed. | `gitleaks` runs in CI over full history and as a pre-commit hook; `detect-private-key` in pre-commit; `.gitignore` excludes `.env`, `*.pem`, `*.key`, `credentials.json`; `Dockerfile` and `.dockerignore` exclude secrets from image layers. | A secret committed and pushed must be **rotated**, not just deleted — history is public and mirrors exist. |
| **I**nformation disclosure | SBOM or provenance reveals internal infrastructure. | `provenance: true` and `sbom: true` on the image build; `tools/gen_sbom.py` is planned. | Not a meaningful risk for a public repository; noted for completeness. |
| **R**epudiation | A published artefact cannot be traced to a commit. | Multi-arch image carries build provenance attestation; releases attach sdist and wheel to a tagged GitHub release; run digests identify simulation results. | PyPI artefacts are not signed beyond whatever the publish action provides. |
| **D**enial of service | A dependency is yanked or an upstream is deleted, breaking installs. | Version lower bounds only (`>=`), no upper pins, no lockfile for Python. | A breaking upstream release can break an install. There is no lockfile; this is a deliberate trade for a library-shaped package and it is worth revisiting if a service is deployed from this repository. |

## 4. The two boundary assets, stated explicitly

### A1 — read-only with respect to the wearer

**The asset:** the property that this software cannot act on a person.

**Why it is an asset and not a limitation:** a simulation project that can drive a
stimulator has a safety case it has not made. Adding "just one" output channel is how
that boundary crosses without anyone deciding to cross it.

**Existing controls:** no write/stimulate method in the base class; `bidirectional`
defaults to `False`; every driver declares capabilities; the pull request checklist
asks for an explicit confirmation; `devices/__init__.py` and
`docs/hardware.md` state the boundary.

**Residual risk:** enforced by convention and review, not by a mechanism. A
`write()` method on a subclass would compile, pass lint, pass tests and ship. The
strongest practical control is a reviewer who knows this is a boundary.

### A2 — this must never become a medical device

**The asset:** the property that this software has no clinical function and makes no
clinical claim.

**Existing controls:** `DISCLAIMER` in `__init__.py` is attached to every
`SimulationResult` and printed by the CLI epilog and report footer; the report's
"what this does not show" section is generated, not optional; the provenance system
makes the unsupported assumption visible in every run; the issue templates require a
confirmation that the report does not request medical capability; the FAQ answers
"isn't this pseudoscience?" directly.

**Residual risk:** the largest one in this document is **not technical**. It is a
person quoting `time_to_50pct_repair_hours` as a prediction about a wound. No code
change prevents that. The mitigations are documentation, the disclaimer travelling
with every artefact, and refusing feature requests that would add clinical framing.
Adding a clinical endpoint, an intervention, a "treatment" mode or a user-facing
"healing score" would be the point at which this asset is lost, and it should be
treated as a security-relevant change rather than a product decision.

## 5. Summary of open items

Ranked by how much they matter, not by effort:

1. **No clinical-claim enforcement beyond documentation.** (A2) Highest
   consequence, lowest technical solvability.
2. **The read-only boundary is a convention, not a mechanism.** (A1)
3. **Pipelines are a speculative arbitrary-code-execution surface.** (3.5) Nothing
   exists, so nothing is exploitable — but the design must be closed before it is
   built.
4. **A shared API key provides no identity, no revocation and no attribution.**
   (3.1) And the rate-limiter weakens as replicas scale up.
5. **Session authorisation is unspecified.** (3.1, 3.2) One key means one tenant
   in practice.
6. **Anything involving front-end secrets** (3.6) is unbuilt, and the failure mode
   — an inlined build-time variable — is easy and permanent.
7. **Actions are pinned to major tags, not SHAs.** (3.7)
8. **No load testing.** Every availability statement in this document is a design
   intent, not a measurement.

## 6. What this document is not

- It is not a penetration test. No dynamic testing has been performed.
- It is not a review by anyone outside the project.
- It is not a compliance artefact. There is no certification, no audit trail and no
  control framework behind it. In particular, nothing here should be read as an
  ISO 27001, SOC 2, HIPAA or medical-device-adjacent statement, because none of
  those applies to this project.
- It does not cover the host, the container runtime, the cluster, the broker or the
  browser.
