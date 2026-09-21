# Firmware

Reference firmware for the microcontroller bridge. It exists to make the serial
protocol concrete and testable, not to be a product.

## Target

`esp32/bridge/bridge.ino` targets an **ESP32 development board** with the
Arduino core (tested against ESP32 Arduino core 2.x APIs). It uses only
`Arduino.h`, so it should also build for an ESP8266 or a classic AVR board after
changing the analog pin and the ADC resolution constant.

## Build and flash

With the [Arduino CLI](https://arduino.github.io/arduino-cli/):

```bash
arduino-cli core install esp32:esp32
arduino-cli compile --fqbn esp32:esp32:esp32 hardware/firmware/esp32/bridge
arduino-cli upload  --fqbn esp32:esp32:esp32 --port /dev/ttyUSB0 \
                    hardware/firmware/esp32/bridge
```

Or open the folder in the Arduino IDE, select your board and port, and upload.

Then point the host adapter at the port:

```bash
export CS_SERIAL_PORT=/dev/ttyUSB0
export CS_SERIAL_BAUD=115200
```

## What it does

1. Prints a boot banner. Non-`CS,` lines are deliberately emitted first, because
   the host must tolerate them — a device that only works if the host parses
   everything it says is a device that breaks the first time it prints a warning.
2. Samples an analog pulse sensor on `ANALOG_PIN`.
3. Detects beats with a moving baseline plus an absolute threshold and a
   refractory period. This is the standard cheap-pulse-sensor approach and it is
   fragile: motion, poor contact and ambient light all corrupt it.
4. Emits one line per second:

```text
CS,heart_rate,63.20
CS,hrv_index,0.41
```

5. Emits `CS,heart_rate,0,invalid` — never a fabricated value — when it has not
   seen a beat recently enough to estimate a rate.

## What it does not do

- **It is not a medical device.** It does not measure ECG, blood oxygenation,
  blood pressure or anything diagnostic. A $5 analog pulse sensor on a
  breadboard is a toy sensor.
- **It does not smooth over failure.** No value is emitted when there is no
  measurement; the firmware reports `invalid` rather than printing the last
  number again.
- **It does not accept commands.** There is no write path from the host to the
  board. The serial link is one-way by construction.
- **It does not calibrate itself.** The thresholds are constants you must adjust
  by hand for your sensor and your finger.

## Constants worth checking before you trust a number

| Constant | Meaning | Why you must set it |
|---|---|---|
| `ANALOG_PIN` | Sensor input | Depends on your board's ADC-capable pins |
| `ADC_MAX` | ADC full-scale value | 4095 on a 12-bit ESP32 ADC, 1023 on a 10-bit AVR |
| `BEAT_THRESHOLD` | Absolute rise required to count a beat | Depends on sensor gain and finger pressure |
| `REFRACTORY_MS` | Minimum gap between beats | Sets the maximum rate the firmware can report |

The firmware's heart-rate value is a rough estimate derived from a noisy analog
signal. Do not use it for anything you would care about being wrong.
