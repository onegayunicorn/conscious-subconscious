/**
 * Site copy.
 *
 * Every number on this page is a real output of this repository, quoted from a
 * command you can re-run. Nothing here is rounded for effect, and nothing is a
 * projection.
 *
 * The tone rules from `media/brand.md` apply: declare the assumption in the first
 * sentence, avoid wellness vocabulary, and never make a health claim.
 */

export const REPOSITORY = 'https://github.com/onegayunicorn/conscious-subconscious';

export const HERO = {
  tagline: 'A reproducible simulation sandbox for mind–body models',
  lede: 'A deterministic Python engine that models an autonomous homeostatic process and a deliberate attentional process acting on the same damaged tissue. Every constant carries a tag saying where it came from. Most of them are guesses, and the reports say so.',
  boundary:
    'Educational and artistic simulation. Not a medical device. It encodes an unvalidated assumption and provides no medical advice.',
};

export interface SweepRow {
  coupling: string;
  timeTo50: string;
  area: string;
  attributable: string;
}

/**
 * Output of:
 *   cs-sim sweep --param conscious.neural_drive_coupling --values 0:3:0.75
 * at the default seed, dt and horizon. Re-run it and compare.
 */
export const SWEEP_ROWS: readonly SweepRow[] = [
  { coupling: '0', timeTo50: '33.95', area: '26.69', attributable: '0' },
  { coupling: '0.75', timeTo50: '27.6', area: '21.09', attributable: '0.1447' },
  { coupling: '1.5', timeTo50: '22.9', area: '17.25', attributable: '0.2204' },
  { coupling: '2.25', timeTo50: '18.8', area: '14.61', attributable: '0.2658' },
  { coupling: '3', timeTo50: '16', area: '12.62', attributable: '0.2899' },
];

export const COMPARISON_ROWS = [
  { scenario: 'baseline', timeTo50: '33.95', area: '26.69', focus: '0 h', attributable: '0' },
  { scenario: 'focused', timeTo50: '27.6', area: '21.09', focus: '29.45 h', attributable: '0.145' },
  {
    scenario: 'intermittent',
    timeTo50: '27.6',
    area: '21.28',
    focus: '23.85 h',
    attributable: '0.119',
  },
  {
    scenario: 'focused-uncoupled',
    timeTo50: '33.95',
    area: '26.69',
    focus: '36.8 h',
    attributable: '0',
  },
];

export interface Feature {
  title: string;
  body: string;
}

export const FEATURES: readonly Feature[] = [
  {
    title: 'Provenance on every constant',
    body: 'Each of the 34 parameters carries a tag saying where its value came from: measured, literature, assumed or invented. Exactly one is supported. The one that matters most — conscious.neural_drive_coupling, which is the entire mind-over-tissue claim — is invented, and every report says so above the results.',
  },
  {
    title: 'A control that switches the claim off',
    body: 'Set the coupling constant to zero and attention becomes inert. A test asserts that the repair metrics then match the no-attention baseline exactly. If that test fails, attention is leaking into repair through an undocumented path.',
  },
  {
    title: 'Sensitivity instead of confidence',
    body: 'cs-sim sensitivity perturbs every unsupported parameter and ranks them by how far the headline metric moves. The output is a ranking of things nobody has measured — which is the honest summary of what the model knows.',
  },
  {
    title: 'Determinism you can check',
    body: 'A seeded generator with named substreams and a virtual clock, so adding a module cannot perturb another component and no run reads the wall clock. Every run emits a digest; equal digests mean byte-identical results.',
  },
  {
    title: 'A protocol, not just a script',
    body: 'One versioned envelope for every message, JSON-RPC for control, NDJSON or MQTT for telemetry, and JSON Schema as the tie-breaker between the Python service and the TypeScript console.',
  },
  {
    title: 'An audit that runs on itself',
    body: 'A short rule set for the mistakes this kind of project actually makes — a committed token, a wildcard CORS origin, an eval left in from debugging. CI runs it against this repository and fails on any high-severity finding.',
  },
];

export const NOTS: readonly string[] = [
  'Not a medical device, a clinical tool, or evidence of anything about bodies.',
  'Not a brain model. There are no neurons, no networks, and no learning rule.',
  'Not calibrated. Nothing was fitted to data, because there was no data to fit.',
  'Not a claim that visualisation or attention changes the rate at which a real wound heals.',
  'Not closed-loop hardware. Every device adapter reads; none of them writes to a person.',
];

export const QUICKSTART = `git clone ${REPOSITORY}.git
cd conscious-subconscious
pip install -e ".[api,dev]"

cs-sim compare            # baseline vs focused vs intermittent
cs-sim sensitivity        # which guesses drive the result
cs-sim run --scenario focused --report`;

export const STATS = [
  { label: 'parameters', value: '34' },
  { label: 'with empirical support', value: '1' },
  { label: 'Python tests', value: '551' },
  { label: 'verified references', value: '28' },
  { label: 'runtime dependencies in the core', value: '0' },
];
