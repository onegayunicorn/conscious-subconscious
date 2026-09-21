import type { ReactElement } from 'react';

import { LOCALES, createTranslator, type Locale, type Translator } from '../i18n';
import type { ConnectionState } from '../hooks/useSimulation';
import { classNames } from '../lib/format';

export interface ControlsProps {
  connection: ConnectionState;
  busy: boolean;
  scenario: string;
  policy: string;
  locale: Locale;
  scenarios: readonly string[];
  onScenarioChange: (scenario: string) => void;
  onPolicyChange: (policy: string) => void;
  onLocaleChange: (locale: Locale) => void;
  onStart: () => void;
  onStep: () => void;
  onRun: () => void;
  onFocus: () => void;
  onRelease: () => void;
  onReset: () => void;
  t: Translator['t'];
}

export function Controls({
  connection,
  busy,
  scenario,
  policy,
  locale,
  scenarios,
  onScenarioChange,
  onPolicyChange,
  onLocaleChange,
  onStart,
  onStep,
  onRun,
  onFocus,
  onRelease,
  onReset,
  t,
}: ControlsProps): ReactElement {
  const disabled = busy || connection === 'streaming';

  return (
    <form className="controls" onSubmit={(event) => event.preventDefault()}>
      <div className="controls__group">
        <label className="field">
          <span className="field__label">Scenario</span>
          <select
            className="field__input mono"
            value={scenario}
            disabled={disabled}
            onChange={(event) => onScenarioChange(event.target.value)}
          >
            {scenarios.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Focus policy</span>
          <select
            className="field__input mono"
            value={policy}
            disabled={disabled}
            onChange={(event) => onPolicyChange(event.target.value)}
          >
            {['never', 'always', 'intermittent'].map((name) => (
              <option key={name} value={name}>
                {t(`policy.${name}`)}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span className="field__label">Language</span>
          <select
            className="field__input mono"
            value={locale}
            onChange={(event) => onLocaleChange(event.target.value as Locale)}
          >
            {LOCALES.map((code) => (
              <option key={code} value={code}>
                {code}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="controls__group controls__group--actions">
        <button type="button" className="button button--primary" onClick={onStart} disabled={busy}>
          {connection === 'streaming' ? t('action.pause') : t('action.start')}
        </button>
        <button type="button" className="button" onClick={onStep} disabled={busy}>
          {t('action.step')}
        </button>
        <button type="button" className="button" onClick={onRun} disabled={busy}>
          {t('action.run')}
        </button>
        <button type="button" className="button" onClick={onFocus} disabled={busy}>
          {t('action.focus')}
        </button>
        <button type="button" className="button" onClick={onRelease} disabled={busy}>
          {t('action.release')}
        </button>
        <button type="button" className="button button--quiet" onClick={onReset} disabled={busy}>
          {t('action.reset')}
        </button>
      </div>

      <p className={classNames('status', `status--${connection}`)}>
        <span className="status__dot" aria-hidden="true" />
        {t(`state.${connection === 'offline' ? 'error' : connection === 'paused' ? 'paused' : connection === 'streaming' ? 'running' : connection === 'complete' ? 'complete' : connection === 'error' ? 'error' : 'idle'}`)}
      </p>
    </form>
  );
}

/** Placeholder translator used before a locale is chosen. */
export const fallbackTranslator = createTranslator('en');
