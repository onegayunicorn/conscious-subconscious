# Deployment

Four ways to run this project, in increasing order of ceremony:

| Path | What it runs | Directory |
| --- | --- | --- |
| Local virtualenv | `cs-sim` on the interpreter of your choice | — |
| Docker / Compose | the service image, with a SQLite data volume | `docker/` |
| Kubernetes | the same image as a Deployment, Service, Ingress and HPA | `k8s/` |
| systemd | `cs-sim` as a periodic, hardened batch job | `systemd/` |

The supported build matrix — which OS/architecture/Python combinations are
`supported`, `best-effort` or `unsupported`, and what has actually been tested —
is `platforms.yaml` in this directory.

Read the last section of this file before treating any of the above as
production-ready. Most of it has not been verified.

## Boundary

Every path below deploys a **simulation**. Nothing here is a medical device,
nothing here produces clinical information, and nothing here should be used to
make a decision about a human body. See `DISCLAIMER.md` in the repository root
for the canonical wording.

## 1. Local (no container)

```bash
make install-dev                     # core + api + dev extras into .venv
.venv/bin/cs-sim run --scenario focused --report
```

Or, without a virtualenv:

```bash
PYTHONPATH=src python3 -m conscious_subconscious.sim.cli run --scenario baseline
```

## 2. Docker and Compose

The build context is the **repository root**, because the image needs
`pyproject.toml`, `src/` and `i18n/`:

```bash
docker build -f deploy/docker/Dockerfile -t conscious-subconscious:0.1.0 .
# or: make docker
```

Compose:

```bash
docker compose -f deploy/docker/docker-compose.yml up --build
# or: make docker-compose-up
```

### Configuration

There is no committed `.env`. `docker-compose.yml` references `../../.env` with
`required: false`, so the stack starts with the image's safe defaults when the
file is absent and nothing fails. If you want to override anything, copy the
template and edit the copy:

```bash
cp .env.example .env      # .env is git-ignored; never commit it
```

`.env.example` documents every variable: `CS_API_KEY`, `CS_HOST`, `CS_PORT`,
`CS_ALLOWED_ORIGINS`, `CS_RATE_LIMIT_PER_MINUTE`, `CS_MAX_BODY_BYTES`,
`CS_LOG_LEVEL`, the three simulation defaults (`CS_DEFAULT_SEED`,
`CS_DEFAULT_DT_HOURS`, `CS_DEFAULT_HORIZON_HOURS`) and the three device
variables (`CS_SERIAL_PORT`, `CS_SERIAL_BAUD`, `CS_BLE_ADDRESS`,
`CS_LSL_STREAM_NAME`).

`CS_API_KEY` empty is a deliberate local-development posture: the service logs a
warning and refuses to bind to a non-loopback interface. Do not work around
that by binding to `0.0.0.0` without a key.

### Known issues with this image as written

Both are honest gaps rather than oversights:

1. **`COPY i18n ./i18n` will fail today.** The `i18n/locales/` directory is
   referenced by `tools/check_locales.py`, the `locale-parity` pre-commit hook
   and `CS_LOCALES_DIR`, but it does not exist in the repository yet. Until it
   does, the image cannot be built. Creating an empty `i18n/locales/` with a
   single `en.json` is enough to unblock it.
2. **`.dockerignore` is in the wrong place to take effect.** Docker reads
   `.dockerignore` from the build-context root — the repository root here — so
   `deploy/docker/.dockerignore` is documentation of intent rather than an active
   exclusion list. The exclusions it lists need to be mirrored into a root
   `.dockerignore` before a build will actually skip `node_modules`, `out/` and
   `runs/`. Do that as a deliberate change with a review, not as a drive-by.

### Volume

`cs-data` is a named local volume mounted at `/data`, matching `CS_DATA_DIR`.
It holds the SQLite file the service will use once the service exists. It is not
backed up, not replicated and not encrypted by this project.

## 3. Kubernetes

```bash
# Validate the raw manifests (what `make k8s-validate` does):
kubectl apply --dry-run=client -f deploy/k8s/ -R

# Validate the kustomize composition:
kubectl kustomize deploy/k8s/ | kubectl apply --dry-run=client -f -
```

Apply in dependency order, or let kustomize handle it:

```bash
kubectl apply -k deploy/k8s/
```

`kustomization.yaml` lists everything except `secret.example.yaml`, which is
placeholders only and must never be applied. Create the real Secret out of band:

```bash
kubectl -n conscious-subconscious create secret generic \
  conscious-subconscious-secrets \
  --from-literal=CS_API_KEY="$(openssl rand -hex 32)"
```

What the manifests already do:

- run as UID/GID 10001, `runAsNonRoot: true`, `readOnlyRootFilesystem: true`,
  all capabilities dropped, `seccompProfile: RuntimeDefault`
- liveness on `/healthz`, readiness on `/readyz`, plus a startup probe
- NetworkPolicy: default-deny in both directions, with ingress allowed only from
  the `ingress-nginx` namespace and from within the namespace itself, and egress
  allowed only to DNS
- no service account token mounted (`automountServiceAccountToken: false`)

What they do **not** do: no PodSecurity admission labels, no resource quotas, no
service mesh, no policy engine, no PodDisruptionBudget, and no persistent storage
(`/data` is an `emptyDir`, so a pod restart loses it). All of that is operator
responsibility.

## 4. systemd

See `systemd/README.md` for the full procedure. In short: a `oneshot` service
that runs `cs-sim run --scenario week-long --report` plus a sensitivity ranking,
driven by a daily timer, under a hardened unit with no network access at all.

## What has NOT been verified

Stated explicitly, because a deployment guide that implies testing it did not do
is worse than no deployment guide:

- **No load testing has been done.** No throughput, latency, concurrency or
  soak numbers exist for this project. The HPA thresholds in
  `k8s/hpa.yaml` are conventional starting values, not measurements.
- **The Kubernetes manifests have never been applied to a live cluster.** They
  are written against the documented APIs and dry-run validated at most.
- **The systemd units have never been started on a real host**, and
  `systemd-analyze security` has not been run against them.
- **The service image has never been started successfully**, because the service
  it starts does not exist yet. The image builds and `cs-sim` inside it works.
- **The `linux/arm64` image has been cross-built but never executed.**
- **No backup, restore, migration or disaster-recovery procedure exists**, because
  there is no data worth that procedure yet. If you deploy this and accumulate a
  data directory you care about, you own that problem.
- **No TLS certificates, DNS names or real hostnames are configured.** Every host
  in these manifests is `.example.invalid`, which cannot resolve.
- **No monitoring, alerting or log aggregation is configured.**
- **No security review by anyone outside this project has happened.** The threat
  model in `security/threat-model.md` is a self-assessment.
- **Payments, accounts, subscriptions and multi-tenancy do not exist** and no part
  of this deployment introduces them.
