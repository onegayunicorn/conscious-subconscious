#!/usr/bin/env python3
"""Check (and optionally repair) locale catalog parity.

Every locale must define exactly the keys the reference locale defines. A
missing key falls back to English at runtime, which is fine; a missing key that
*looks* translated is not, because nobody notices it until a screenshot is in a
release note.

Exit codes: 0 = in sync, 1 = drift, 2 = could not run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOCALES_DIR = ROOT / "i18n" / "locales"
REFERENCE = "en"


def load(path: Path) -> dict[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    for key, value in data.items():
        if not isinstance(value, str):
            raise ValueError(f"{path}: value for {key!r} must be a string")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--sync",
        action="store_true",
        help="add missing keys to each catalog, copying the reference string",
    )
    args = parser.parse_args(argv)

    if not LOCALES_DIR.is_dir():
        print(f"locales directory not found: {LOCALES_DIR}", file=sys.stderr)
        return 2

    catalogs = {path.stem: path for path in sorted(LOCALES_DIR.glob("*.json"))}
    if REFERENCE not in catalogs:
        print(f"reference catalog {REFERENCE}.json is missing from {LOCALES_DIR}", file=sys.stderr)
        return 2

    reference = load(catalogs[REFERENCE])
    report: dict[str, dict[str, object]] = {}
    drifted = False

    for locale, path in catalogs.items():
        if locale == REFERENCE:
            continue
        catalog = load(path)
        missing = sorted(set(reference) - set(catalog))
        extra = sorted(set(catalog) - set(reference))
        unused = sorted(
            key
            for key, value in catalog.items()
            if "{" not in value and "{" in reference.get(key, "")
        )
        if missing or extra:
            drifted = True
        if args.sync and missing:
            merged = dict(catalog)
            for key in missing:
                merged[key] = reference[key]
            path.write_text(
                json.dumps(dict(sorted(merged.items())), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        report[locale] = {
            "key_count": len(catalog),
            "missing": missing,
            "extra": extra,
            "missing_placeholders": unused,
        }

    if args.json:
        print(
            json.dumps(
                {
                    "reference": REFERENCE,
                    "reference_key_count": len(reference),
                    "locales": report,
                    "in_sync": not drifted,
                },
                indent=2,
            )
        )
    else:
        print(f"reference: {REFERENCE} ({len(reference)} keys)")
        for locale, entry in report.items():
            status = "OK" if not entry["missing"] and not entry["extra"] else "DRIFT"
            print(
                f"  {locale:<10} {status:<6} keys={entry['key_count']} "
                f"missing={len(entry['missing'])} extra={len(entry['extra'])}"
            )
            for key in entry["missing"]:
                print(f"      missing: {key}")
            for key in entry["extra"]:
                print(f"      extra:   {key}")
            for key in entry["missing_placeholders"]:
                print(f"      placeholder not present in translation: {key}")
        if args.sync and drifted:
            print("\ncatalogs updated; review the copied English strings.")
        elif drifted:
            print("\nrun with --sync to add the missing keys as English placeholders.")

    return 1 if (drifted and not args.sync) else 0


if __name__ == "__main__":
    raise SystemExit(main())
