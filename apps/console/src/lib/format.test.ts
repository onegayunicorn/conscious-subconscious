import { describe, expect, it } from 'vitest';

import {
  EM_DASH,
  clamp,
  classNames,
  downsample,
  formatHours,
  formatNumber,
  formatPercent,
  formatTimestamp,
} from './format';
import { createTranslator, direction, resolveLocale } from '../i18n';

describe('formatNumber', () => {
  it('renders an absent value as an em dash, not zero', () => {
    // This is the whole point of the module: null and 0 are different statements.
    expect(formatNumber(null)).toBe(EM_DASH);
    expect(formatNumber(undefined)).toBe(EM_DASH);
    expect(formatNumber(Number.NaN)).toBe(EM_DASH);
    expect(formatNumber(Number.POSITIVE_INFINITY)).toBe(EM_DASH);
  });

  it('renders zero as zero', () => {
    expect(formatNumber(0)).toBe('0');
  });

  it('trims trailing zeros', () => {
    expect(formatNumber(1.5)).toBe('1.5');
    expect(formatNumber(2)).toBe('2');
  });

  it('switches to exponential notation at the extremes', () => {
    expect(formatNumber(1_500_000)).toContain('e');
    expect(formatNumber(0.0000001)).toContain('e');
  });
});

describe('formatHours and formatPercent', () => {
  it('appends units only when there is a value', () => {
    expect(formatHours(12.5)).toBe('12.5 h');
    expect(formatHours(null)).toBe(EM_DASH);
    expect(formatPercent(0.1447)).toBe('14.5%');
    expect(formatPercent(null)).toBe(EM_DASH);
  });
});

describe('formatTimestamp', () => {
  it('renders an em dash for unusable input', () => {
    expect(formatTimestamp('not a date')).toBe(EM_DASH);
  });

  it('renders a real timestamp', () => {
    expect(formatTimestamp('2026-09-21T12:00:00Z')).not.toBe(EM_DASH);
  });
});

describe('classNames', () => {
  it('drops falsy entries', () => {
    expect(classNames('a', false, null, undefined, 'b')).toBe('a b');
  });
});

describe('downsample', () => {
  it('keeps short series intact', () => {
    expect(downsample([1, 2, 3], 10)).toEqual([1, 2, 3]);
  });

  it('reduces to the limit', () => {
    const points = Array.from({ length: 1000 }, (_, index) => index);
    expect(downsample(points, 50)).toHaveLength(50);
  });

  it('always keeps the final point', () => {
    const points = Array.from({ length: 100 }, (_, index) => index);
    const sampled = downsample(points, 10);
    expect(sampled[sampled.length - 1]).toBe(99);
  });

  it('rejects a non-positive limit', () => {
    expect(() => downsample([1, 2, 3], 0)).toThrow();
  });
});

describe('clamp', () => {
  it('confines a value to a range', () => {
    expect(clamp(5, 0, 1)).toBe(1);
    expect(clamp(-5, 0, 1)).toBe(0);
    expect(clamp(0.5, 0, 1)).toBe(0.5);
  });
});

describe('i18n', () => {
  it('resolves browser tags to a bundled locale', () => {
    expect(resolveLocale('zh-CN')).toBe('zh-Hans');
    expect(resolveLocale('en-GB')).toBe('en');
    expect(resolveLocale('es-419')).toBe('es');
    expect(resolveLocale('de-DE')).toBe('en');
    expect(resolveLocale(undefined)).toBe('en');
  });

  it('translates a known key', () => {
    expect(createTranslator('en').t('app.title')).toBe('conscious-subconscious');
  });

  it('returns the key when it is missing, never an empty string', () => {
    expect(createTranslator('en').t('nope.not.here')).toBe('nope.not.here');
  });

  it('interpolates placeholders', () => {
    const rendered = createTranslator('en').t('provenance.banner', {
      unsupported: 33,
      total: 34,
    });
    expect(rendered).toContain('33');
    expect(rendered).toContain('34');
  });

  it('leaves unknown placeholders alone instead of throwing', () => {
    expect(() => createTranslator('en').t('provenance.banner')).not.toThrow();
  });

  it('translates into the other locales', () => {
    expect(createTranslator('zh-Hans').t('field.integrity')).not.toBe(
      createTranslator('en').t('field.integrity'),
    );
  });

  it('reports right-to-left for Arabic', () => {
    expect(direction('ar')).toBe('rtl');
    expect(direction('en')).toBe('ltr');
  });
});
