# Protocol

One envelope, one codec, one topic scheme, one version string — so a bug in
framing is found once rather than once per transport. Everything in
`src/conscious_subconscious/protocols/` is a pure function over dictionaries; no
module in that package opens a socket, so the whole wire contract is testable
without a network, a broker or an event loop.

> **Boundary.** This is the wire format for a simulation service. Messages carry
> simulation state and sensor readings; none of them is a clinical measurement and
> none of them is medical advice. See
> [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## Source of truth

The JSON Schema files in `protocols/schemas/` define the contract. The Python
implementation and the TypeScript consumer are both derived from them; when the two
disagree, **the schema is the tie-breaker**.

| Schema | Covers |
| --- | --- |
| `envelope.schema.json` | The wrapper applied to every message on every transport. |
| `device-hello.schema.json` | `device.hello` payloads. |
| `stream-sample.schema.json` | `stream.sample` payloads (one sensor reading). |
| `sim-tick.schema.json` | `sim.tick` payloads (one simulation step, streamed). |
| `sim-command.schema.json` | `sim.command` payloads (control). |

All five use JSON Schema draft 2020-12 and set `additionalProperties: false`. That
is deliberate: a protocol that silently ignores fields it does not understand will
one day be handed a field it *should* have understood, and will do the wrong thing
quietly instead of loudly.

## Envelope

Every message on every transport is wrapped in `Envelope`
(`protocols/envelope.py`). Fields, required unless noted:

| Field | Type | Notes |
| --- | --- | --- |
| `v` | string | Protocol version. Currently `1.0.0`. Must equal the receiver's version exactly. |
| `id` | string | Unique message id, 1–128 chars. Used for de-duplication and to correlate JSON-RPC replies. |
| `ts` | string | RFC 3339 / ISO-8601 timestamp **with an explicit UTC offset**. Wall-clock time, not simulation time. |
| `type` | string | One of the message types below. Unknown types are rejected. |
| `source` | string | Producing component, 1–128 chars, e.g. `engine` or `device.heart-rate`. |
| `session` | string | *Optional.* Session scope. Same character class as MQTT topics: `^[A-Za-z0-9._-]{1,64}$`. |
| `payload` | object | Message-type-specific body. Capped at **262 144** serialised bytes. |

`validate_envelope()` returns **every** problem it found, not just the first, so an
integrator sees the whole list at once instead of fixing one typo per round trip.
`Envelope.from_dict` / `from_json` reject a message that fails validation; the
dataclass constructor validates in `__post_init__`, so an invalid envelope cannot
exist even in memory.

Hard ceilings, all enforced in `envelope.py`:

| Limit | Value | Why |
| --- | ---: | --- |
| `MAX_PAYLOAD_BYTES` | 262 144 | A peer sending a 100 MB payload is a denial of service, not a chatty sensor. |
| `MAX_ID_LENGTH` | 128 | Bounded identifier. |
| `MAX_SOURCE_LENGTH` | 128 | Bounded identifier. |
| `DEFAULT_MAX_LINE_BYTES` | 1 048 576 | NDJSON framing ceiling (below). |

## Message types

`protocols/envelope.py::MessageType`. This set is closed: an unknown `type` is a
validation error, not something to ignore.

| Type | Direction | Payload schema |
| --- | --- | --- |
| `device.hello` | device → consumer | `device-hello.schema.json` — announces channels so a consumer never hard-codes driver knowledge. |
| `device.state` | device → consumer | Unschematised in v1.0.0. |
| `stream.sample` | device → consumer | `stream-sample.schema.json` — one reading, in the channel's own unit. |
| `sim.tick` | service → consumer | `sim-tick.schema.json` — one simulation step. |
| `sim.command` | consumer → service | `sim-command.schema.json` — control. |
| `session.start` / `session.stop` | consumer → service | Unschematised in v1.0.0. |
| `heartbeat` | either | Unschematised in v1.0.0. |
| `error` | either | Unschematised in v1.0.0. |
| `jsonrpc` | either | Payload is validated as JSON-RPC 2.0 (below). |

Two payload rules worth noting because they are honesty rules, not plumbing:

- **`sim-tick` separates `integrity` from `perceived_progress`.** Actual and felt
  progress are different quantities and the model never conflates them.
- **`sim-command` has no command that sets tissue integrity.** The enum is
  `focus`, `release`, `set_policy`, `step`, `run`, `snapshot`. Nothing bypasses the
  repair rule — not even an operator.
- **`stream-sample` carries `quality`** (`ok` / `suspect` / `invalid`) and
  `t_seconds`, which is *device* time. Device time is not simulation time and the
  two are never mixed.

## NDJSON framing

`protocols/codec.py`. Transport framing is newline-delimited JSON: one message per
line, UTF-8, terminated by `\n`.

Chosen because it is debuggable with `cat`, trivially streamable, and has no
length-prefix parsing bugs. It has one classic failure mode — a peer that never
sends a newline grows an unbounded buffer — which is why `NdjsonDecoder` enforces
`max_line_bytes` (default 1 048 576) and **raises** rather than truncating. A
truncated message that still parses is far more dangerous than a rejected one.

```text
encode(msg)  ->  b'{"id":"...","payload":{...},"source":"...","ts":"...","type":"...","v":"1.0.0"}\n'
decode(line) ->  dict
NdjsonDecoder.feed(chunk) -> [dict, ...]   # whole messages only
```

`encode` sorts keys and refuses to emit a body containing a raw newline, which
would break framing. Blank lines are skipped by the decoder; a non-object line is
an error.

## JSON-RPC 2.0 control

`protocols/jsonrpc.py`. Control is separated from streaming on purpose: a command
is request/response and must be answerable ("did the focus command apply?"), while
a sample is fire-and-forget. Mixing the two makes both harder to reason about.

Messages are carried in an envelope with `type: "jsonrpc"`, and
`validate_jsonrpc` runs as part of envelope validation.

Standard codes plus an application range (`-32000..-32099`):

| Code | Name | Meaning here |
| ---: | --- | --- |
| −32700 | `PARSE_ERROR` | Body was not valid JSON. |
| −32600 | `INVALID_REQUEST` | Structurally not a JSON-RPC request or response. |
| −32601 | `METHOD_NOT_FOUND` | Unknown method. |
| −32602 | `INVALID_PARAMS` | Parameters failed validation. |
| −32603 | `INTERNAL_ERROR` | Unexpected server-side failure. |
| −32001 | `SESSION_NOT_FOUND` | No such session id. |
| −32002 | `SIMULATION_FINISHED` | Command applied to a run that has already finished. |
| −32003 | `DEVICE_UNAVAILABLE` | Driver cannot run here (missing package, port or peer). |
| −32004 | `RATE_LIMITED` | Token bucket exhausted. |
| −32005 | `UNAUTHORISED` | Missing or wrong `X-API-Key`. |

Structural rules enforced: a response may not carry both `result` and `error`; a
response must carry an `id` (use `null` for "unknown request"); a request may not
also be a response; `id` must be a string, an integer or `null` — never a boolean;
`error.code` must be an integer and `error.message` a non-empty string.

Builders: `request()`, `notification()` (a request with no `id`), `response()`,
`error()`. Predicates: `is_request()`, `is_response()`, `is_error()`.

## MQTT topics

`protocols/topics.py`. One place decides what a topic looks like, so a producer and
a consumer cannot disagree about it.

```text
cs/v1/sessions/{session}/events
cs/v1/sessions/{session}/commands
cs/v1/sessions/{session}/devices/{device}/stream
cs/v1/sessions/{session}/devices/{device}/state
cs/v1/sessions/{session}/devices/{device}/hello
cs/v1/sessions/{session}/devices/{device}/command
```

Wildcards, for subscribers only:

```text
cs/v1/sessions/{session}/devices/+/stream     # every device's stream in one session
cs/v1/sessions/+/events                       # every session's events (operators, not clients)
```

**Identifiers are restricted to `^[A-Za-z0-9._-]{1,64}$`.** MQTT level separators
are `/` and the wildcards `+` and `#` are meaningful, so an identifier containing
either would let a peer publish into another session's namespace. `+/#`, `/`,
empty segments and over-long identifiers are all rejected by
`validate_identifier` before a topic string is ever built. That is a small thing
that turns into a large thing.

`parse_topic()` accepts only concrete topics (no wildcards) and rejects trailing
levels, unknown segments and wrong level counts. Device topics must have exactly
seven levels.

## Versioning policy

Two independent version strings, and they move for different reasons.

### `SCHEMA_VERSION` (currently `1.0.0`)

Versioned as `MAJOR.MINOR.PATCH` in `envelope.py`. Carried in every envelope as
`v`.

- **PATCH** — clarifications that change no accepted or rejected message. A
  receiver built for `1.0.0` still works.
- **MINOR** — additive: a new optional envelope key, a new optional payload field,
  a new message type. A receiver must ignore what it does not understand *if the
  schema says it may*; our schemas set `additionalProperties: false`, so in
  practice a minor bump is a breaking change for a strict receiver. Treat additive
  changes as breaking until proven otherwise.
- **MAJOR** — breaking: removing or renaming a key, changing a type, tightening a
  constraint, adding a required field.

**The rule that matters:** a receiver refuses a message whose `v` it does not
match, rather than guessing. `validate_envelope` reports *"unsupported protocol
version '2.0.0'; this build speaks 1.0.0"*. Refusing is cheap; misinterpreting a
field whose meaning changed is not.

### `TOPIC_VERSION` (currently `v1`)

Bumped when the **topic layout** changes: a new level, a renamed segment, a
different wildcard shape. `parse_topic` rejects any version it does not expect.
The two version strings are allowed to diverge, because a deployment can rename a
topic tree without changing a payload.

## Transports

`protocols/transport.py` defines the abstract `Transport` — `send`, `receive`,
`close`, plus a context manager — and ships exactly one concrete implementation,
`InProcessTransport`, with `make_pair()` to build two connected endpoints.

The in-process transport exists so that everything above the wire can be tested
without a network, a broker or a port binding, which is why protocol tests run on
three operating systems in under a second. **Concrete network transports
(WebSocket, MQTT, serial) do not exist in this repository yet**; they belong with
the service and device layers that need them, and the service layer is planned
rather than implemented.

One design decision is worth carrying into any real transport: the in-process
queue is **finite** (`max_queue`, default 1024) and a full queue **raises** rather
than dropping. Silently dropping samples is how a monitoring system ends up
reporting a healthy average over an unhealthy window.
