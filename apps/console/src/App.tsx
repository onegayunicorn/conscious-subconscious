import { useEffect, useMemo, useState, type ReactElement } from 'react';

import { SimulationClient } from './api/client';
import { AttentionChart, LineChart, MediatorBars } from './components/Charts';
import { Controls } from './components/Controls';
import {
  AttentionPanel,
  DisclaimerBanner,
  EventLog,
  MetricsPanel,
  OfflinePanel,
  ProvenanceBanner,
} from './components/Panels';
import { createTranslator, direction, resolveLocale, type Locale } from './i18n';
import { useSimulation } from './hooks/useSimulation';

const client = new SimulationClient();

const MEDIATOR_LABELS: Record<string, string> = {
  growth_factor: 'growth factor',
  cytokine: 'cytokines',
  perfusion: 'perfusion',
  neural_drive: 'neural drive',
  atp: 'local energy',
};

export function App(): ReactElement {
  const [locale, setLocale] = useState<Locale>(() =>
    resolveLocale(typeof navigator === 'undefined' ? undefined : navigator.language),
  );
  const [scenario, setScenario] = useState('baseline');
  const [policy, setPolicy] = useState('never');

  const translator = useMemo(() => createTranslator(locale), [locale]);
  const simulation = useSimulation(client);

  // Flip the document direction for Arabic. Doing it in an effect rather than in
  // the markup means the whole document — including scrollbars and the title —
  // agrees on the direction.
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = direction(locale);
  }, [locale]);

  const scenarios = useMemo(() => {
    const names = simulation.meta?.modules;
    return names === undefined
      ? ['baseline', 'focused', 'intermittent', 'focused-uncoupled']
      : ['baseline', 'focused', 'intermittent', 'focused-uncoupled', 'expectancy-on', 'inflammation-heavy', 'unmodulated'];
  }, [simulation.meta]);

  const offline = simulation.connection === 'offline';

  return (
    <div className="app">
      <header className="app__header">
        <div>
          <h1 className="app__title">
            conscious<span className="app__title-accent">-</span>subconscious
          </h1>
          <p className="app__tagline">{translator.t('app.tagline')}</p>
        </div>
        <a
          className="app__link"
          href="https://github.com/onegayunicorn/conscious-subconscious"
          rel="noreferrer noopener"
          target="_blank"
        >
          {translator.t('nav.source')}
        </a>
      </header>

      <DisclaimerBanner t={translator.t} />
      <ProvenanceBanner provenance={simulation.provenance} t={translator.t} />

      <Controls
        connection={simulation.connection}
        busy={simulation.busy}
        scenario={scenario}
        policy={policy}
        locale={locale}
        scenarios={scenarios}
        onScenarioChange={setScenario}
        onPolicyChange={(next) => {
          setPolicy(next);
          void simulation.setPolicy(next);
        }}
        onLocaleChange={setLocale}
        onStart={() => void simulation.start({ scenario, policy })}
        onStep={() => void simulation.stepOnce(20)}
        onRun={() => void simulation.runToCompletion()}
        onFocus={() => void simulation.focus()}
        onRelease={() => void simulation.release()}
        onReset={simulation.reset}
        t={translator.t}
      />

      {simulation.error !== null && (
        <p className="banner banner--error" role="alert">
          {simulation.error}
        </p>
      )}

      {offline && simulation.error !== null && <OfflinePanel message={simulation.error} />}

      <main className="app__grid">
        <section className="panel panel--wide" aria-labelledby="integrity-heading">
          <h2 id="integrity-heading" className="panel__title">
            {translator.t('field.integrity')}
          </h2>
          <LineChart
            ticks={simulation.ticks}
            yLabel={translator.t('field.integrity')}
            xLabel={translator.t('field.time_hours')}
          />
        </section>

        <section className="panel panel--wide" aria-labelledby="attention-chart-heading">
          <h2 id="attention-chart-heading" className="panel__title">
            {translator.t('panel.attention')}
          </h2>
          <AttentionChart ticks={simulation.ticks} budget={1} />
        </section>

        <section className="panel" aria-labelledby="mediators-heading">
          <h2 id="mediators-heading" className="panel__title">
            {translator.t('panel.mediators')}
          </h2>
          <MediatorBars
            mediators={simulation.snapshot?.mediators ?? {}}
            labels={MEDIATOR_LABELS}
          />
          <p className="panel__footnote">
            Modelled channels, not measurements. Only <span className="mono">neural_drive</span> is
            produced by attention, and only its coupling constant connects it to repair.
          </p>
        </section>

        <AttentionPanel snapshot={simulation.snapshot} t={translator.t} />
        <MetricsPanel metrics={simulation.metrics} runDigest={simulation.runDigest} t={translator.t} />
        <EventLog lines={simulation.log} />
      </main>

      <footer className="app__footer">
        <p>{translator.t('disclaimer.full')}</p>
      </footer>
    </div>
  );
}
