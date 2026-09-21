"""Locale loading and message lookup.

The catalogs live at ``i18n/locales/`` in the repository root so translators can
work without touching Python. This module finds them by probing, in order:

1. ``$CS_LOCALES_DIR`` — an explicit directory (used by the container image);
2. a ``locales/`` directory beside this module — how a wheel ships them;
3. ``i18n/locales`` in this file's parent directories — a repo checkout.

If none is found, :func:`translate` still works: it returns the key itself, and
:func:`catalog_status` reports the problem. A missing translation must never
crash a simulation run, but it must also never be invisible.
"""

from __future__ import annotations

import functools
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .core.errors import ConfigurationError

__all__ = [
    "DEFAULT_LOCALE",
    "translate",
    "available_locales",
    "load_catalog",
    "catalog_status",
    "missing_keys",
    "parity_report",
    "locales_directory",
    "clear_cache",
]

DEFAULT_LOCALE = "en"

#: Lookup order when a key is absent: exact locale, then its base language, then English.
_BASE_LANGUAGE_ALIASES: Mapping[str, str] = {
    "zh": "zh-Hans",
    "zh-cn": "zh-Hans",
    "zh-hans": "zh-Hans",
    "zh-tw": "zh-Hant",
}


def locales_directory() -> Path | None:
    """Locate the catalog directory, or ``None`` if it is not present."""
    override = os.environ.get("CS_LOCALES_DIR")
    if override:
        candidate = Path(override)
        return candidate if candidate.is_dir() else None

    beside = Path(__file__).resolve().parent / "locales"
    if beside.is_dir():
        return beside

    for parent in Path(__file__).resolve().parents:
        candidate = parent / "i18n" / "locales"
        if candidate.is_dir():
            return candidate
    return None


def _catalog_files() -> dict[str, Path]:
    directory = locales_directory()
    if directory is None:
        return {}
    return {path.stem: path for path in sorted(directory.glob("*.json"))}


@functools.lru_cache(maxsize=32)
def load_catalog(locale: str = DEFAULT_LOCALE) -> dict[str, str]:
    """Load one catalog. Returns an empty mapping when the locale is unknown."""
    files = _catalog_files()
    path = files.get(locale)
    if path is None:
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigurationError(f"{path} must contain a JSON object of key -> string")
    catalog: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise ConfigurationError(f"{path}: keys must be strings, found {key!r}")
        if not isinstance(value, str):
            raise ConfigurationError(f"{path}: value for {key!r} must be a string")
        catalog[key] = value
    return catalog


def available_locales() -> tuple[str, ...]:
    """Every locale with a catalog, English first."""
    names = sorted(_catalog_files())
    if DEFAULT_LOCALE in names:
        names.remove(DEFAULT_LOCALE)
        names.insert(0, DEFAULT_LOCALE)
    return tuple(names)


def _chain(locale: str) -> tuple[str, ...]:
    """Locales consulted for ``locale``, in order."""
    chain: list[str] = [locale]
    base = locale.split("-")[0].lower()
    alias = _BASE_LANGUAGE_ALIASES.get(locale.lower()) or _BASE_LANGUAGE_ALIASES.get(base)
    if alias and alias not in chain:
        chain.append(alias)
    if DEFAULT_LOCALE not in chain:
        chain.append(DEFAULT_LOCALE)
    return tuple(chain)


def translate(key: str, locale: str = DEFAULT_LOCALE, **fields: Any) -> str:
    """Look up ``key`` and interpolate ``fields``.

    Falls back through the locale chain and finally returns the key itself, so a
    missing translation shows up as an obviously-wrong string rather than an
    empty one.
    """
    if not key:
        raise ConfigurationError("translation key must be non-empty")
    template: str | None = None
    for candidate in _chain(locale):
        value = load_catalog(candidate).get(key)
        if value is not None:
            template = value
            break
    if template is None:
        return key
    if not fields:
        return template
    try:
        return template.format(**fields)
    except (KeyError, IndexError, ValueError):
        # A malformed placeholder must not take the process down.
        return template


def missing_keys(locale: str, *, reference: str = DEFAULT_LOCALE) -> tuple[str, ...]:
    """Keys present in ``reference`` but absent from ``locale``."""
    reference_keys = set(load_catalog(reference))
    return tuple(sorted(reference_keys - set(load_catalog(locale))))


def catalog_status() -> dict[str, Any]:
    """Report where the catalogs were found, and whether they are usable.

    Surfaced by the health endpoint and by ``cs-sim`` diagnostics. A deployment
    that ships without its catalogs is not broken — it simply renders keys — and
    that is the kind of thing nobody notices until a screenshot is published.
    """
    directory = locales_directory()
    reference = load_catalog(DEFAULT_LOCALE)
    return {
        "directory": str(directory) if directory is not None else None,
        "found": directory is not None,
        "reference": DEFAULT_LOCALE,
        "reference_key_count": len(reference),
        "locales": list(available_locales()),
        "healthy": bool(reference),
        "hint": (
            None
            if reference
            else (
                "no catalogs found: set CS_LOCALES_DIR, or ship a locales/ directory "
                "beside the module"
            )
        ),
    }


def parity_report() -> dict[str, Any]:
    """Compare every catalog against the reference and report the differences."""
    reference = load_catalog(DEFAULT_LOCALE)
    report: dict[str, Any] = {
        "directory": str(locales_directory()) if locales_directory() else None,
        "reference": DEFAULT_LOCALE,
        "reference_key_count": len(reference),
        "locales": {},
    }
    for locale in available_locales():
        catalog = load_catalog(locale)
        missing = sorted(set(reference) - set(catalog))
        extra = sorted(set(catalog) - set(reference))
        report["locales"][locale] = {
            "key_count": len(catalog),
            "missing": missing,
            "extra": extra,
            "in_sync": not missing and not extra,
        }
    return report


def clear_cache() -> None:
    """Drop cached catalogs. Used by tests after writing a temporary catalog."""
    load_catalog.cache_clear()
