# Wiring

```text
        +3V3 ──────────────┬──────────────┐
                           │              │
                      ┌────┴────┐    ┌────┴─────┐
                      │  Pulse  │    │  ESP32   │
                      │  sensor │    │  devkit  │
   signal ────────────┤  OUT    ├────┤ GPIO 34  │   (ADC1 — see note 1)
                      │         │    │          │
        GND ──────────┴────┬────┘    │  USB ────┼──── host (CS, protocol)
                           │         └──────────┘
                          GND
```

An ASCII sketch is enough here because the circuit is three wires. What follows
is the part that actually matters.

## 1. Never exceed the ADC reference voltage

The ESP32's ADC input must stay between 0 V and its reference (about 3.3 V;
3.6 V is the absolute maximum and anything above it can damage the pin
permanently). Many pulse sensors are sold for 5 V logic and will output more
than 3.3 V. Check the sensor's rated supply and output swing before connecting
it, and use a level shifter or a resistor divider if the output can exceed
3.3 V. Feeding 5 V into an ESP32 GPIO is a reliable way to destroy the board and
possibly the host USB port with it.

## 2. Use an ADC1 pin

On the ESP32, ADC2 pins are unusable while Wi-Fi is active. The reference
firmware uses GPIO 34, which is ADC1 and is also input-only — a good choice for
a sensor, and a bad choice if you were hoping to drive something from it.

## 3. Common ground is not optional

The sensor and the board must share a ground. A missing common ground produces
readings that look plausible and are meaningless, which is worse than no reading
at all.

## 4. Keep the analog run short

A long unshielded wire next to a USB cable or a switching supply picks up noise.
If your heart-rate estimate jumps around when you move your hand near the
board, that is almost always the wiring, not the firmware.

## 5. Power from the board's regulator, not a second supply

Sharing a single 5 V USB supply keeps the grounds trivially common and avoids
ground-loop offsets that shift the baseline the firmware is tracking.

## Before you connect anything to a person

- **This is not a medical device.** It must not be used to monitor, diagnose or
  treat anyone. Read [`../../DISCLAIMER.md`](../../DISCLAIMER.md).
- **Battery power beats mains power** for anything worn on a body. A USB cable
  to a mains-powered laptop is a path you do not want to be part of.
- **No outputs.** Do not add an LED, buzzer, vibration motor or electrode driven
  by this firmware. The serial link is intentionally one-way; see
  [`../README.md`](../README.md) for why that boundary exists.
- If you intend to use any of this on a person other than yourself, that is a
  research-ethics question, not a wiring question, and it needs a review board —
  not a breadboard.
