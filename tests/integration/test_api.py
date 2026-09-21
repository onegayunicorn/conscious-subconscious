"""End-to-end tests of the HTTP service.

Skipped cleanly when the ``api`` extra is absent. The interesting assertions are
the security ones: authentication, rate limiting, body caps, and the fact that
there is no endpoint which writes tissue integrity.
"""

from __future__ import annotations

import contextlib

import pytest

fastapi = pytest.importorskip("fastapi", reason="install the 'api' extra to test the service")
from fastapi.testclient import TestClient  # noqa: E402

from conscious_subconscious.core.errors import ConfigurationError  # noqa: E402
from conscious_subconscious.services import Settings  # noqa: E402
from conscious_subconscious.services.api.app import create_app  # noqa: E402

API_KEY = "test-key"


def make_client(**overrides: object) -> TestClient:
    defaults: dict[str, object] = {
        "host": "127.0.0.1",
        "api_key": API_KEY,
        "rate_limit_per_minute": 500,
        "allowed_origins": ("http://localhost:5173",),
        "max_sessions": 8,
        "session_ttl_seconds": 3600.0,
    }
    defaults.update(overrides)
    return TestClient(create_app(Settings(**defaults)))  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    return make_client()


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": API_KEY}


class TestOps:
    def test_healthz_is_open(self, client: TestClient) -> None:
        assert client.get("/healthz").json()["status"] == "ok"

    def test_readyz_is_open(self, client: TestClient) -> None:
        body = client.get("/readyz").json()
        assert body["auth_enabled"] is True

    def test_metrics_are_prometheus_text(self, client: TestClient) -> None:
        response = client.get("/v1/metrics")
        assert response.status_code == 200
        assert "conscious_subconscious_" in response.text


class TestAuthentication:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/v1/meta"),
            ("get", "/v1/parameters"),
            ("get", "/v1/sessions"),
            ("post", "/v1/sessions"),
        ],
    )
    def test_protected_routes_reject_a_missing_key(
        self, client: TestClient, method: str, path: str
    ) -> None:
        response = getattr(client, method)(path)
        assert response.status_code == 401

    def test_protected_routes_reject_a_wrong_key(self, client: TestClient) -> None:
        assert client.get("/v1/meta", headers={"X-API-Key": "wrong"}).status_code == 401

    def test_correct_key_is_accepted(self, client: TestClient, auth: dict[str, str]) -> None:
        assert client.get("/v1/meta", headers=auth).status_code == 200

    def test_auth_can_be_disabled_on_loopback(self) -> None:
        open_client = make_client(api_key=None)
        assert open_client.get("/v1/meta").status_code == 200

    def test_every_v1_route_except_metrics_is_protected(self, client: TestClient) -> None:
        """A new route must not be able to be added without the guard.

        Repeating `dependencies=[Depends(guard)]` per route is easy to forget, so
        it is checked here rather than assumed.
        """
        schema = client.get("/openapi.json").json()
        unprotected: list[str] = []
        for path, operations in schema["paths"].items():
            if not path.startswith("/v1"):
                continue
            if path == "/v1/metrics":
                continue
            for method in operations:
                response = client.request(
                    method.upper(), path.replace("{session_id}", "x").replace("{locale}", "en")
                )
                if response.status_code != 401:
                    unprotected.append(f"{method.upper()} {path} -> {response.status_code}")
        assert not unprotected, "unprotected /v1 routes: " + ", ".join(unprotected)

    def test_public_bind_without_a_key_refuses_to_start(self) -> None:
        with pytest.raises(ConfigurationError):
            create_app(Settings(host="0.0.0.0", api_key=None))


class TestRateLimit:
    def test_requests_are_limited(self) -> None:
        limited = make_client(rate_limit_per_minute=3)
        headers = {"X-API-Key": API_KEY}
        statuses = [limited.get("/v1/meta", headers=headers).status_code for _ in range(5)]
        assert 429 in statuses

    def test_rate_limit_response_has_retry_after(self) -> None:
        limited = make_client(rate_limit_per_minute=1)
        headers = {"X-API-Key": API_KEY}
        limited.get("/v1/meta", headers=headers)
        response = limited.get("/v1/meta", headers=headers)
        assert "Retry-After" in response.headers


class TestBodySize:
    def test_oversized_body_is_rejected(self) -> None:
        tiny = make_client(max_body_bytes=32)
        response = tiny.post(
            "/v1/sessions",
            headers={"X-API-Key": API_KEY},
            json={"scenario": "baseline", "overrides": {"x.y": 1.0}},
        )
        assert response.status_code == 413


class TestCatalogue:
    def test_meta_reports_the_contract(self, client: TestClient, auth: dict[str, str]) -> None:
        body = client.get("/v1/meta", headers=auth).json()
        assert body["protocol_version"] == "1.0.0"
        assert "not a medical device" in body["disclaimer"]
        assert "neural_drive_coupling" not in str(body["auth"])

    def test_parameters_expose_provenance(self, client: TestClient, auth: dict[str, str]) -> None:
        body = client.get("/v1/parameters", headers=auth).json()
        assert body["summary"]["unsupported"] > 0
        assert all("provenance" in entry for entry in body["parameters"])

    def test_unsupported_only_filter(self, client: TestClient, auth: dict[str, str]) -> None:
        body = client.get("/v1/parameters?unsupported_only=true", headers=auth).json()
        assert all(entry["supported"] is False for entry in body["parameters"])

    def test_scenarios_expose_caveats(self, client: TestClient, auth: dict[str, str]) -> None:
        body = client.get("/v1/scenarios", headers=auth).json()
        assert all(scenario["caveat"] for scenario in body["scenarios"])

    def test_modules_and_devices(self, client: TestClient, auth: dict[str, str]) -> None:
        assert client.get("/v1/modules", headers=auth).json()["modules"]
        assert client.get("/v1/device-kinds", headers=auth).json()["devices"]
        assert client.get("/v1/pipeline-steps", headers=auth).json()["steps"]

    def test_i18n_catalog_is_served(self, client: TestClient, auth: dict[str, str]) -> None:
        body = client.get("/v1/i18n/en", headers=auth).json()
        assert body["strings"]["app.title"] == "conscious-subconscious"

    def test_unknown_locale_is_404(self, client: TestClient, auth: dict[str, str]) -> None:
        assert client.get("/v1/i18n/xx-YY", headers=auth).status_code == 404


class TestSessions:
    def test_create_returns_a_snapshot(self, client: TestClient, auth: dict[str, str]) -> None:
        response = client.post(
            "/v1/sessions",
            headers=auth,
            json={"scenario": "baseline", "dt_hours": 0.5, "horizon_hours": 4.0},
        )
        assert response.status_code == 201
        assert response.json()["snapshot"]["steps"] == 0

    def test_unknown_scenario_is_a_configuration_error(
        self, client: TestClient, auth: dict[str, str]
    ) -> None:
        response = client.post("/v1/sessions", headers=auth, json={"scenario": "nope"})
        assert response.status_code == 400

    def test_unknown_override_key_is_a_parameter_error(
        self, client: TestClient, auth: dict[str, str]
    ) -> None:
        response = client.post("/v1/sessions", headers=auth, json={"overrides": {"ghost.key": 1.0}})
        assert response.status_code == 400

    def test_extra_body_fields_are_rejected(self, client: TestClient, auth: dict[str, str]) -> None:
        """A typo'd field must be reported, not silently ignored."""
        response = client.post("/v1/sessions", headers=auth, json={"seeds": 1})
        assert response.status_code == 422

    def test_step_advances_and_reports(self, client: TestClient, auth: dict[str, str]) -> None:
        session_id = client.post(
            "/v1/sessions", headers=auth, json={"dt_hours": 0.5, "horizon_hours": 4.0}
        ).json()["id"]
        body = client.post(
            f"/v1/sessions/{session_id}/step", headers=auth, json={"count": 3}
        ).json()
        assert body["snapshot"]["steps"] == 3

    def test_run_and_fetch_result(self, client: TestClient, auth: dict[str, str]) -> None:
        session_id = client.post(
            "/v1/sessions", headers=auth, json={"dt_hours": 1.0, "horizon_hours": 4.0}
        ).json()["id"]
        assert client.get(f"/v1/sessions/{session_id}/result", headers=auth).status_code == 409
        run = client.post(f"/v1/sessions/{session_id}/run", headers=auth, json={}).json()
        assert run["metrics"]["samples"] == 4
        result = client.get(f"/v1/sessions/{session_id}/result", headers=auth).json()
        assert result["disclaimer"]

    def test_result_can_include_samples(self, client: TestClient, auth: dict[str, str]) -> None:
        session_id = client.post(
            "/v1/sessions", headers=auth, json={"dt_hours": 1.0, "horizon_hours": 3.0}
        ).json()["id"]
        client.post(f"/v1/sessions/{session_id}/run", headers=auth, json={})
        body = client.get(
            f"/v1/sessions/{session_id}/result?include_samples=true", headers=auth
        ).json()
        assert len(body["samples"]) == 3

    def test_commands_are_applied(self, client: TestClient, auth: dict[str, str]) -> None:
        session_id = client.post(
            "/v1/sessions", headers=auth, json={"dt_hours": 1.0, "horizon_hours": 4.0}
        ).json()["id"]
        body = client.post(
            f"/v1/sessions/{session_id}/commands", headers=auth, json={"command": "focus"}
        ).json()
        assert body["outcome"]["changed"] is True

    def test_set_policy_without_a_policy_is_rejected(
        self, client: TestClient, auth: dict[str, str]
    ) -> None:
        session_id = client.post("/v1/sessions", headers=auth, json={}).json()["id"]
        response = client.post(
            f"/v1/sessions/{session_id}/commands", headers=auth, json={"command": "set_policy"}
        )
        assert response.status_code == 422

    def test_there_is_no_endpoint_that_writes_integrity(
        self, client: TestClient, auth: dict[str, str]
    ) -> None:
        session_id = client.post("/v1/sessions", headers=auth, json={}).json()["id"]
        response = client.post(
            f"/v1/sessions/{session_id}/commands",
            headers=auth,
            json={"command": "set_integrity", "value": 1.0},
        )
        assert response.status_code == 422

    def test_unknown_session_is_404(self, client: TestClient, auth: dict[str, str]) -> None:
        assert client.get("/v1/sessions/deadbeef", headers=auth).status_code == 404

    def test_delete_then_get_is_404(self, client: TestClient, auth: dict[str, str]) -> None:
        session_id = client.post("/v1/sessions", headers=auth, json={}).json()["id"]
        assert client.delete(f"/v1/sessions/{session_id}", headers=auth).status_code == 204
        assert client.get(f"/v1/sessions/{session_id}", headers=auth).status_code == 404

    def test_session_capacity_is_enforced(self, auth: dict[str, str]) -> None:
        small = make_client(max_sessions=1)
        small.post("/v1/sessions", headers=auth, json={})
        assert small.post("/v1/sessions", headers=auth, json={}).status_code == 429

    def test_listing_sessions(self, client: TestClient, auth: dict[str, str]) -> None:
        client.post("/v1/sessions", headers=auth, json={})
        assert len(client.get("/v1/sessions", headers=auth).json()["sessions"]) == 1

    def test_metrics_for_a_session(self, client: TestClient, auth: dict[str, str]) -> None:
        session_id = client.post("/v1/sessions", headers=auth, json={}).json()["id"]
        body = client.get(f"/v1/sessions/{session_id}/metrics", headers=auth).json()
        assert body["tissue"]["integrity"] > 0


class TestStreaming:
    def test_snapshot_command_streams_one_tick(self, auth: dict[str, str]) -> None:
        client = make_client()
        session_id = client.post("/v1/sessions", headers=auth, json={}).json()["id"]
        with client.websocket_connect(f"/ws/v1/sessions/{session_id}?api_key={API_KEY}") as socket:
            socket.send_json({"command": "snapshot", "steps": 1})
            message = socket.receive_json()
            assert message["type"] == "sim.tick"
            assert message["session"] == session_id

    def test_step_command_streams_the_requested_count(self, auth: dict[str, str]) -> None:
        client = make_client()
        session_id = client.post(
            "/v1/sessions", headers=auth, json={"dt_hours": 1.0, "horizon_hours": 10.0}
        ).json()["id"]
        with client.websocket_connect(f"/ws/v1/sessions/{session_id}?api_key={API_KEY}") as socket:
            socket.send_json({"command": "step", "steps": 3})
            ticks = [socket.receive_json() for _ in range(3)]
            assert [tick["payload"]["t_hours"] for tick in ticks] == [1.0, 2.0, 3.0]

    def test_stream_requires_a_key(self) -> None:
        """An unauthenticated peer must never reach a connected state.

        Asserted on the observable outcome — no data delivered — rather than on a
        named exception, because the framework's refusal surfaces as a handshake
        error or a disconnect depending on version.
        """
        client = make_client()
        session_id = client.post("/v1/sessions", headers={"X-API-Key": API_KEY}, json={}).json()[
            "id"
        ]
        delivered: list[object] = []
        with (
            contextlib.suppress(Exception),
            client.websocket_connect(f"/ws/v1/sessions/{session_id}") as socket,
        ):
            delivered.append(socket.receive_json())
        assert delivered == []

    def test_unknown_stream_command_is_reported(self, auth: dict[str, str]) -> None:
        client = make_client()
        session_id = client.post("/v1/sessions", headers=auth, json={}).json()["id"]
        with client.websocket_connect(f"/ws/v1/sessions/{session_id}?api_key={API_KEY}") as socket:
            socket.send_json({"command": "teleport"})
            assert socket.receive_json()["type"] == "error"
