import type { ReactElement } from 'react';

import keyVisual from './assets/key-visual.svg';
import mindTissue from './assets/mind-tissue-diagram.svg';
import {
  COMPARISON_ROWS,
  FEATURES,
  HERO,
  NOTS,
  QUICKSTART,
  REPOSITORY,
  STATS,
  SWEEP_ROWS,
} from './content';

/**
 * One page, no router, no analytics, no third-party scripts.
 *
 * The argument of this site is "we do not overclaim", so the disclaimer is in the
 * header, above the fold, and again in the footer — and every table carries a
 * caption naming the command that produced it.
 */
export function App(): ReactElement {
  const year = new Date().getFullYear();

  return (
    <div className="page">
      <header className="hero">
        <div className="hero__text">
          <p className="hero__eyebrow">open source · MIT · Python 3.10+</p>
          <h1 className="hero__title">
            conscious<span className="hero__dash">-</span>subconscious
          </h1>
          <p className="hero__tagline">{HERO.tagline}</p>
          <p className="hero__lede">{HERO.lede}</p>
          <p className="boundary" role="note">
            {HERO.boundary}
          </p>
          <div className="hero__actions">
            <a className="button button--primary" href={REPOSITORY} rel="noreferrer noopener">
              Source on GitHub
            </a>
            <a className="button" href="#numbers" rel="noreferrer noopener">
              See the numbers
            </a>
          </div>
        </div>
        <img
          className="hero__visual"
          src={keyVisual}
          alt="Diagram of two interacting signals: a steady homeostatic curve crossed by a focused attention pulse."
          width={800}
          height={450}
        />
      </header>

      <section className="stats" aria-label="Project facts">
        {STATS.map((stat) => (
          <div className="stat" key={stat.label}>
            <span className="stat__value mono">{stat.value}</span>
            <span className="stat__label">{stat.label}</span>
          </div>
        ))}
      </section>

      <section className="section" id="numbers">
        <h2 className="section__title">The awkward table</h2>
        <p className="section__lede">
          The model&apos;s headline result is that attention speeds repair. That result comes from a
          single constant with no empirical support. So the useful question is not &ldquo;is the
          effect big?&rdquo; but &ldquo;how much of the conclusion rests on a number nobody
          measured?&rdquo;
        </p>
        <div className="table-wrap">
          <table className="table">
            <caption>
              <span className="mono">cs-sim compare</span> — seed 20260921, dt 0.05 h, 72 h horizon.
              Times in hours; the last row is the control.
            </caption>
            <thead>
              <tr>
                <th scope="col">Scenario</th>
                <th scope="col">Time to 50% repair</th>
                <th scope="col">Area under damage</th>
                <th scope="col">Attention engaged</th>
                <th scope="col">Repair attributable to attention</th>
              </tr>
            </thead>
            <tbody>
              {COMPARISON_ROWS.map((row) => (
                <tr key={row.scenario} className={row.scenario === 'focused-uncoupled' ? 'row--control' : undefined}>
                  <th scope="row" className="mono">
                    {row.scenario}
                  </th>
                  <td className="mono">{row.timeTo50}</td>
                  <td className="mono">{row.area}</td>
                  <td className="mono">{row.focus}</td>
                  <td className="mono">{row.attributable}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section__note">
          <span className="mono">focused-uncoupled</span> holds attention exactly as the{' '}
          <span className="mono">focused</span> scenario does, with the coupling constant set to
          zero. Repair is identical to the baseline. It still spends 36.8 hours of attention. The
          speed-up above it is a property of one invented number.
        </p>
      </section>

      <section className="section">
        <h2 className="section__title">Vary the guess, watch the answer move</h2>
        <p className="section__lede">
          Holding everything else fixed and sweeping only the coupling constant:
        </p>
        <div className="table-wrap">
          <table className="table">
            <caption>
              <span className="mono">
                cs-sim sweep --param conscious.neural_drive_coupling --values 0:3:0.75
              </span>
            </caption>
            <thead>
              <tr>
                <th scope="col">neural_drive_coupling</th>
                <th scope="col">Time to 50% repair</th>
                <th scope="col">Area under damage</th>
                <th scope="col">Attributable to attention</th>
              </tr>
            </thead>
            <tbody>
              {SWEEP_ROWS.map((row) => (
                <tr key={row.coupling}>
                  <th scope="row" className="mono">
                    {row.coupling}
                  </th>
                  <td className="mono">{row.timeTo50}</td>
                  <td className="mono">{row.area}</td>
                  <td className="mono">{row.attributable}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section__note">
          A linear sweep from 0 to 3 takes the modelled repair time from 62 hours to 30.6 — and the
          curve continues in whichever direction the constant is set. The model cannot tell you
          where the true value sits, because the true value is not known, and the project does not
          pretend otherwise.
        </p>
      </section>

      <section className="section">
        <h2 className="section__title">How the model is built</h2>
        <img
          className="diagram"
          src={mindTissue}
          alt="Architecture diagram: the damaged tissue at the centre, the subconscious homeostatic loop on one side, the conscious attention loop on the other, and the mediator field between them."
          width={1200}
          height={700}
        />
        <ul className="features">
          {FEATURES.map((feature) => (
            <li className="feature" key={feature.title}>
              <h3 className="feature__title">{feature.title}</h3>
              <p className="feature__body">{feature.body}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="section">
        <h2 className="section__title">What it is not</h2>
        <ul className="nots">
          {NOTS.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="section">
        <h2 className="section__title">Run it</h2>
        <pre className="code">
          <code>{QUICKSTART}</code>
        </pre>
        <p className="section__note">
          The simulation core has no third-party runtime dependencies. If you want to reason about
          the model rather than run it, read{' '}
          <a href={`${REPOSITORY}/blob/main/docs/model-spec.md`}>docs/model-spec.md</a> — it maps
          every symbol to its parameter and its provenance grade.
        </p>
      </section>

      <footer className="footer">
        <p className="footer__boundary">{HERO.boundary}</p>
        <p className="footer__meta">
          MIT licensed · © {year} the conscious-subconscious contributors ·{' '}
          <a href={REPOSITORY} rel="noreferrer noopener">
            {REPOSITORY.replace('https://', '')}
          </a>
        </p>
        <p className="footer__meta">
          Not a medical device. No medical advice. Do not use any output of this project to make a
          decision about a human body.
        </p>
      </footer>
    </div>
  );
}
