# Hardware layer

The physical side of the project: what you can connect, what it sends, and what
it is deliberately not allowed to do.

## The read-only boundary

Every adapter in this repository **reads**. None of them writes to a person.

There is no stimulation output, no haptic driver, no LED that pulses in time
with a heartbeat, and no path by which the simulation can send anything to the
wearer. That is not an unfinished feature. A project that can drive a stimulator
needs a different safety case — one about consent, dose limits, fail-safe
behaviour and regulatory classification — and nothing here has one.

If you want to build the other half, build it as a separate project with its own
risk analysis. `security/threat-model.md` treats this boundary as an asset to
protect, not a gap to close.

**This is not a medical device and not a fitness device.** Nothing in this
repository measures, diagnoses, monitors or treats any condition. See
[`DISCLAIMER.md`](../DISCLAIMER.md).

## What is here

| Path | Contents |
|---|---|
| `firmware/esp32/bridge/` | Reference firmware for an ESP32 dev board: reads an analog pulse sensor, emits the `CS,` serial line protocol. |
| `firmware/README.md` | Toolchain, flashing, and what the firmware does and does not compute. |
| `wiring/README.md` | Wiring notes and electrical safety constraints. |
| `BOM.csv` | Bill of materials with indicative parts. No prices — they change constantly and a stale price is worse than none. |

## The wire protocol

Firmware emits newline-terminated ASCII lines:

```text
CS,<channel>,<value>
CS,<channel>,<value>,<quality>
```

- `CS` is the frame prefix. Lines not starting with `CS,` are ignored by the
  host, so a boot banner is harmless (`SerialBridgeDevice` relies on this).
- `<quality>` is optional and one of `ok`, `suspect`, `invalid`.
- Channels the host does not recognise are accepted but marked `invalid`, so
  firmware may be newer than the host without either side guessing.

The host side of this is `src/conscious_subconscious/devices/serial_bridge.py`,
which is where the parsing rules and their tests live.

## Supported adapter paths

| Path | Adapter | Extra required | Notes |
|---|---|---|---|
| Synthetic | `simulated` | none | Deterministic. Use this for everything except actual signal work. |
| Microcontroller over USB serial | `serial` | `pyserial` | The `CS,` protocol above. |
| Lab equipment (EEG, physio rigs) | `lsl` | `pylsl` | Resolves a stream by name; never blocks for a full sample, because a step that stalls on a hardware clock stops being reproducible. |
| BLE heart-rate monitor | `ble-heart-rate` | `bleak` | Subscribes to the standard Heart Rate Measurement characteristic (0x2A37). Parsing is a pure function and is tested without a radio. |
| Recorded session | `replay` | none | Playback as fast as the caller asks, so a recording replays identically every time. This is what makes a hardware bug reproducible. |

Install the driver extras with:

```bash
pip install 'conscious-subconscious[devices]'
```

Absent drivers do not break anything: each imports its dependency lazily and
raises `DeviceUnavailable` — a distinct type from `DeviceError` — when it cannot
run here.

## Recording and replay

`ReplayDevice` reads the same CSV shape the adapters emit, so a live capture can
be replayed without conversion:

```csv
t_seconds,channel,value
0.000000,heart_rate,62.400000
0.000000,hrv_index,0.550000
1.000000,heart_rate,61.900000
```

Write one with `conscious_subconscious.devices.write_recording`. Device time is
not simulation time; the two are never mixed.

## What this layer does not do

- No ECG, EEG or EDA interpretation. The adapters deliver numbers in the
  channel's own units and stop there.
- No clinical or fitness conclusions. The heart-rate numbers a cheap analog
  sensor produces are not accurate enough for anything that matters.
- No closed loop. Nothing read here can cause anything to be sent to the wearer.
