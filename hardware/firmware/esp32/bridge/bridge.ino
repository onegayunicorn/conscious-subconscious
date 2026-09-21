/*
 * conscious-subconscious — reference serial bridge
 * -------------------------------------------------
 * Reads an analog pulse sensor and emits the `CS,<channel>,<value>` line
 * protocol that SerialBridgeDevice expects on the host.
 *
 * READ THIS FIRST
 *   This is not a medical device and not a fitness device. It does not measure
 *   ECG or anything diagnostic. A cheap analog pulse sensor is easily fooled by
 *   motion, ambient light and finger pressure, and the value it produces is a
 *   rough estimate. Do not use it for any decision that matters.
 *
 *   The link is one-way. There is no command parser and no output pin that
 *   does anything except the serial port. If you add one, you are building a
 *   different project with a different safety case.
 *
 * Protocol
 *   CS,heart_rate,63.20         bpm, one decimal is plenty
 *   CS,hrv_index,0.41           dimensionless 0..1, see notes below
 *   CS,heart_rate,0,invalid     emitted when there is no recent measurement
 *
 * Hardware
 *   Analog pulse sensor signal -> ANALOG_PIN. Power the sensor from 3V3 and
 *   make sure its output never exceeds the ADC reference. See
 *   ../../wiring/README.md before you connect anything.
 */

#include <Arduino.h>

// ----------------------------------------------------------------- hardware
static const uint8_t ANALOG_PIN = 34;      // ESP32: an ADC1 pin (ADC2 fights Wi-Fi)
static const int ADC_MAX = 4095;           // 12-bit ADC on ESP32; 1023 on a 10-bit AVR
static const unsigned long SERIAL_BAUD = 115200;

// ----------------------------------------------------------------- tuning
// These are the constants you will have to change by hand for your sensor.
static const int BEAT_THRESHOLD = 180;     // ADC counts above baseline to call a beat
static const unsigned long REFRACTORY_MS = 300;   // caps the reportable rate at 200 bpm
static const unsigned long STALE_MS = 3000;       // no beat for this long => invalid
static const size_t RR_WINDOW = 24;               // beats kept for the HRV estimate

// ----------------------------------------------------------------- state
static int baseline = ADC_MAX / 2;
static unsigned long lastBeatMs = 0;
static unsigned long lastEmitMs = 0;
static float lastBpm = 0.0f;

static unsigned int rrIntervals[RR_WINDOW];  // milliseconds between beats
static size_t rrCount = 0;
static size_t rrNext = 0;

// ----------------------------------------------------------------- helpers
static void emit(const char *channel, float value) {
  Serial.print(F("CS,"));
  Serial.print(channel);
  Serial.print(',');
  Serial.println(value, 2);
}

static void emitInvalid(const char *channel) {
  // Never repeat a stale number. Repeating the last reading is the single most
  // common way a sensor bridge quietly turns into a random number generator.
  Serial.print(F("CS,"));
  Serial.print(channel);
  Serial.print(F(",0,invalid"));
  Serial.println();
}

static void recordInterval(unsigned long intervalMs) {
  rrIntervals[rrNext] = (unsigned int)intervalMs;
  rrNext = (rrNext + 1) % RR_WINDOW;
  if (rrCount < RR_WINDOW) {
    rrCount++;
  }
}

/*
 * RMSSD over the beat window, mapped onto 0..1 for the host's `hrv_index`
 * channel. Both the metric and the mapping are crude: RMSSD is defined over
 * beat-to-beat intervals, and the 20..80 ms span used to normalise it is a
 * presentation choice, not a clinical interpretation.
 */
static bool computeHrvIndex(float *out) {
  if (rrCount < 4) {
    return false;
  }
  double sumSquares = 0.0;
  size_t pairs = 0;
  for (size_t i = 1; i < rrCount; i++) {
    long diff = (long)rrIntervals[i] - (long)rrIntervals[i - 1];
    sumSquares += (double)diff * (double)diff;
    pairs++;
  }
  if (pairs == 0) {
    return false;
  }
  float rmssd = sqrt(sumSquares / (double)pairs);
  const float RMSSD_MIN_MS = 20.0f;
  const float RMSSD_MAX_MS = 80.0f;
  float index = (rmssd - RMSSD_MIN_MS) / (RMSSD_MAX_MS - RMSSD_MIN_MS);
  if (index < 0.0f) index = 0.0f;
  if (index > 1.0f) index = 1.0f;
  *out = index;
  return true;
}

// ----------------------------------------------------------------- lifecycle
void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(200);  // let the USB-serial bridge settle before the banner

  // Deliberately not in the CS, dialect: the host must tolerate plain chatter.
  Serial.println(F("conscious-subconscious serial bridge"));
  Serial.println(F("reference firmware - not a medical device"));
  Serial.println(F("emitting CS,<channel>,<value> at 1 Hz"));
}

void loop() {
  const unsigned long now = millis();
  const int reading = analogRead(ANALOG_PIN);

  // Slow baseline tracking so a drift in ambient light does not look like a beat.
  baseline = (baseline * 7 + reading) / 8;

  const bool aboveThreshold = (reading - baseline) > BEAT_THRESHOLD;
  const bool pastRefractory = (now - lastBeatMs) > REFRACTORY_MS;

  if (aboveThreshold && pastRefractory) {
    if (lastBeatMs != 0) {
      recordInterval(now - lastBeatMs);
    }
    lastBeatMs = now;
  }

  if (now - lastEmitMs < 1000) {
    return;
  }
  lastEmitMs = now;

  if (lastBeatMs == 0 || (now - lastBeatMs) > STALE_MS) {
    emitInvalid("heart_rate");
    emitInvalid("hrv_index");
    return;
  }

  // Rate from the most recent interval.
  unsigned long latestInterval = now - lastBeatMs;
  if (rrCount > 0) {
    size_t lastIndex = (rrNext + RR_WINDOW - 1) % RR_WINDOW;
    latestInterval = rrIntervals[lastIndex];
  }
  if (latestInterval > 0) {
    lastBpm = 60000.0f / (float)latestInterval;
  }

  if (lastBpm >= 25.0f && lastBpm <= 220.0f) {
    emit("heart_rate", lastBpm);
  } else {
    // Outside anything plausible: say so rather than reporting it.
    emitInvalid("heart_rate");
  }

  float hrvIndex = 0.0f;
  if (computeHrvIndex(&hrvIndex)) {
    emit("hrv_index", hrvIndex);
  } else {
    emitInvalid("hrv_index");
  }
}
