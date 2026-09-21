/**
 * Wire types, mirroring `protocols/schemas/` and the service's response shapes.
 *
 * These are declared by hand rather than generated. Two hand-written
 * implementations of one contract can drift, which is why the Python side is
 * checked against the JSON Schema in `tests/conformance/`: the schema is the
 * tie-breaker, and a drift shows up as a failing test rather than as a console
 * that silently renders `undefined`.
 */

/** Values a parameter's provenance can take. Matches the Python `Provenance`. */
export type Provenance = 'measured' | 'literature' | 'assumed' | 'invented';

/** Provenance grades with empirical support. Everything else is a free knob. */
export const SUPPORTED_PROVENANCE: readonly Provenance[] = ['measured', 'literature'];

export interface ParameterRecord {
  key: string;
  value: number;
  unit: string;
  provenance: Provenance;
  supported: boolean;
  rationale: string;
  note: string;
  minimum: number | null;
  maximum: number | null;
}

export interface ProvenanceSummary {
  total: number;
  supported: number;
  unsupported: number;
  unsupported_fraction: number;
}

export interface ScenarioRecord {
  name: string;
  summary: string;
  caveat: string;
  config: Record<string, unknown>;
}

export interface MetricsSummary {
  samples: number;
  final_integrity: number;
  time_to_50pct_repair_hours: number | null;
  time_to_full_repair_hours: number | null;
  area_under_damage_integrity_hours: number;
  mean_integrity: number;
  peak_neural_drive: number;
  peak_growth_factor: number;
  attention_spent: number;
  focus_hours: number;
  min_attention: number;
  fatigue_episodes: number;
  total_repair: number;
  attention_attributable_repair: number;
  attention_attributable_fraction: number;
  final_perception_gap: number;
}

export interface TissueSnapshot {
  name: string;
  integrity: number;
  damage: number;
  max_integrity: number;
  total_repair: number;
  wasted_repair: number;
  is_healed: boolean;
}

export interface ConsciousSnapshot {
  focused: boolean;
  focus_target: string | null;
  attention: number;
  fatigued: boolean;
  attention_spent: number;
  focus_hours: number;
}

export interface SessionSnapshot {
  id: string;
  t_hours: number;
  steps: number;
  finished: boolean;
  scenario: string;
  seed: number;
  focus_policy: string;
  modules: string[];
  tissue: TissueSnapshot;
  mediators: Record<string, number>;
  conscious: ConsciousSnapshot;
  signals: Record<string, number>;
  provided_samples: number;
}

/** `sim.tick` payload. */
export interface SimTick {
  t_hours: number;
  integrity: number;
  damage: number;
  attention?: number;
  focused?: boolean;
  fatigued?: boolean;
  perceived_progress?: number;
  mediators?: Record<string, number>;
  rates?: Record<string, number>;
  applied_repair?: number;
}

/** The envelope every message is wrapped in. */
export interface Envelope<T> {
  v: string;
  id: string;
  ts: string;
  type: string;
  source: string;
  session?: string;
  payload: T;
}

export interface ApiMeta {
  name: string;
  version: string;
  protocol_version: string;
  parameter_count: number;
  focus_policies: string[];
  modules: string[];
  device_kinds: string[];
  pipeline_steps: string[];
  locales: string[];
  default_locale: string;
  auth: { enabled: boolean; scheme: string; note: string };
  disclaimer: string;
  provenance_policy: string;
}

export interface SessionCreated {
  id: string;
  snapshot: SessionSnapshot;
  disclaimer: string;
}

export interface RunResult {
  scenario: string;
  seed: number;
  final_integrity: number;
  metrics: MetricsSummary;
  provenance_summary: ProvenanceSummary;
  digests: { parameters: string; config: string; run: string };
  disclaimer: string;
}

export interface CreateSessionBody {
  scenario?: string;
  seed?: number;
  dt_hours?: number;
  horizon_hours?: number;
  focus_policy?: 'never' | 'always' | 'intermittent';
  modules?: string[];
  overrides?: Record<string, number>;
}

/** One point on a chart. Kept small because a run can produce thousands. */
export interface TickPoint {
  t: number;
  integrity: number;
  perceived: number;
  attention: number;
  focused: boolean;
}
