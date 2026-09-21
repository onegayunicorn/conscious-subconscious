/**
 * Display helpers.
 *
 * The single rule that matters: an absent value renders as an em dash, never as
 * `0` or `NaN`. "Never reached 50% repair in the horizon" and "reached it in
 * zero hours" are opposite statements, and a table that renders both as `0` is a
 * table that lies.
 */

export const EM_DASH = '—';

/** Format a number for display, or the em dash when it is absent or not finite. */
export function formatNumber(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EM_DASH;
  }
  if (value !== 0 && (Math.abs(value) >= 100000 || Math.abs(value) < 0.001)) {
    return value.toExponential(2);
  }
  const fixed = value.toFixed(digits);
  return fixed.includes('.') ? fixed.replace(/0+$/, '').replace(/\.$/, '') : fixed;
}

/** Format a duration in hours. */
export function formatHours(value: number | null | undefined, digits = 2): string {
  const rendered = formatNumber(value, digits);
  return rendered === EM_DASH ? EM_DASH : `${rendered} h`;
}

/** Format a fraction as a percentage. */
export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return EM_DASH;
  }
  return `${(value * 100).toFixed(digits)}%`;
}

/** Format an ISO timestamp as a compact local time, tolerating bad input. */
export function formatTimestamp(iso: string): string {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return EM_DASH;
  }
  return parsed.toLocaleTimeString();
}

/** Join class names, dropping falsy entries. */
export function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter((value): value is string => Boolean(value)).join(' ');
}

/**
 * Trim a series for rendering, keeping the shape of the run.
 *
 * Down-samples by taking evenly spaced points, and always keeps the final point:
 * dropping the last sample would hide the end state, which is usually the thing
 * being looked at.
 */
export function downsample<T>(points: readonly T[], limit: number): T[] {
  if (limit <= 0) {
    throw new Error('limit must be positive');
  }
  if (points.length <= limit) {
    return [...points];
  }
  const step = points.length / limit;
  const sampled: T[] = [];
  for (let index = 0; index < limit - 1; index += 1) {
    const point = points[Math.floor(index * step)];
    if (point !== undefined) {
      sampled.push(point);
    }
  }
  const last = points[points.length - 1];
  if (last !== undefined) {
    sampled.push(last);
  }
  return sampled;
}

/** Clamp to a range, used by chart scales. */
export function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}
