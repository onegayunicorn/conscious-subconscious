# Hardware

Five adapters are registered in `src/conscious_subconscious/devices/`. Four of them
touch hardware or recorded data; the fifth needs nothing at all and is the default
everywhere.

> **Boundary.** These adapters read from sensors. They are **read-only with respect
> to the person wearing the sensor**: there is no stimulation, actuation or write
> method in any adapter, and `DeviceCapabilities.bidirectional` defaults to
> `False`. That is a deliberate safety boundary, not a missing feature — a project
> that can drive a stimulator is a different project with a different safety case.
> See `security/threat-model.md`.
>
> Nothing here is a medical device, and none of it measures anything clinically.
> See [DISCLAIMER.md](https://github.com/onegayunicorn/conscious-subconscious/blob/main/DISCLAIMER.md).

## The driver contract

`devices/base.py`. Every adapter — real or synthetic — implements the same tiny
surface:

| Method | Contract |
| --- | --- |
| `open()` | Acquire the device. Raises `DeviceUnavailable` if that is impossible *here*. |
| `read()` | Return every `Sample` available since the last call. May return none. |
| `close()` | Release. Must be safe to call twice. |
| `capabilities` | Static `DeviceCapabilities`: channels, nominal rate, `bidirectional`. |

Plus `describe()` and `hello_payload()` for discovery.

Two properties are load-bearing:

1. **Read-only.** No adapter has a `write`, `send` or `stimulate` method.
2. **Honest unavailability.** A driver that cannot run here raises
   `DeviceUnavailable` — distinct from `DeviceError`. "pyserial is not installed"
   and "the sensor returned garbage" need different responses from the caller, so
   they get different exception types. `build_reported()` returns both the drivers
   that were built and the failures, because the difference between "the sensor was
   not found" and "the sensor was found and broken" is exactly what a caller needs.

Optional dependencies (`pyserial`, `pylsl`, `bleak`) are imported **inside** each
driver, so `import conscious_subconscious.devices` succeeds on a machine with none
of them installed, and the failure arrives with a useful message only when someone
actually tries to open a port or a radio.

## The adapters

### `simulated` — no hardware required

`devices/simulated.py`. A deterministic synthetic heart-rate and HRV-index source:
a resting mean, a slow respiratory-sinus-arrhythmia-like oscillation and bounded
noise. Each device owns its own named RNG substream, so two simulated devices in a
session do not perturb each other and adding a third does not change the first two.

This is the default adapter everywhere, and it is why the console, the API and the
pipelines can be demonstrated on a machine with no sensors. It is a cartoon of a
heart-rate signal, and it is labelled as one.

- Channels: `heart_rate` (bpm), `hrv_index` (ratio)
- Requires: nothing

### `serial` — microcontroller bridge

`devices/serial_bridge.py`. Reads lines from a serial port.

- Channels: `heart_rate` (bpm), `eda` (microsiemens), `skin_temperature` (degC),
  `hrv_index` (ratio)
- Requires: `pyserial` (`pip install "conscious-subconscious[devices]"`), a port,
  and a device speaking the line protocol below
- Configuration: `CS_SERIAL_PORT` (e.g. `/dev/ttyUSB0`, `COM3`), `CS_SERIAL_BAUD`
  (default 115200), or `{"port": ..., "baud": ..., "sample_rate_hz": ...}`

**Line format.** Intentionally boring and self-describing, so firmware can emit it
with `Serial.println` and no JSON library:

```text
CS,<channel>,<value>
CS,<channel>,<value>,<quality>
```

Concrete lines:

```text
CS,heart_rate,62.4
CS,hrv_index,0.55
CS,eda,3.1,suspect
```

Rules, all implemented in `parse_line()`:

- Lines that do **not** start with `CS,` are device chatter and are ignored. A
  firmware boot banner must not crash the host.
- A `CS,` line that is malformed **is** an error. At that point the device is
  speaking the protocol and speaking it wrongly: wrong field count, empty channel,
  non-numeric value and `NaN` all raise.
- `<quality>` is one of `ok`, `suspect`, `invalid`. Anything else is an error.
- An **unknown channel** is marked `invalid` rather than rejected. Firmware may
  legitimately be newer than the host, and an unrecognised channel must never
  silently reach a module that would misinterpret it. `Sample.usable` is `False`
  for `invalid`, so it cannot be fed to a module.
- Reads are drained with a bound of 256 lines per call, so a chatty device cannot
  starve the caller, and lines at or above 512 bytes are rejected.

A fragment of matching firmware is sketched in `hardware/firmware/`. That directory
does not exist in this repository yet, which means the line format above is the
only specification you have — it is exactly the format `parse_line()` implements.

### `lsl` — Lab Streaming Layer

`devices/lsl_device.py`. Resolves an LSL stream by name and pulls whatever is
available on each `read()`.

- Requires: `pylsl` **and** a liblsl binary available to the loader, plus a stream
  on the local network
- Configuration: `CS_LSL_STREAM_NAME` (default `conscious-subconscious`)
- Pulls are capped per call (`MAX_CHUNK`), and the adapter **never blocks for a
  full sample**: a simulation step that stalls on a hardware clock stops being
  reproducible.

LSL is the lingua franca of lab hardware, and it handles clock synchronisation that
is genuinely hard to do yourself. It is also the most fragile of the four to set up,
because the Python wrapper is not the whole story.

### `ble-heart-rate` — Bluetooth LE heart rate

`devices/ble_heart_rate.py`. Subscribes to GATT notifications and never writes a
characteristic.

- Service `0000180d-0000-1000-8000-00805f9b34fb`, characteristic
  `00002a37-0000-1000-8000-00805f9b34fb`
- Requires: `bleak`, a Bluetooth adapter, and a suitable OS permission grant
  (macOS and Windows both prompt; on Linux the process needs access to the HCI
  device)
- Configuration: `CS_BLE_ADDRESS`; leave blank to scan and take the first
  advertiser

The parsing is deliberately split from the Bluetooth stack.
`parse_heart_rate_measurement()` is a pure function over bytes and is fully tested
in CI with no radio, no adapter and no `bleak` installed. `rmssd_ms()` and
`hrv_index_from_rmssd()` turn RR intervals into the normalised index the autonomic
module consumes.

That split exists because the parsing is where the bugs are: the characteristic has
a flags byte, two widths for the same field, optional sections, and RR intervals in
units of 1/1024 s. Getting it wrong produces plausible-looking numbers, which is the
worst kind of wrong.

### `replay` — a recorded session

`devices/replay.py`. Plays back a CSV recording deterministically. Replay is what
makes a hardware bug reproducible: if a run misbehaved because a sensor produced a
bad stretch of data, the fix is only verifiable if that stretch can be played back
byte for byte.

Format — the same comma-separated shape used everywhere else, so a recording can be
produced by hand, by the console or by `tcpdump`-style tooling without a custom
writer:

```csv
t_seconds,channel,value
0.000,heart_rate,62.4
0.000,hrv_index,0.55
1.000,heart_rate,61.9
```

`write_recording()` writes that format. Replay is **not** wall-clock paced: it
hands out samples as fast as the caller asks, so a four-hour recording replays in
milliseconds and two replays of the same file produce identical results.

## Configuration summary

| Variable | Adapter | Default |
| --- | --- | --- |
| `CS_SERIAL_PORT` | `serial` | empty — the adapter raises `DeviceUnavailable` |
| `CS_SERIAL_BAUD` | `serial` | 115200 |
| `CS_BLE_ADDRESS` | `ble-heart-rate` | empty — scan and take the first advertiser |
| `CS_LSL_STREAM_NAME` | `lsl` | `conscious-subconscious` |

## What hardware cannot do here

Stated as invariants, since they are the point:

- No adapter can send a stimulus, actuate anything, or write to the wearer.
- No adapter can change tissue integrity, in whole or in part.
- No adapter path reaches `Tissue.apply_repair`. The only caller of that method is
  `SubconsciousSystem.step`, and the only input it takes from hardware is an
  HRV-style index that moves a mediator channel.
- No sensor reading is presented as a clinical measurement. `stream.sample`
  carries raw values in the channel's own unit, with a `quality` flag, and device
  time is never mixed with simulation time.

## Practical notes

- On a machine without the optional extras, `import conscious_subconscious.devices`
  still works and `describe_all()` still lists all five kinds. Building a driver
  is what requires the dependency.
- LSL on macOS and Windows generally needs the liblsl runtime installed separately
  from the Python wheel.
- BLE scanning requires an OS-level permission that cannot be granted by the code.
- Serial ports are usually owned by a group (`dialout` on Debian-family systems);
  membership is an operator decision, not something the project requests.
- Nothing in this project starts an adapter automatically. Creating one is always
  an explicit act by a caller.

## What has not been verified

- **No adapter has been tested against a physical sensor by this project.** The
  pure parsing functions are covered; the I/O paths are not.
- **No firmware is shipped.** `hardware/firmware/` is referenced by the serial
  adapter's documentation and does not exist in this repository.
- **No BLE, LSL or serial device has been exercised in CI**, because CI has no
  hardware, no radio and no broker.
- **No rate, latency or jitter measurements exist** for any adapter. There is no
  throughput claim to make and none is made.
