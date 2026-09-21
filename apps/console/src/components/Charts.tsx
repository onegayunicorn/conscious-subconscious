import type { ReactElement } from 'react';

import type { TickPoint } from '../api/types';
import { EM_DASH, clamp, downsample, formatNumber } from '../lib/format';

/**
 * Hand-rolled SVG charts.
 *
 * A charting library would be 100 kB and would decide for us what an absent
 * value looks like. Here, a gap in the data is a gap in the line — never a point
 * at zero, which is the single most common way a monitoring chart misleads.
 */

const VIEW_WIDTH = 720;
const VIEW_HEIGHT = 220;
const PADDING = { top: 12, right: 12, bottom: 26, left: 44 };

interface Series {
  points: Array<{ x: number; y: number | null }>;
  label: string;
  color: string;
  dashed?: boolean;
}

export interface LineChartProps {
  ticks: readonly TickPoint[];
  yMin?: number;
  yMax?: number;
  yLabel: string;
  xLabel: string;
  points?: number;
}

function buildPath(series: Series, scaleX: (x: number) => number, scaleY: (y: number) => number): string {
  let path = '';
  let penDown = false;
  for (const point of series.points) {
    if (point.y === null) {
      // Lift the pen across a gap instead of drawing a line to zero.
      penDown = false;
      continue;
    }
    const x = scaleX(point.x).toFixed(2);
    const y = scaleY(point.y).toFixed(2);
    path += penDown ? ` L ${x} ${y}` : ` M ${x} ${y}`;
    penDown = true;
  }
  return path.trim();
}

export function LineChart({
  ticks,
  yMin = 0,
  yMax = 1,
  yLabel,
  xLabel,
  points = 360,
}: LineChartProps): ReactElement {
  const sampled = downsample(ticks, points);
  const first = sampled[0];
  const last = sampled[sampled.length - 1];

  if (first === undefined || last === undefined) {
    return (
      <div className="chart chart--empty" role="img" aria-label={`${yLabel}: no data yet`}>
        <span>{EM_DASH}</span>
      </div>
    );
  }

  const xMin = first.t;
  const xMax = last.t === xMin ? xMin + 1 : last.t;
  const span = xMax - xMin;

  const scaleX = (x: number): number =>
    PADDING.left + ((x - xMin) / span) * (VIEW_WIDTH - PADDING.left - PADDING.right);
  const scaleY = (y: number): number =>
    PADDING.top +
    (1 - (clamp(y, yMin, yMax) - yMin) / (yMax - yMin)) *
      (VIEW_HEIGHT - PADDING.top - PADDING.bottom);

  const series: Series[] = [
    {
      label: 'integrity',
      color: 'var(--cs-mint)',
      points: sampled.map((point) => ({ x: point.t, y: point.integrity })),
    },
    {
      label: 'perceived',
      color: 'var(--cs-amber)',
      dashed: true,
      points: sampled.map((point) => ({ x: point.t, y: point.perceived })),
    },
  ];

  const gridLines = [0, 0.25, 0.5, 0.75, 1];

  return (
    <figure className="chart">
      <svg
        viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`}
        role="img"
        aria-label={`${yLabel} against ${xLabel}`}
        preserveAspectRatio="none"
      >
        {gridLines.map((fraction) => {
          const y = scaleY(yMin + fraction * (yMax - yMin));
          return (
            <g key={fraction}>
              <line
                x1={PADDING.left}
                x2={VIEW_WIDTH - PADDING.right}
                y1={y}
                y2={y}
                className="chart__grid"
              />
              <text x={PADDING.left - 8} y={y + 4} className="chart__axis-label" textAnchor="end">
                {formatNumber(yMin + fraction * (yMax - yMin), 2)}
              </text>
            </g>
          );
        })}

        {series.map((entry) => (
          <path
            key={entry.label}
            d={buildPath(entry, scaleX, scaleY)}
            fill="none"
            stroke={entry.color}
            strokeWidth={2}
            strokeDasharray={entry.dashed === true ? '5 4' : undefined}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        <text x={PADDING.left} y={VIEW_HEIGHT - 6} className="chart__axis-label">
          {xLabel} {formatNumber(xMin, 2)}
        </text>
        <text
          x={VIEW_WIDTH - PADDING.right}
          y={VIEW_HEIGHT - 6}
          className="chart__axis-label"
          textAnchor="end"
        >
          {formatNumber(xMax, 2)}
        </text>
      </svg>
      <figcaption className="chart__caption">
        <span className="legend legend--mint">actual integrity</span>
        <span className="legend legend--amber">perceived progress</span>
        <span className="chart__note">
          The two lines are different quantities. The gap between them is the model&apos;s
          perception channel, not an error.
        </span>
      </figcaption>
    </figure>
  );
}

export interface AttentionChartProps {
  ticks: readonly TickPoint[];
  budget: number;
  points?: number;
}

export function AttentionChart({ ticks, budget, points = 360 }: AttentionChartProps): ReactElement {
  const sampled = downsample(ticks, points);
  const last = sampled[sampled.length - 1];

  if (last === undefined) {
    return (
      <div className="chart chart--empty" role="img" aria-label="attention budget: no data yet">
        <span>{EM_DASH}</span>
      </div>
    );
  }

  const first = sampled[0] ?? last;
  const xMin = first.t;
  const xMax = last.t === xMin ? xMin + 1 : last.t;
  const scaleX = (x: number): number =>
    PADDING.left + ((x - xMin) / (xMax - xMin)) * (VIEW_WIDTH - PADDING.left - PADDING.right);
  const scaleY = (y: number): number =>
    PADDING.top +
    (1 - clamp(y, 0, budget) / budget) * (VIEW_HEIGHT - PADDING.top - PADDING.bottom);

  const path = buildPath(
    { label: 'attention', color: 'var(--cs-amber)', points: sampled.map((p) => ({ x: p.t, y: p.attention })) },
    scaleX,
    scaleY,
  );

  // Shade the intervals where attention was actually engaged.
  const bands: Array<{ x: number; width: number }> = [];
  let open: number | null = null;
  for (const point of sampled) {
    if (point.focused && open === null) {
      open = point.t;
    } else if (!point.focused && open !== null) {
      bands.push({ x: scaleX(open), width: Math.max(1, scaleX(point.t) - scaleX(open)) });
      open = null;
    }
  }
  if (open !== null) {
    bands.push({ x: scaleX(open), width: Math.max(1, scaleX(last.t) - scaleX(open)) });
  }

  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} role="img" aria-label="attention budget over time">
        {bands.map((band, index) => (
          <rect
            key={index}
            x={band.x}
            y={PADDING.top}
            width={band.width}
            height={VIEW_HEIGHT - PADDING.top - PADDING.bottom}
            className="chart__band"
          />
        ))}
        <line
          x1={PADDING.left}
          x2={VIEW_WIDTH - PADDING.right}
          y1={scaleY(budget)}
          y2={scaleY(budget)}
          className="chart__grid"
        />
        <path d={path} fill="none" stroke="var(--cs-amber)" strokeWidth={2} strokeLinejoin="round" />
        <text
          x={VIEW_WIDTH - PADDING.right}
          y={VIEW_HEIGHT - 6}
          className="chart__axis-label"
          textAnchor="end"
        >
          {formatNumber(xMax, 2)} h
        </text>
      </svg>
      <figcaption className="chart__caption">
        <span className="legend legend--amber">attention budget</span>
        <span className="chart__note">
          Shaded bands are the intervals where attention was engaged. The budget is finite and
          returns slowly, which is why forced continuous focus is not the best strategy.
        </span>
      </figcaption>
    </figure>
  );
}

export interface MediatorBarsProps {
  mediators: Record<string, number>;
  labels: Record<string, string>;
}

export function MediatorBars({ mediators, labels }: MediatorBarsProps): ReactElement {
  const entries = Object.entries(mediators).sort(([a], [b]) => a.localeCompare(b));
  const peak = Math.max(0.0001, ...entries.map(([, value]) => value));

  return (
    <ul className="bars">
      {entries.map(([channel, value]) => (
        <li key={channel} className="bars__row">
          <span className="bars__label mono">{labels[channel] ?? channel}</span>
          <span className="bars__track">
            <span
              className={
                channel === 'neural_drive' ? 'bars__fill bars__fill--accent' : 'bars__fill'
              }
              style={{ width: `${(value / peak) * 100}%` }}
            />
          </span>
          <span className="bars__value mono">{formatNumber(value, 3)}</span>
        </li>
      ))}
    </ul>
  );
}
