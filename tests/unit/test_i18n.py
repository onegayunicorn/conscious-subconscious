"""Localisation: catalog discovery, parity, lookup and fallback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conscious_subconscious.core.errors import ConfigurationError
from conscious_subconscious.i18n import (
    DEFAULT_LOCALE,
    available_locales,
    catalog_status,
    clear_cache,
    load_catalog,
    locales_directory,
    missing_keys,
    parity_report,
    translate,
)


class TestCatalogs:
    def test_directory_is_found(self) -> None:
        assert locales_directory() is not None

    def test_english_is_first(self) -> None:
        assert available_locales()[0] == DEFAULT_LOCALE

    def test_expected_locales_ship(self) -> None:
        assert {"en", "zh-Hans", "es", "ar"}.issubset(set(available_locales()))

    def test_english_catalog_is_non_trivial(self) -> None:
        assert len(load_catalog("en")) >= 50

    def test_unknown_locale_returns_an_empty_catalog(self) -> None:
        assert load_catalog("xx-YY") == {}

    def test_parity_holds_across_every_locale(self) -> None:
        report = parity_report()
        for locale, entry in report["locales"].items():
            assert entry["missing"] == [], f"{locale} is missing keys"
            assert entry["extra"] == [], f"{locale} has unknown keys"

    def test_missing_keys_helper_agrees_with_the_report(self) -> None:
        assert missing_keys("en") == ()

    def test_every_value_is_a_string(self) -> None:
        for locale in available_locales():
            for key, value in load_catalog(locale).items():
                assert isinstance(value, str), f"{locale}:{key}"

    def test_placeholders_match_english(self) -> None:
        """A translation that drops {total} renders a sentence with a hole in it."""
        reference = load_catalog("en")
        for locale in available_locales():
            for key, value in load_catalog(locale).items():
                expected = reference[key].count("{")
                assert value.count("{") == expected, f"{locale}:{key} placeholder count differs"


class TestTranslate:
    def test_looks_up_a_known_key(self) -> None:
        assert translate("app.title") == "conscious-subconscious"

    def test_returns_the_key_when_missing(self) -> None:
        """A missing translation must be obvious, not an empty string."""
        assert translate("this.key.does.not.exist") == "this.key.does.not.exist"

    def test_interpolates_fields(self) -> None:
        rendered = translate("provenance.banner", unsupported=30, total=34)
        assert "30" in rendered and "34" in rendered

    def test_malformed_placeholder_falls_back_to_the_template(self) -> None:
        """A bad placeholder must not take the process down."""
        rendered = translate("provenance.banner")
        assert "{" in rendered

    def test_unknown_fields_are_ignored(self) -> None:
        assert translate("app.title", unused="x") == "conscious-subconscious"

    def test_falls_back_to_english_for_a_partial_locale(self) -> None:
        # zh-CN is not shipped; the alias must resolve to zh-Hans.
        assert translate("app.title", "zh-CN") == translate("app.title", "zh-Hans")

    def test_unknown_locale_falls_back_to_english(self) -> None:
        assert translate("field.integrity", "xx-YY") == translate("field.integrity", "en")

    def test_translations_differ_from_english_where_expected(self) -> None:
        assert translate("field.integrity", "zh-Hans") != translate("field.integrity", "en")

    def test_rejects_an_empty_key(self) -> None:
        with pytest.raises(ConfigurationError):
            translate("")


class TestCatalogStatus:
    def test_status_reports_the_directory(self) -> None:
        status = catalog_status()
        assert status["reference"] == DEFAULT_LOCALE
        assert status["reference_key_count"] > 0

    def test_invalid_json_is_reported_not_swallowed(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
        monkeypatch.setenv("CS_LOCALES_DIR", str(tmp_path))
        clear_cache()
        try:
            with pytest.raises(ConfigurationError):
                load_catalog("broken")
        finally:
            monkeypatch.delenv("CS_LOCALES_DIR", raising=False)
            clear_cache()

    def test_non_string_values_are_rejected(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "bad.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
        monkeypatch.setenv("CS_LOCALES_DIR", str(tmp_path))
        clear_cache()
        try:
            with pytest.raises(ConfigurationError):
                load_catalog("bad")
        finally:
            monkeypatch.delenv("CS_LOCALES_DIR", raising=False)
            clear_cache()

    def test_env_var_override_is_honoured(self, tmp_path: Path, monkeypatch) -> None:
        (tmp_path / "en.json").write_text(json.dumps({"only.key": "value"}), encoding="utf-8")
        monkeypatch.setenv("CS_LOCALES_DIR", str(tmp_path))
        clear_cache()
        try:
            assert locales_directory() == tmp_path
            assert load_catalog("en") == {"only.key": "value"}
            assert translate("only.key") == "value"
        finally:
            monkeypatch.delenv("CS_LOCALES_DIR", raising=False)
            clear_cache()

    def test_missing_directory_is_survivable(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv("CS_LOCALES_DIR", str(tmp_path / "absent"))
        clear_cache()
        try:
            assert locales_directory() is None
            assert load_catalog("en") == {}
            assert translate("app.title") == "app.title"
        finally:
            monkeypatch.delenv("CS_LOCALES_DIR", raising=False)
            clear_cache()
