import type { ReactElement } from 'react';

import type { MetricsSummary, ProvenanceSummary, SessionSnapshot } from '../api/types';
import { EM_DASH, formatHours, formatNumber, formatPercent } from '../lib/format';
import type { Translator } from '../i18n';

/**
 * Panels. The provenance banner is not optional and is not dismissible: it is the
 * first thing under the header and it renders even when the service is offline,
 * because the caveat must survive a cropped screenshot.
 */

export function DisclaimerBanner({ t }: { t: Translator['t'] }): ReactElement {
  return (
    <p className="banner banner--boundary" role="note">
      {t('disclaimer.short')} <span className="banner__detail">{t('app.boundary')}</span>
    </p>
  );
}

export function ProvenanceBanner({
  provenance,
  t,
}: {
  provenance: ProvenanceSummary | null;
  t: Translator['t'];
}): ReactElement {
  if (provenance === null) {
    return (
      <p className="banner banner--provenance" role="note">
        {t('state.loading')}
      </p>
    );
  }
  return (
    <p className="banner banner--provenance" role="note">
      {t('provenance.banner', {
        unsupported: provenance.unsupported,
        total: provenance.total,
      })}
    </p>
  );
}

export function MetricsPanel({
  metrics,
  runDigest,
  t,
}: {
  metrics: MetricsSummary | null;
  runDigest: string | null;
  t: Translator['t'];
}): ReactElement {
  const rows: Array<[string, string]> = [
    [t('metric.time_to_50pct_repair'), formatHours(metrics?.time_to_50pct_repair_hours ?? null)],
    [t('metric.time_to_full_repair'), formatHours(metrics?.time_to_full_repair_hours ?? null)],
    [t('metric.area_under_damage'), formatNumber(metrics?.area_under_damage_integrity_hours ?? null, 3)],
    [
      t('metric.attention_attributable'),
      formatPercent(metrics?.attention_attributable_fraction ?? null),
    ],
    [t('metric.focus_hours'), formatHours(metrics?.focus_hours ?? null)],
    [t('metric.fatigue_episodes'), formatNumber(metrics?.fatigue_episodes ?? null, 0)],
  ];

  return (
    <section className="panel" aria-labelledby="metrics-heading">
      <h2 id="metrics-heading" className="panel__title">
        {t('panel.metrics')}
      </h2>
      <table className="table">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td className="mono">{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="panel__footnote">
        {t('metric.attention_attributable')}: a decomposition of the model, not a measurement.
        Run digest <span className="mono">{runDigest?.slice(0, 16) ?? EM_DASH}</span>.
      </p>
    </section>
  );
}

export function AttentionPanel({
  snapshot,
  t,
}: {
  snapshot: SessionSnapshot | null;
  t: Translator['t'];
}): ReactElement {
  const conscious = snapshot?.conscious ?? null;
  return (
    <section className="panel" aria-labelledby="attention-heading">
      <h2 id="attention-heading" className="panel__title">
        {t('panel.attention')}
      </h2>
      <dl className="facts">
        <div className="facts__row">
          <dt>{t('field.attention')}</dt>
          <dd className="mono">{formatNumber(conscious?.attention ?? null, 3)}</dd>
        </div>
        <div className="facts__row">
          <dt>{t('field.focused')}</dt>
          <dd className="mono">{conscious?.focused === true ? 'yes' : 'no'}</dd>
        </div>
        <div className="facts__row">
          <dt>{t('field.fatigued')}</dt>
          <dd className="mono">{conscious?.fatigued === true ? 'yes' : 'no'}</dd>
        </div>
        <div className="facts__row">
          <dt>{t('field.integrity')}</dt>
          <dd className="mono">{formatNumber(snapshot?.tissue.integrity ?? null, 4)}</dd>
        </div>
        <div className="facts__row">
          <dt>{t('field.damage')}</dt>
          <dd className="mono">{formatNumber(snapshot?.tissue.damage ?? null, 4)}</dd>
        </div>
        <div className="facts__row">
          <dt>{t('field.time_hours')}</dt>
          <dd className="mono">{formatNumber(snapshot?.t_hours ?? null, 2)}</dd>
        </div>
      </dl>
      <p className="panel__footnote">{t('field.perception_gap')}: perceived progress is tracked separately from integrity.</p>
    </section>
  );
}

export function EventLog({ lines }: { lines: readonly string[] }): ReactElement {
  return (
    <section className="panel panel--wide" aria-labelledby="log-heading">
      <h2 id="log-heading" className="panel__title">
        Events
      </h2>
      {lines.length === 0 ? (
        <p className="panel__footnote">Nothing yet.</p>
      ) : (
        <ul className="log mono">
          {lines.slice(0, 20).map((line, index) => (
            <li key={index}>{line}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function OfflinePanel({ message }: { message: string }): ReactElement {
  return (
    <div className="panel panel--warning" role="status">
      <h2 className="panel__title">Cannot reach the simulation service</h2>
      <p>{message}</p>
      <p className="panel__footnote">
        Start it with <span className="mono">python -m conscious_subconscious.services.api</span> and
        reload. The console is fully usable only when the service is running; it never renders
        simulated data of its own.
      </p>
    </div>
  );
}
