# Internationalisation

Message catalogs for the web console, the marketing site and any Python surface
that needs user-facing text.

## Where the files live

`i18n/locales/<locale>.json` is the **canonical** location. Translators edit
these files; nothing else needs to change.

The Python loader (`src/conscious_subconscious/i18n.py`) finds them by probing,
in order:

1. `$CS_LOCALES_DIR`, if set — used by the container image;
2. a `locales/` directory shipped beside the module — how a wheel carries them;
3. `i18n/locales` in a parent directory of the installed module — a repo checkout.

If none is found, the loader returns the **key** rather than an empty string, and
`catalog_status()` reports the problem. A missing translation must be visible,
and it must never break a simulation run.

## Locales

| Locale | Status |
|---|---|
| `en` | Reference. Every key is defined here. |
| `zh-Hans` | Complete; not reviewed by a native speaker. |
| `es` | Complete; not reviewed by a native speaker. |
| `ar` | Complete; not reviewed by a native speaker. |

**The non-English catalogs have not been reviewed by native speakers.** They were
produced as a first pass so the plumbing is real rather than theoretical. Treat
them as draft translations and expect terminology to change.

## Rules

- Flat, dotted keys (`field.integrity`, not nested objects). Flat keys diff
  cleanly in review and cannot be silently shadowed by a nested structure.
- Every key present in `en.json` must be present in every other catalog. Values
  are plain strings only — no numbers, arrays or nested objects.
- Placeholders use `{name}` and must exist in the English string too. A
  malformed placeholder is caught at render time and falls back to the raw
  template rather than raising.
- Do not translate the project name `conscious-subconscious`, parameter keys
  (`conscious.neural_drive_coupling`), channel names (`growth_factor`) or any
  identifier that appears in code or a URL.

## Checking parity

```bash
python3 tools/check_locales.py          # exit 1 on any mismatch
python3 tools/check_locales.py --json   # machine-readable
python3 tools/check_locales.py --sync   # add missing keys, copying English
```

`--sync` copies the English string for a missing key, which is deliberately the
least creative option: an untranslated string that is obviously English is
easier to spot than a machine-guessed one that looks finished.

The pre-commit hook and CI both run the parity check, so a catalog cannot drift
without somebody seeing it.
