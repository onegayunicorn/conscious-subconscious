"""The HTTP application.

Design notes
------------
* ``create_app`` is a factory so tests can build an app with explicit settings
  and no environment.
* Authentication, rate limiting and body-size limits are applied as dependencies
  and middleware in one place, at construction. A service whose security posture
  depends on remembering a decorator on each route is one forgotten decorator
  away from being open.
* Errors never echo raw caller input without redaction.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

from ... import DISCLAIMER, PROVENANCE_POLICY, __version__
from ...core.errors import ConfigurationError, ConsciousSubconsciousError
from ...devices.registry import describe_all as describe_devices
from ...i18n import DEFAULT_LOCALE, available_locales, parity_report
from ...model.engine import FOCUS_POLICIES
from ...modules.registry import describe_all as describe_modules
from ...parameters import PARAMETER_COUNT, default_parameters
from ...pipelines.runner import describe_steps
from ...protocols import SCHEMA_VERSION, MessageType, new_envelope
from ..config import Settings, load_settings
from ..security import ApiKeyAuth, RateLimiter, assert_safe_bind, redact
from ..session import SessionLimitReached, SessionManager, SessionNotFound
from ..telemetry import StandardCounters, render_prometheus
from .schemas import CommandRequest, RunRequest, SimulationCreate, StepRequest

__all__ = ["create_app"]

_SAMPLE_LIMIT = 5000


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the application. Safe to call repeatedly in tests."""
    resolved = settings or load_settings()
    assert_safe_bind(host=resolved.host, api_key=resolved.api_key)

    app = FastAPI(
        title="conscious-subconscious API",
        version=__version__,
        description=(
            "Reproducible simulation sandbox for modelling subconscious repair and "
            "conscious attention acting on a scalar tissue model.\n\n"
            f"**{DISCLAIMER}**"
        ),
        openapi_tags=[
            {"name": "meta", "description": "Version, schema and provenance information."},
            {
                "name": "catalogue",
                "description": "Static catalogues: scenarios, parameters, modules, devices.",
            },
            {"name": "sessions", "description": "Create and drive simulation sessions."},
            {"name": "ops", "description": "Health, readiness and metrics."},
        ],
    )

    auth = ApiKeyAuth(key=resolved.api_key)
    limiter = RateLimiter(per_minute=resolved.rate_limit_per_minute)
    counters = StandardCounters()
    sessions = SessionManager(
        max_sessions=resolved.max_sessions, ttl_seconds=resolved.session_ttl_seconds
    )

    app.state.settings = resolved
    app.state.sessions = sessions
    app.state.counters = counters

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.allowed_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    # ------------------------------------------------------------------ deps
    async def guard(
        request: Request, x_api_key: str | None = Header(default=None, alias="X-API-Key")
    ) -> None:
        """Authentication + rate limiting + body-size limit, for every /v1 route."""
        client = request.client.host if request.client else "unknown"
        if not auth.check(x_api_key):
            counters.rejected_requests += 1
            counters.record_request("401")
            raise HTTPException(
                status_code=401,
                detail="a valid X-API-Key header is required",
                headers={"WWW-Authenticate": "X-API-Key"},
            )
        decision = limiter.check(client)
        if not decision.allowed:
            counters.rejected_requests += 1
            counters.record_request("429")
            raise HTTPException(
                status_code=429,
                detail="rate limit exceeded",
                headers={"Retry-After": str(int(decision.retry_after_seconds) + 1)},
            )
        declared = request.headers.get("content-length")
        if declared is not None:
            try:
                if int(declared) > resolved.max_body_bytes:
                    counters.record_request("413")
                    raise HTTPException(
                        status_code=413,
                        detail=f"request body exceeds {resolved.max_body_bytes} bytes",
                    )
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="invalid Content-Length header"
                ) from None

    @app.exception_handler(SessionNotFound)
    async def _session_not_found(request: Request, exc: SessionNotFound) -> JSONResponse:
        counters.record_request("404")
        return JSONResponse(
            status_code=404,
            content={"detail": "session not found or expired", "code": "session_not_found"},
        )

    @app.exception_handler(SessionLimitReached)
    async def _session_limit(request: Request, exc: SessionLimitReached) -> JSONResponse:
        counters.record_request("429")
        return JSONResponse(status_code=429, content={"detail": str(exc), "code": "session_limit"})

    @app.exception_handler(ConfigurationError)
    async def _config_error(request: Request, exc: ConfigurationError) -> JSONResponse:
        counters.record_request("400")
        return JSONResponse(
            status_code=400, content={"detail": redact(str(exc)), "code": "configuration_error"}
        )

    @app.exception_handler(ConsciousSubconsciousError)
    async def _domain_error(request: Request, exc: ConsciousSubconsciousError) -> JSONResponse:
        counters.record_request("400")
        return JSONResponse(
            status_code=400,
            content={"detail": redact(str(exc)), "code": type(exc).__name__},
        )

    # ------------------------------------------------------------------ ops
    @app.get("/healthz", tags=["ops"], summary="Liveness probe")
    async def healthz() -> dict[str, Any]:
        return {"status": "ok", "version": __version__}

    @app.get("/readyz", tags=["ops"], summary="Readiness probe")
    async def readyz() -> dict[str, Any]:
        return {
            "status": "ready",
            "sessions_open": len(sessions),
            "sessions_capacity": sessions.max_sessions,
            "auth_enabled": auth.enabled,
        }

    @app.get("/v1/metrics", tags=["ops"], summary="Prometheus metrics")
    async def metrics() -> PlainTextResponse:
        payload = counters.as_metrics(sessions_open=len(sessions))
        return PlainTextResponse(render_prometheus(payload), media_type="text/plain; version=0.0.4")

    # ------------------------------------------------------------ catalogue
    # Catalogue routes carry the guard too. Metadata is not secret, but a service
    # whose protection depends on which routes happen to be "interesting" is a
    # service whose protection is a judgement call made per route. tests
    # /integration/test_api.py asserts every /v1 route except /v1/metrics is
    # protected, so a new route cannot be added without the guard.
    @app.get("/v1/meta", tags=["meta"], dependencies=[Depends(guard)])
    async def meta() -> dict[str, Any]:
        return {
            "name": "conscious-subconscious",
            "version": __version__,
            "protocol_version": SCHEMA_VERSION,
            "parameter_count": PARAMETER_COUNT,
            "focus_policies": list(FOCUS_POLICIES),
            "modules": [entry["name"] for entry in describe_modules()],
            "device_kinds": [entry["kind"] for entry in describe_devices()],
            "pipeline_steps": [entry["uses"] for entry in describe_steps()],
            "locales": list(available_locales()),
            "default_locale": DEFAULT_LOCALE,
            "auth": auth.describe(),
            "disclaimer": DISCLAIMER,
            "provenance_policy": PROVENANCE_POLICY,
        }

    @app.get("/v1/parameters", tags=["catalogue"], dependencies=[Depends(guard)])
    async def parameters(unsupported_only: bool = False) -> dict[str, Any]:
        params = default_parameters()
        selected = params.unsupported() if unsupported_only else params.sorted()
        return {
            "summary": params.support_summary(),
            "parameters": [p.as_dict() for p in selected],
        }

    @app.get("/v1/scenarios", tags=["catalogue"], dependencies=[Depends(guard)])
    async def scenarios() -> dict[str, Any]:
        from ...sim.scenarios import builtin_scenarios  # noqa: PLC0415

        return {"scenarios": [s.as_dict() for s in builtin_scenarios()]}

    @app.get("/v1/modules", tags=["catalogue"], dependencies=[Depends(guard)])
    async def modules() -> dict[str, Any]:
        return {"modules": describe_modules()}

    @app.get("/v1/device-kinds", tags=["catalogue"], dependencies=[Depends(guard)])
    async def device_kinds() -> dict[str, Any]:
        return {"devices": describe_devices()}

    @app.get("/v1/pipeline-steps", tags=["catalogue"], dependencies=[Depends(guard)])
    async def pipeline_steps() -> dict[str, Any]:
        return {"steps": describe_steps()}

    @app.get("/v1/i18n/{locale}", tags=["catalogue"], dependencies=[Depends(guard)])
    async def catalogue(locale: str = DEFAULT_LOCALE) -> dict[str, Any]:
        from ...i18n import load_catalog  # noqa: PLC0415

        catalog = load_catalog(locale)
        if not catalog:
            raise HTTPException(
                status_code=404,
                detail=f"unknown locale {locale!r}; available: {', '.join(available_locales())}",
            )
        return {
            "locale": locale,
            "strings": catalog,
            "parity": parity_report()["locales"].get(locale),
        }

    # ------------------------------------------------------------- sessions
    @app.post("/v1/sessions", tags=["sessions"], status_code=201, dependencies=[Depends(guard)])
    async def create_session(body: SimulationCreate) -> dict[str, Any]:
        from ...sim.scenarios import get_scenario  # noqa: PLC0415

        scenario = get_scenario(body.scenario)
        overrides: dict[str, float] = dict(scenario.config.get("overrides", {}))
        overrides.update(body.overrides)
        config = scenario.build(
            seed=body.seed,
            dt_hours=body.dt_hours,
            horizon_hours=body.horizon_hours,
            tissue_name=body.tissue_name,
            focus_policy=body.focus_policy,
            modules=tuple(body.modules) if body.modules else scenario.config.get("modules", ()),
            overrides=overrides,
        )
        session = sessions.create(config)
        counters.sessions_created += 1
        counters.record_request("201")
        return {
            "id": session.id,
            "snapshot": session.as_dict(),
            "disclaimer": DISCLAIMER,
        }

    @app.get("/v1/sessions", tags=["sessions"], dependencies=[Depends(guard)])
    async def list_sessions() -> dict[str, Any]:
        counters.record_request("200")
        return {"sessions": list(sessions.list_ids()), "capacity": sessions.max_sessions}

    @app.get("/v1/sessions/{session_id}", tags=["sessions"], dependencies=[Depends(guard)])
    async def get_session(session_id: str) -> dict[str, Any]:
        counters.record_request("200")
        return sessions.snapshot(session_id)

    @app.delete(
        "/v1/sessions/{session_id}",
        tags=["sessions"],
        status_code=204,
        dependencies=[Depends(guard)],
    )
    async def delete_session(session_id: str) -> None:
        sessions.delete(session_id)
        counters.record_request("204")
        return

    @app.post("/v1/sessions/{session_id}/step", tags=["sessions"], dependencies=[Depends(guard)])
    async def step_session(session_id: str, body: StepRequest) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for _ in range(body.count):
            state = sessions.step(session_id)
            counters.steps_total += 1
        counters.record_request("200")
        return {"state": state, "snapshot": sessions.snapshot(session_id)}

    @app.post("/v1/sessions/{session_id}/run", tags=["sessions"], dependencies=[Depends(guard)])
    async def run_session(session_id: str, body: RunRequest) -> dict[str, Any]:
        result = (
            sessions.run(session_id)
            if body.hours is None
            else sessions.run_to(session_id, body.hours)
        )
        counters.record_request("200")
        return result.as_dict(include_samples=False)

    @app.post(
        "/v1/sessions/{session_id}/commands", tags=["sessions"], dependencies=[Depends(guard)]
    )
    async def command_session(session_id: str, body: CommandRequest) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if body.target:
            kwargs["target"] = body.target
        if body.policy:
            kwargs["policy"] = body.policy
        outcome = sessions.command(session_id, body.command, **kwargs)
        counters.record_request("200")
        return {"outcome": outcome, "snapshot": sessions.snapshot(session_id)}

    @app.get("/v1/sessions/{session_id}/metrics", tags=["sessions"], dependencies=[Depends(guard)])
    async def session_metrics(session_id: str) -> dict[str, Any]:
        snapshot = sessions.snapshot(session_id)
        counters.record_request("200")
        return {"id": session_id, "t_hours": snapshot["t_hours"], "tissue": snapshot["tissue"]}

    @app.get("/v1/sessions/{session_id}/result", tags=["sessions"], dependencies=[Depends(guard)])
    async def session_result(session_id: str, include_samples: bool = False) -> dict[str, Any]:
        result = sessions.result(session_id)
        if result is None:
            counters.record_request("409")
            raise HTTPException(
                status_code=409,
                detail="this session has not been run to completion yet; POST /run first",
            )
        counters.record_request("200")
        samples = result.samples[:_SAMPLE_LIMIT] if include_samples else ()
        payload = result.as_dict(include_samples=False)
        if include_samples:
            payload["samples"] = [s.as_dict() for s in samples]
            payload["samples_truncated"] = len(result.samples) > _SAMPLE_LIMIT
        return payload

    # -------------------------------------------------------------- streaming
    @app.websocket("/ws/v1/sessions/{session_id}")
    async def stream(websocket: WebSocket, session_id: str) -> None:
        """Stream ``sim.tick`` messages for a session.

        Authentication happens before ``accept`` so an unauthenticated peer
        never reaches a connected state. Query-parameter credentials are
        accepted for WebSockets only because browsers cannot set headers on a
        WebSocket handshake — a real limitation, not a preference.
        """
        provided = websocket.query_params.get("api_key")
        if not auth.check(provided):
            await websocket.close(code=4401, reason="api key required")
            return
        try:
            sessions.peek(session_id)
        except SessionNotFound:
            await websocket.close(code=4404, reason="session not found")
            return

        await websocket.accept()
        try:
            request = await websocket.receive_json()
        except WebSocketDisconnect:
            return
        except Exception:
            await websocket.send_json(
                new_envelope(
                    MessageType.ERROR, "api", {"detail": "expected a JSON control message"}
                ).as_dict()
            )
            await websocket.close(code=4400, reason="bad request")
            return

        command = str((request or {}).get("command", "step"))
        steps = int((request or {}).get("steps", 200))
        interval_ms = int((request or {}).get("interval_ms", 0))

        if command not in {"step", "snapshot"}:
            await websocket.send_json(
                new_envelope(
                    MessageType.ERROR,
                    "api",
                    {
                        "detail": f"unknown stream command {command!r}",
                        "allowed": ["step", "snapshot"],
                    },
                ).as_dict()
            )
            await websocket.close(code=4400, reason="unknown command")
            return

        if command == "snapshot":
            await websocket.send_json(
                new_envelope(
                    MessageType.SIM_TICK,
                    "engine",
                    sessions.snapshot(session_id),
                    session=session_id,
                ).as_dict()
            )
            await websocket.close()
            return

        for _ in _stream_steps(steps):
            try:
                state = sessions.step(session_id)
                counters.steps_total += 1
            except SessionNotFound:
                await websocket.send_json(
                    new_envelope(
                        MessageType.ERROR, "api", {"detail": "session expired"}, session=session_id
                    ).as_dict()
                )
                break
            except ConfigurationError as exc:
                await websocket.send_json(
                    new_envelope(
                        MessageType.ERROR, "api", {"detail": redact(str(exc))}, session=session_id
                    ).as_dict()
                )
                break
            await websocket.send_json(
                new_envelope(MessageType.SIM_TICK, "engine", state, session=session_id).as_dict()
            )
            if interval_ms > 0:
                import asyncio  # noqa: PLC0415

                await asyncio.sleep(interval_ms / 1000.0)
        try:
            await websocket.close()
        except RuntimeError:  # pragma: no cover - already closed by the peer
            pass

    return app


def _stream_steps(count: int) -> Iterator[int]:
    """Clamp a requested stream length. A client cannot ask for infinite work."""
    bounded = max(1, min(int(count), 20_000))
    return iter(range(bounded))
