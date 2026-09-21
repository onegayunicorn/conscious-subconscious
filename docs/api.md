# API service

**The service layer is not implemented in this repository.**

`conscious_subconscious.services.api` is referenced in three places — the
`__main__:main` entry point documented in `pyproject.toml`, the `CS_API_KEY` /
`CS_HOST` / `CS_PORT` block in `.env.example`, and the container and Kubernetes
manifests — but the package does not exist. This page therefore separates what you
can actually rely on today from what is planned, and marks which is which.

> **Boundary.** The planned service exposes a simulation. It is not a medical
> device and serves no clinical function. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Status

| Item | Status |
| --- | --- |
| FastAPI application | **Not implemented** |
| HTTP endpoints | **Not implemented** |
| WebSocket / streaming transport | **Not implemented** |
| MQTT transport | **Not implemented** |
| Authentication | **Not implemented** in code; the contract is documented below |
| `/healthz`, `/readyz` | **Not implemented**; assumed by the Dockerfile, Compose and Kubernetes probes |
| Interactive command surface | **Implemented** in the engine (`SimulationEngine.command`) |
| Wire contract (envelope, codec, topics, JSON-RPC) | **Implemented** (`protocols/`) |
| Session manager | **Not implemented** |

Installing the `api` extra gets you `fastapi`, `uvicorn` and `pydantic` and
nothing to serve. The simulation itself is fully usable today through
[`cs-sim`](cli.md).

## What exists today that constrains the service

Even though the HTTP layer is absent, the important parts of the contract are
already fixed in code, and a future service has to honour them.

### The interactive command surface

`SimulationEngine.command()` is implemented and deliberately narrow:

| Command | Effect |
| --- | --- |
| `focus` | Engage attention on a target (defaults to the tissue name). |
| `release` | Withdraw attention. |
| `set_policy` | Change the focus policy for the remainder of the run. Must be one of `never`, `always`, `intermittent`. |

Anything else raises `ConfigurationError`. **There is no command that sets tissue
integrity directly.** That is not an omission: nothing may bypass the repair rule,
not a module, not an API caller, not an operator. A service that exposed such a
command would be a different project.

`SimulationEngine.snapshot()` returns the current state without advancing time
(`t_hours`, `steps`, `finished`, scenario, seed, focus policy, modules, tissue,
mediators, conscious state, last rates). `step()` advances exactly one step and
returns a compact snapshot. A service that streams `sim.tick` needs no new engine
API.

### The wire contract

Everything a service would put on the wire is already specified and implemented in
`protocols/`:

- `Envelope` with `v`, `id`, `ts`, `type`, `source`, optional `session`, `payload`
- `MessageType`: `device.hello`, `device.state`, `stream.sample`, `sim.tick`,
  `sim.command`, `session.start`, `session.stop`, `heartbeat`, `error`, `jsonrpc`
- NDJSON framing with a maximum line length
- JSON-RPC 2.0 builders, validators and an application error-code range
- MQTT topic helpers with identifier validation
- JSON Schema files in `protocols/schemas/` as the tie-breaker between the Python
  and TypeScript implementations

See [protocol.md](protocol.md) for the full description.

### Configuration the service reads

From `.env.example`. These names are fixed by documentation and by the deployment
manifests, so a service implementation has to use them.

| Variable | Purpose | Default |
| --- | --- | --- |
| `CS_API_KEY` | Shared secret required in the `X-API-Key` header for every `/v1` route. | empty |
| `CS_HOST` | Bind address. Keep `127.0.0.1` for local work. | `127.0.0.1` |
| `CS_PORT` | Bind port. | `8080` |
| `CS_ALLOWED_ORIGINS` | Comma-separated CORS allow-list. Never `*` with credentials. | `http://localhost:5173,http://127.0.0.1:5173` |
| `CS_RATE_LIMIT_PER_MINUTE` | Requests per minute per client, enforced by an in-process token bucket. | `120` |
| `CS_MAX_BODY_BYTES` | Maximum accepted request body. | `1048576` |
| `CS_LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR`. | `INFO` |

The documented behaviour when `CS_API_KEY` is empty is deliberate and should be
preserved by any implementation: the service logs a loud warning and **refuses to
bind to a non-loopback interface**. An unauthenticated simulation service should
not be reachable off-box, and the refusal is the enforcement mechanism rather than
a comment in a README.

### Health endpoints

`/healthz` (liveness) and `/readyz` (readiness) are already baked into:

- the image's `HEALTHCHECK` (`deploy/docker/Dockerfile`)
- the Compose healthcheck (`deploy/docker/docker-compose.yml`)
- the Kubernetes `livenessProbe`, `readinessProbe` and `startupProbe`
  (`deploy/k8s/deployment.yaml`)
- the ingress path rules (`deploy/k8s/ingress.yaml`)

They must be served unauthenticated (a probe cannot hold an API key), must not
require the data directory (a liveness probe that depends on a volume turns a
storage problem into a restart loop), and must return HTTP 200 when healthy.
Neither endpoint may expose simulation state.

## Planned endpoints

**None of the following exists.** They are listed so that the intended surface is
reviewable and so that the JSON-RPC method names in `protocols/jsonrpc.py` have a
documented home. Treat every row as a proposal, not a description.

| Method | Path | Body | Purpose |
| --- | --- | --- | --- |
| `POST` | `/v1/sessions` | scenario config | Create a session; returns a session id. |
| `GET` | `/v1/sessions/{id}` | — | Session state snapshot. |
| `DELETE` | `/v1/sessions/{id}` | — | End a session and release its engine. |
| `POST` | `/v1/sessions/{id}/step` | `{"steps": n}` | Advance `n` steps. |
| `POST` | `/v1/sessions/{id}/run` | — | Run to the configured horizon. |
| `POST` | `/v1/sessions/{id}/commands` | `sim.command` payload | `focus`, `release` or `set_policy`. |
| `GET` | `/v1/sessions/{id}/state` | — | Equivalent of `SimulationEngine.snapshot()`. |
| `GET` | `/v1/scenarios` | — | The built-in scenario list. |
| `GET` | `/v1/parameters` | `?unsupported=true` | Parameters with provenance. |
| `GET` | `/v1/modules` | — | Registered modules. |
| `WS` | `/v1/sessions/{id}/stream` | — | `sim.tick` envelopes as the run advances. |
| `GET` | `/healthz` | — | Liveness. Unauthenticated. |
| `GET` | `/readyz` | — | Readiness. Unauthenticated. |

Conventions those endpoints are expected to follow, all inherited from the code
that already exists:

- **Authentication.** `X-API-Key` on every `/v1` route, compared against
  `CS_API_KEY`. Failure is JSON-RPC `UNAUTHORISED` (`-32005`) or an HTTP 401.
- **Rate limiting.** In-process token bucket at `CS_RATE_LIMIT_PER_MINUTE`, with
  `RATE_LIMITED` (`-32004`) when exhausted. An in-process bucket is per-worker, so
  a multi-replica deployment multiplies the effective limit unless it is moved to
  a shared store — an operator decision, not a hidden one.
- **Body size.** `CS_MAX_BODY_BYTES`, rejected before parsing.
- **CORS.** Exactly `CS_ALLOWED_ORIGINS`. Never `*` with credentials.
- **Errors.** JSON-RPC application codes where the caller is a machine, with the
  same shape as a successful message; no stack traces and no file paths in a
  response body.
- **No secrets in responses.** `CS_API_KEY` is never echoed, logged or included in
  an error payload.

## What a session manager would have to get right

Not implemented anywhere yet, and worth stating because it is where such services
usually go wrong:

- **Session ids must satisfy the same character class as MQTT topics**
  (`^[A-Za-z0-9._-]{1,64}$`). A session id is used as a topic level, so an
  identifier containing `/`, `+` or `#` lets one tenant publish into another's
  namespace. `validate_identifier` exists for exactly this.
- **Bounded session count and bounded lifetime.** Each session holds an engine,
  a sample history and an event history. The event bus alone keeps up to 20 000
  events per run (`EventBus(history_limit=20_000)`), so an unbounded number of
  long-lived sessions is a memory exhaustion bug that looks like a feature.
- **A finished run is finished.** `SimulationEngine.step()` raises once a run has
  completed; the service must surface that as `SIMULATION_FINISHED` (`-32002`)
  rather than constructing a replacement engine behind the caller's back.
- **Single writer per session.** Two concurrent `step` calls on one engine produce
  an order-dependent result. Determinism is a property of a run, not of a
  concurrent access pattern.

## What has not been verified

- Nothing here has been load tested. There are no throughput or latency figures for
  this project, and none are claimed.
- No implementation of these endpoints has been written, reviewed or run.
- The authentication, rate-limiting and body-size behaviour described above is
  specified in `.env.example` and in the deployment configuration; none of it is
  enforced anywhere yet because there is no code to enforce it in.
- The health endpoints have never returned a response, because there is no server.

The threat model for the planned service — including what each of the above
mitigations is supposed to achieve and what remains — is in
`security/threat-model.md`.
