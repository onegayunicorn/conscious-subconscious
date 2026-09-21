# Deployment

Four paths, in increasing order of ceremony. The operationally relevant details —
including what has **not** been verified — live in `deploy/README.md`, and the
supported OS/architecture/interpreter matrix is `deploy/platforms.yaml`. This page
is the summary.

> **Boundary.** Every path below deploys a simulation. None of them produces a
> medical device or clinical information. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Configuration variables

From `.env.example` at the repository root. Copy the template to `.env` for local
use; `.env` is git-ignored and **no** real value is committed anywhere in this
repository. Every variable has a safe default in code, so the file documents the
knobs rather than bootstrapping them.

### API service

| Variable | Default | Notes |
| --- | --- | --- |
| `CS_API_KEY` | empty | Shared secret required in `X-API-Key` for every `/v1` route. Empty means the service logs a loud warning and refuses to bind to a non-loopback interface. |
| `CS_HOST` | `127.0.0.1` | Bind address. Keep loopback for local work; override to `0.0.0.0` only inside a container. |
| `CS_PORT` | `8080` | Bind port. |
| `CS_ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated CORS allow-list. Never `*` with credentials. |
| `CS_RATE_LIMIT_PER_MINUTE` | `120` | Requests per minute per client, enforced by an in-process token bucket. |
| `CS_MAX_BODY_BYTES` | `1048576` | Maximum accepted request body, in bytes. |
| `CS_LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR`. |

The whole API block is currently inert: the service layer is not implemented. See
[api.md](api.md).

### Simulation defaults

| Variable | Default | Notes |
| --- | --- | --- |
| `CS_DEFAULT_SEED` | `20260921` | Root seed for every run. |
| `CS_DEFAULT_DT_HOURS` | `0.05` | Time step. |
| `CS_DEFAULT_HORIZON_HOURS` | `72` | Run length. |

### Devices (all optional)

| Variable | Default | Notes |
| --- | --- | --- |
| `CS_SERIAL_PORT` | empty | e.g. `/dev/ttyUSB0`, `COM3`. Empty means the serial adapter is unavailable. |
| `CS_SERIAL_BAUD` | `115200` | Serial baud rate. |
| `CS_BLE_ADDRESS` | empty | Leave blank to scan and take the first advertiser. |
| `CS_LSL_STREAM_NAME` | `conscious-subconscious` | LSL stream name to resolve. |

### Set by the deployment, not by you

| Variable | Value | Where |
| --- | --- | --- |
| `CS_LOCALES_DIR` | `/app/i18n/locales` | Dockerfile and Kubernetes ConfigMap. |
| `CS_DATA_DIR` | `/data` | Dockerfile and Kubernetes ConfigMap. |

## 1. Local

```bash
make install-dev          # core + api + dev extras into .venv
.venv/bin/cs-sim run --scenario focused --report

# or, no install:
PYTHONPATH=src python3 -m conscious_subconscious.sim.cli compare
```

The core has no third-party runtime dependencies, so `python3` alone is enough for
everything in [cli.md](cli.md). The `devices` and `science` extras are opt-in:

```bash
make install-devices      # pyserial, pylsl, bleak
make install-science      # numpy, matplotlib
```

## 2. Docker and Compose

The build context is the **repository root**, because the image needs
`pyproject.toml`, `src/` and `i18n/`:

```bash
docker build -f deploy/docker/Dockerfile -t conscious-subconscious:0.1.0 .
# or: make docker
```

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
# or: make docker-compose-up
```

What the image does:

- multi-stage, so the compiler and build tooling stay in the builder stage and are
  absent from the final image
- `python:3.12-slim` base, Python minor version pinned
- installs `.[api]`
- runs as UID/GID **10001**, non-root, with a `HEALTHCHECK` on `/healthz` that uses
  the standard library rather than adding `curl` to the image
- `COPY i18n/` with `CS_LOCALES_DIR=/app/i18n/locales`, so translations are mounted
  or copied as data rather than baked into code

Compose adds a named volume `cs-data` mounted at `/data` (matching `CS_DATA_DIR`),
a healthcheck with explicit timing, `no-new-privileges`, and a host port bound to
`127.0.0.1` only.

`env_file` points at `../../.env` with `required: false`, which is what **fails
safely when `.env` is absent**: Compose skips the file, the image's own defaults
apply, and `CS_API_KEY` stays empty so the service keeps its refuse-to-bind-off-box
posture. Never replace that with a committed `.env`.

Two known gaps in this path, stated plainly in `deploy/README.md`: `COPY i18n
./i18n` fails because `i18n/locales/` does not exist in the repository yet, and
`deploy/docker/.dockerignore` is not consulted by the daemon because Docker reads
`.dockerignore` from the build-context root.

## 3. Kubernetes

```bash
kubectl apply --dry-run=client -f deploy/k8s/ -R      # raw manifests (make k8s-validate)
kubectl kustomize deploy/k8s/ | kubectl apply --dry-run=client -f -   # composed
kubectl apply -k deploy/k8s/                          # apply
```

`deploy/k8s/` contains a namespace, a ConfigMap, an example Secret, a Deployment, a
Service, an HPA, a NetworkPolicy, an Ingress and a `kustomization.yaml`.

Already enforced by the manifests:

| Control | Where |
| --- | --- |
| Non-root: UID/GID 10001, `runAsNonRoot: true` | Deployment pod and container `securityContext` |
| `readOnlyRootFilesystem: true`, with `emptyDir` mounts for `/data` and `/tmp` | Deployment |
| All capabilities dropped, `allowPrivilegeEscalation: false`, `seccompProfile: RuntimeDefault` | Deployment |
| Liveness on `/healthz`, readiness on `/readyz`, plus a startup probe | Deployment |
| Default-deny ingress **and** egress; ingress only from the `ingress-nginx` namespace and the same namespace; egress only to DNS | NetworkPolicy |
| `automountServiceAccountToken: false` | Deployment |
| Resource requests and limits | Deployment |

`secret.example.yaml` contains placeholders only and is **not** listed in
`kustomization.yaml`. Create the real Secret out of band:

```bash
kubectl -n conscious-subconscious create secret generic \
  conscious-subconscious-secrets \
  --from-literal=CS_API_KEY="$(openssl rand -hex 32)"
```

Not provided, and therefore operator responsibility: PodSecurity admission labels,
resource quotas, a PodDisruptionBudget, persistent storage (`/data` is an
`emptyDir`, so a pod restart loses it), TLS certificates, DNS names, monitoring and
alerting.

## 4. systemd

A hardened **oneshot** unit driven by a daily timer: it runs `cs-sim run --scenario
week-long --report` and then a one-factor sensitivity ranking, writes both to the
state directory, and exits. It has no network address family available
(`RestrictAddressFamilies=AF_UNIX`), `ProtectSystem=strict` with a single
`ReadWritePaths` entry, `NoNewPrivileges`, an empty `CapabilityBoundingSet` and a
system-call allow-list.

Full procedure, including the service account to create and the paths you must
edit, is in `deploy/systemd/README.md`.

## Post-deploy checks

```bash
cs-sim version                       # the wheel installed and its entry point runs
cs-sim run --scenario baseline       # a run completes and prints a digest
cs-sim compare                       # the three-scenario comparison renders
curl -fsS http://127.0.0.1:8080/healthz   # only once the service exists
```

The release workflow performs the first three inside a clean virtualenv before
publishing anything, because a wheel that installs but cannot run its entry point
is a broken release.

## What has not been verified

Repeat of the honest list, because a deployment guide that implies testing it did
not do is worse than no guide:

- **No load testing has been performed.** No throughput, latency, concurrency or
  soak numbers exist for this project.
- **The Kubernetes manifests have never been applied to a live cluster.**
- **The systemd units have never been started on a real host**, and
  `systemd-analyze security` has not been run against them.
- **The service image has never started successfully**, because the service it
  starts does not exist. `cs-sim` inside the image does work.
- **The `linux/arm64` image is cross-built under QEMU and has never been executed.**
- **No backup, restore or migration procedure exists**, because there is no data
  worth one yet. If you accumulate a data directory you care about, you own that.
- **Every hostname in the manifests is `.example.invalid`** and cannot resolve.
- **No monitoring, alerting or log aggregation is configured.**
- **No external security review has happened.** `security/threat-model.md` is a
  self-assessment.
- **Payments, accounts and multi-tenancy do not exist**, and no deployment path
  introduces them.
