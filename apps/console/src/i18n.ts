/**
 * Localisation for the console.
 *
 * The catalogs are copied from the repository's canonical `i18n/locales/` by
 * `scripts/sync-locales.mjs` at build time. English is the reference: every key
 * exists there, and a key missing elsewhere falls back to it.
 *
 * A missing key renders as the key itself, never as an empty string. That is
 * deliberately ugly — a blank label in a screenshot is easy to ship by accident,
 * `field.integrity` is not.
 */
import ar from './locales/ar.json';
import en from './locales/en.json';
import es from './locales/es.json';
import zhHans from './locales/zh-Hans.json';

export type Locale = 'en' | 'zh-Hans' | 'es' | 'ar';

const CATALOGS: Record<Locale, Record<string, string>> = {
  en: en as Record<string, string>,
  'zh-Hans': zhHans as Record<string, string>,
  es: es as Record<string, string>,
  ar: ar as Record<string, string>,
};

export const DEFAULT_LOCALE: Locale = 'en';

/** Locales with a bundled catalog, in the reference order. */
export const LOCALES: readonly Locale[] = ['en', 'zh-Hans', 'es', 'ar'];

/** Locale aliases so `zh-CN` in a browser preference resolves to `zh-Hans`. */
const ALIASES: Record<string, Locale> = {
  zh: 'zh-Hans',
  'zh-cn': 'zh-Hans',
  'zh-hans': 'zh-Hans',
  'zh-sg': 'zh-Hans',
  ar: 'ar',
  es: 'es',
  en: 'en',
};

/** Writing direction, so the interface can flip for Arabic. */
export function direction(locale: Locale): 'ltr' | 'rtl' {
  return locale === 'ar' ? 'rtl' : 'ltr';
}

export function isLocale(value: string): value is Locale {
  return (LOCALES as readonly string[]).includes(value);
}

/** Best-effort match of a browser language tag to a bundled locale. */
export function resolveLocale(tag: string | undefined): Locale {
  if (!tag) {
    return DEFAULT_LOCALE;
  }
  const normalised = tag.toLowerCase();
  if (isLocale(normalised)) {
    return normalised;
  }
  const exact = ALIASES[normalised];
  if (exact !== undefined) {
    return exact;
  }
  const base = normalised.split('-')[0] ?? '';
  return ALIASES[base] ?? DEFAULT_LOCALE;
}

export interface Translator {
  locale: Locale;
  /** Look up a key, interpolating `{name}` placeholders. */
  t: (key: string, fields?: Record<string, string | number>) => string;
}

/**
 * Build a translator for one locale.
 *
 * Interpolation is best-effort: a malformed placeholder returns the raw template
 * rather than throwing, because a missing translation should never take the
 * interface down.
 */
export function createTranslator(locale: Locale): Translator {
  const primary = CATALOGS[locale];
  const fallback = CATALOGS[DEFAULT_LOCALE];

  const t = (key: string, fields?: Record<string, string | number>): string => {
    const template = primary[key] ?? fallback[key] ?? key;
    if (fields === undefined) {
      return template;
    }
    return template.replace(/\{(\w+)\}/g, (match, name: string) => {
      const value = fields[name];
      return value === undefined ? match : String(value);
    });
  };

  return { locale, t };
}

/** Every key the console uses, for the parity script and developer reference. */
export function referenceKeys(): string[] {
  return Object.keys(CATALOGS[DEFAULT_LOCALE]).sort();
}
