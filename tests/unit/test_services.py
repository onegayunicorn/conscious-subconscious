"""Service layer: redaction, auth, rate limiting, sessions, telemetry.

These are testable without FastAPI, which is the point of keeping the HTTP
application in its own subpackage behind an optional extra.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from conscious_subconscious.core.errors import ConfigurationError
from conscious_subconscious.model.engine import RunConfig
from conscious_subconscious.services import (
    ApiKeyAuth,
    Metrics,
    RateLimiter,
    SessionLimitReached,
    SessionManager,
    SessionNotFound,
    Settings,
    StandardCounters,
    assert_safe_bind,
    is_loopback,
    load_settings,
    redact,
    redact_mapping,
    render_prometheus,
)

# Built by concatenation so this test file does not itself look like a leak.
FAKE_GITHUB_PAT = "github_pat_" + "A" * 24
FAKE_GH_CLASSIC = "ghp_" + "b" * 24
FAKE_AWS = "AKIA" + "Q" * 16
FAKE_OPENAI = "sk-" + "c" * 32


class TestRedaction:
    @pytest.mark.parametrize(
        "secret",
        [FAKE_GITHUB_PAT, FAKE_GH_CLASSIC, FAKE_AWS, FAKE_OPENAI],
    )
    def test_masks_credential_shapes(self, secret: str) -> None:
        assert secret not in redact(f"the value is {secret} ok")

    def test_masks_bearer_tokens(self) -> None:
        assert "abcdefghijklmnopqrst" not in redact("Authorization: Bearer abcdefghijklmnopqrst")

    def test_masks_private_key_headers(self) -> None:
        assert "BEGIN RSA PRIVATE KEY" not in redact("-----BEGIN RSA PRIVATE KEY-----\nabc")

    def test_masks_assigned_secrets(self) -> None:
        assert "hunter2hunter2hunter2" not in redact("password=hunter2hunter2hunter2")

    def test_leaves_ordinary_text_alone(self) -> None:
        text = "the tissue reached 0.8 integrity after 30 hours"
        assert redact(text) == text

    def test_type_annotations_are_not_secrets(self) -> None:
        """A pattern that fires on `api_key: str` would be useless in practice."""
        text = "api_key: str | None = None"
        assert redact(text) == text

    def test_empty_input_is_safe(self) -> None:
        assert redact("") == ""

    def test_mapping_is_redacted_recursively(self) -> None:
        payload = {"outer": {"token": FAKE_OPENAI}, "list": [FAKE_AWS]}
        cleaned = redact_mapping(payload)
        assert FAKE_OPENAI not in str(cleaned)
        assert FAKE_AWS not in str(cleaned)

    def test_mapping_depth_is_bounded(self) -> None:
        deep: dict[str, object] = {"value": "leaf"}
        for _ in range(20):
            deep = {"nested": deep}
        assert "_truncated" in str(redact_mapping(deep))


class TestApiKeyAuth:
    def test_disabled_when_no_key_configured(self) -> None:
        auth = ApiKeyAuth(key=None)
        assert auth.enabled is False
        assert auth.check(None) is True

    def test_enabled_rejects_a_missing_key(self) -> None:
        auth = ApiKeyAuth(key="s3cret")
        assert auth.check(None) is False

    def test_enabled_rejects_a_wrong_key(self) -> None:
        assert ApiKeyAuth(key="s3cret").check("wrong") is False

    def test_enabled_accepts_the_right_key(self) -> None:
        assert ApiKeyAuth(key="s3cret").check("s3cret") is True

    def test_describe_never_echoes_the_key(self) -> None:
        assert "s3cret" not in str(ApiKeyAuth(key="s3cret").describe())


class TestRateLimiter:
    def test_allows_up_to_the_limit_then_denies(self) -> None:
        limiter = RateLimiter(per_minute=3, clock=lambda: 0.0)
        assert all(limiter.check("c").allowed for _ in range(3))
        assert limiter.check("c").allowed is False

    def test_retry_after_is_positive_when_denied(self) -> None:
        limiter = RateLimiter(per_minute=1, clock=lambda: 0.0)
        limiter.check("c")
        decision = limiter.check("c")
        assert decision.retry_after_seconds > 0

    def test_window_slides(self) -> None:
        now = [0.0]
        limiter = RateLimiter(per_minute=1, clock=lambda: now[0])
        limiter.check("c")
        assert limiter.check("c").allowed is False
        now[0] = 61.0
        assert limiter.check("c").allowed is True

    def test_clients_are_independent(self) -> None:
        limiter = RateLimiter(per_minute=1, clock=lambda: 0.0)
        limiter.check("a")
        assert limiter.check("b").allowed is True

    def test_remaining_decreases(self) -> None:
        limiter = RateLimiter(per_minute=5, clock=lambda: 0.0)
        assert limiter.check("c").remaining == 4

    def test_reset_clears_state(self) -> None:
        limiter = RateLimiter(per_minute=1, clock=lambda: 0.0)
        limiter.check("c")
        limiter.reset()
        assert limiter.check("c").allowed is True

    def test_rejects_a_non_positive_limit(self) -> None:
        with pytest.raises(ConfigurationError):
            RateLimiter(per_minute=0)


class TestBindSafety:
    @pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
    def test_loopback_detection(self, host: str) -> None:
        assert is_loopback(host)

    def test_non_loopback_detection(self) -> None:
        assert not is_loopback("0.0.0.0")
        assert not is_loopback("10.0.0.5")

    def test_loopback_without_a_key_is_allowed(self) -> None:
        assert_safe_bind(host="127.0.0.1", api_key=None)

    def test_public_bind_without_a_key_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="CS_API_KEY"):
            assert_safe_bind(host="0.0.0.0", api_key=None)

    def test_public_bind_with_a_key_is_allowed(self) -> None:
        assert_safe_bind(host="0.0.0.0", api_key="s3cret")


class TestSettings:
    def test_defaults_are_local_and_closed(self) -> None:
        settings = load_settings({})
        assert settings.host == "127.0.0.1"
        assert settings.auth_enabled is False

    def test_wildcard_origin_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError, match="must not contain"):
            load_settings({"CS_ALLOWED_ORIGINS": "*"})

    def test_origin_list_is_split(self) -> None:
        settings = load_settings({"CS_ALLOWED_ORIGINS": "https://a.example,https://b.example"})
        assert settings.allowed_origins == ("https://a.example", "https://b.example")

    def test_non_numeric_integer_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            load_settings({"CS_PORT": "http"})

    def test_describe_never_echoes_the_key(self) -> None:
        described = str(load_settings({"CS_API_KEY": "s3cret"}).describe())
        assert "s3cret" not in described
        assert "api_key_configured" in described


class TestSessionManager:
    def test_create_and_get(self) -> None:
        manager = SessionManager()
        session = manager.create()
        assert manager.get(session.id) is session

    def test_unknown_session_raises(self) -> None:
        with pytest.raises(SessionNotFound):
            SessionManager().get("nope")

    def test_delete_removes(self) -> None:
        manager = SessionManager()
        session = manager.create()
        manager.delete(session.id)
        assert len(manager) == 0
        with pytest.raises(SessionNotFound):
            manager.delete(session.id)

    def test_capacity_is_enforced(self) -> None:
        manager = SessionManager(max_sessions=1)
        manager.create()
        with pytest.raises(SessionLimitReached):
            manager.create()

    def test_idle_sessions_are_reaped(self) -> None:
        manager = SessionManager(ttl_seconds=60.0)
        session = manager.create()
        session.last_access = datetime.now(timezone.utc) - timedelta(seconds=120)
        assert manager.reap() == (session.id,)
        assert len(manager) == 0

    def test_fresh_sessions_are_not_reaped(self) -> None:
        manager = SessionManager(ttl_seconds=60.0)
        manager.create()
        assert manager.reap() == ()

    def test_reap_frees_capacity(self) -> None:
        manager = SessionManager(max_sessions=1, ttl_seconds=60.0)
        session = manager.create()
        session.last_access = datetime.now(timezone.utc) - timedelta(seconds=120)
        assert manager.create() is not None

    def test_step_advances_the_session(self) -> None:
        manager = SessionManager()
        session = manager.create(RunConfig(horizon_hours=1.0, dt_hours=0.5))
        state = manager.step(session.id)
        assert state["t_hours"] == 0.5

    def test_run_and_result(self) -> None:
        manager = SessionManager()
        session = manager.create(RunConfig(horizon_hours=2.0, dt_hours=0.5))
        assert manager.result(session.id) is None
        result = manager.run(session.id)
        assert result.metrics["samples"] == 4
        assert manager.result(session.id) is not None

    def test_command_is_counted(self) -> None:
        manager = SessionManager()
        session = manager.create(RunConfig(horizon_hours=1.0))
        manager.step(session.id)
        manager.command(session.id, "focus")
        assert session.commands_applied == 1

    def test_snapshot_includes_the_id(self) -> None:
        manager = SessionManager()
        session = manager.create()
        assert manager.snapshot(session.id)["id"] == session.id

    def test_ids_are_unique(self) -> None:
        manager = SessionManager()
        assert manager.create().id != manager.create().id

    def test_rejects_an_invalid_capacity(self) -> None:
        with pytest.raises(ConfigurationError):
            SessionManager(max_sessions=0)

    def test_rejects_a_non_positive_ttl(self) -> None:
        with pytest.raises(ConfigurationError):
            SessionManager(ttl_seconds=0.0)


class TestTelemetry:
    def test_counter_accumulates(self) -> None:
        metrics = Metrics()
        metrics.inc("requests_total", "requests", 2.0, reason="200")
        metrics.inc("requests_total", "requests", 1.0, reason="200")
        assert metrics.counter_value("requests_total", reason="200") == 3.0

    def test_gauge_is_set_not_accumulated(self) -> None:
        metrics = Metrics()
        metrics.set("sessions_open", 3.0)
        metrics.set("sessions_open", 1.0)
        assert metrics.gauge_value("sessions_open") == 1.0

    def test_render_includes_help_type_and_labels(self) -> None:
        metrics = Metrics()
        metrics.inc("requests_total", "HTTP requests handled.", 1.0, reason="200")
        rendered = render_prometheus(metrics)
        assert "# HELP conscious_subconscious_requests_total" in rendered
        assert "# TYPE conscious_subconscious_requests_total counter" in rendered
        assert 'reason="200"' in rendered

    def test_label_values_are_escaped(self) -> None:
        metrics = Metrics()
        metrics.inc("odd_total", "", 1.0, note='a"b')
        assert '\\"' in render_prometheus(metrics)

    def test_conflicting_help_text_is_rejected(self) -> None:
        metrics = Metrics()
        metrics.inc("x_total", "first")
        with pytest.raises(ConfigurationError):
            metrics.inc("x_total", "second")

    def test_empty_metric_name_is_rejected(self) -> None:
        with pytest.raises(ConfigurationError):
            Metrics().inc("")

    def test_standard_counters_render(self) -> None:
        counters = StandardCounters()
        counters.record_request("200")
        counters.steps_total = 5
        rendered = render_prometheus(counters.as_metrics(sessions_open=1))
        assert "conscious_subconscious_steps_total 5" in rendered

    def test_snapshot_is_flat_and_carries_labels(self) -> None:
        metrics = Metrics()
        metrics.inc("a_total", "", 1.0, label="x")
        snapshot = metrics.snapshot()
        assert snapshot == {'a_total{label="x"}': 1.0}


class TestSettingsIsFrozen:
    def test_settings_cannot_be_mutated(self) -> None:
        settings = Settings()
        with pytest.raises(FrozenInstanceError):
            settings.port = 9999  # type: ignore[misc]
