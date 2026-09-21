# Security policy

## Reporting a vulnerability

**Please do not open a public issue for a security problem.**

Use GitHub's private vulnerability reporting on this repository:

**https://github.com/onegayunicorn/conscious-subconscious/security/advisories/new**

If that form is unavailable to you, open an issue that says only *"I need a private
channel to report a security issue"* with no technical detail, and a maintainer will
open one. Do not put the details in the issue.

### There is no security email address

**No dedicated security contact email is configured for this project, and this file
does not invent one.** GitHub private vulnerability reporting is the only
configured channel.

Do not send security reports to any address you may find associated with the
maintainer in another context. If you need an email route and none exists, the
channel above is the correct fallback.

### What to include

The more of this you can provide, the faster it can be assessed:

- a description of the issue and its impact;
- the version (`cs-sim version`), and the commit or tag if you have it;
- the component: `core`, `model`, `modules`, `protocols`, `devices`, `sim`, or a
  deployment path (`docker`, `k8s`, `systemd`);
- reproduction steps, ideally a minimal one;
- whether the issue is reachable without authentication, and whether it needs an
  unusual configuration;
- any suggested fix, if you have one.

**Do not include real credentials, real sensor recordings, or personal data.** If
you must demonstrate something involving such data, describe its shape rather than
pasting it.

### What to expect

This is a project maintained by one person in their own time.

| Stage | Target |
| --- | --- |
| Acknowledgement | Best effort, typically within a week |
| Initial assessment | Best effort, typically within two weeks |
| Fix or mitigation | Depends on severity; critical issues are prioritised |
| Public disclosure | Coordinated, after a fix is available or after 90 days, whichever comes first |

There is no 24-hour response commitment and no bug bounty. If you need a guaranteed
response time, this project cannot provide one and saying otherwise would be a
false promise.

Credit will be given in the advisory and in `CHANGELOG.md` unless you ask to remain
anonymous.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Yes — the current release line |
| Anything earlier | No such version exists |

The project is at `0.1.0` and there is exactly one release line. There are no
backported security fixes, no LTS branch, and no maintenance window for older
versions. The practical advice is to track the latest tag.

Supported interpreter versions follow the CI matrix: **Python 3.10, 3.11, 3.12 and
3.13**. See `deploy/platforms.yaml` for the OS and architecture matrix. A
vulnerability that only affects an interpreter outside that range is out of scope
for a fix, though a report is still welcome.

## Scope

### In scope

- The Python package under `src/conscious_subconscious/` — the engine, model,
  modules, protocol layer, device adapters, CLI and i18n loader.
- The protocol layer specifically: envelope validation, the NDJSON codec, JSON-RPC
  handling, topic and identifier validation.
- The device adapters, including the parsing of untrusted serial and BLE input.
- The deployment artefacts in `deploy/`: the Dockerfile, the Compose file, the
  Kubernetes manifests and the systemd units.
- The CI and release workflows in `.github/workflows/`, including anything that
  could lead to publishing a compromised artefact.
- Documentation that could cause harm if followed — a doc that instructs someone to
  deploy something insecurely is a legitimate finding.

### Out of scope

- **Anything that is not implemented.** The API service
  (`conscious_subconscious.services.api`), the session manager, the data-pipeline
  runner, the web workspaces (`apps/`) and the firmware (`hardware/firmware/`) do
  not exist in this repository. A report about them is a report about absent code
  and will be closed as out of scope. `docs/api.md` marks exactly what is planned.
- **Deployments run by other people.** This project runs no public instance. If you
  found a problem in someone's deployment, report it to them. Generalisable
  misconfigurations in `deploy/` are still in scope.
- **The model being wrong, overclaimed or medically meaningless.** That is not a
  security vulnerability; it is the subject of the documentation. See
  `DISCLAIMER.md` and `research/evidence-grading.md`.
- **Findings that require an already-compromised host**, a malicious operator, or
  physical access to the machine running the service.
- **Dependency advisories with no reachable path** in this project. Forward them
  anyway if you are unsure — they are useful — but they are not treated as
  vulnerabilities in this codebase.
- **Automated scanner output with no analysis.** A wall of tool output with no
  statement of impact will be closed with a pointer back to this file.
- **Missing hardening that is already documented as operator responsibility** in
  `security/hardening-checklist.md`. If you disagree with that classification, say
  so — a disagreement about scope is a legitimate discussion, and the checklist can
  change.

## The boundary that matters most

No shipped device adapter has a write, send, stimulate or actuate method, and
`DeviceCapabilities.bidirectional` defaults to `False`. **There is no path from
this software to a human body.**

If you find any way — direct or indirect, in code, configuration, protocol or a
deployment path — for this software to influence a person's physiology, treat it as
**critical** and report it privately. That boundary is a deliberate safety property
of the project, and a bug that crosses it is the most serious kind of bug this
project can have.

Related, and also treated as a boundary rather than a feature request: nothing in
this project may acquire a clinical function or a clinical claim. A change that
would make it a medical device is a change to what the project is.

## Security posture, honestly

What the project does and does not do. The full reasoning is in
`security/threat-model.md`; the checklist is `security/hardening-checklist.md`.

**Present in this repository:**

- core package with **zero third-party runtime dependencies**
- optional dependencies isolated into `api`, `devices`, `science` extras and
  imported inside the drivers that need them
- API-key authentication, CORS allow-list, per-client rate limiting and a
  body-size cap **specified** in `.env.example` — but not implemented, because the
  service is not written
- bounded input at every layer: payload, NDJSON line, serial line, drain count, LSL
  chunk, event history, virtual-clock steps
- topic and identifier validation against `^[A-Za-z0-9._-]{1,64}$`
- container running as non-root UID/GID 10001, multi-stage build with no toolchain
  in the final image, `HEALTHCHECK` on `/healthz`
- Kubernetes manifests with `runAsNonRoot`, `readOnlyRootFilesystem`, all
  capabilities dropped, a seccomp profile, no service account token, and a
  default-deny NetworkPolicy in both directions
- hardened systemd units with no network address family available
- `gitleaks` on full history, `pip-audit` on the wheel and on each extra,
  dependency review, CodeQL, Dependabot
- OIDC Trusted Publishing to PyPI (no stored API token), tag-only container
  publishing, and a clean-venv install check before a release is published

**Not present, and not claimed:**

- no external audit, no penetration test, no certification
- no lockfile for Python dependencies (deliberate; see
  `security/dependency-policy.md`)
- GitHub Actions pinned to major tags rather than commit SHAs
- no load testing of any kind
- no monitoring, alerting, intrusion detection or log aggregation
- no SBOM for the Python distributions yet (the container image has one)
- no dedicated security contact email, as stated above

Reports that help close any of those gaps are welcome, and so are reports that
show one of them matters more than it looks.
