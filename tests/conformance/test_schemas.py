"""Conformance between the implementation and the published JSON Schemas.

``protocols/schemas/`` is the contract the TypeScript console also implements.
When the two disagree, the schema wins, so the Python side is checked against it
here rather than the other way round.

These tests are skipped when ``jsonschema`` is absent, and the skip is explicit
rather than silent: a conformance suite that quietly does nothing is worse than
no suite, because it looks like coverage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conscious_subconscious.devices import (
    BleHeartRateDevice,
    ReplayDevice,
    SerialBridgeDevice,
    SimulatedCardioDevice,
)
from conscious_subconscious.model.engine import RunConfig, SimulationEngine
from conscious_subconscious.protocols import MessageType, new_envelope, request

jsonschema = pytest.importorskip(
    "jsonschema", reason="install the 'dev' extra for schema conformance"
)

SCHEMA_FILES = (
    "envelope.schema.json",
    "stream-sample.schema.json",
    "sim-tick.schema.json",
    "sim-command.schema.json",
    "device-hello.schema.json",
)


@pytest.fixture(scope="module")
def schemas(repo_root: Path) -> dict[str, dict]:
    directory = repo_root / "protocols" / "schemas"
    loaded: dict[str, dict] = {}
    for name in SCHEMA_FILES:
        path = directory / name
        assert path.is_file(), f"missing schema {name}"
        loaded[name] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


@pytest.fixture(scope="module")
def validator(schemas: dict[str, dict]):
    from jsonschema import Draft202012Validator, FormatChecker

    def build(name: str) -> Draft202012Validator:
        return Draft202012Validator(schemas[name], format_checker=FormatChecker())

    return build


def test_every_schema_is_a_valid_json_schema(schemas: dict[str, dict], validator) -> None:
    for name in SCHEMA_FILES:
        validator(name).check_schema(schemas[name])


def test_envelope_from_the_engine_conforms(validator) -> None:
    envelope = new_envelope(
        MessageType.SIM_TICK, "engine", {"t_hours": 1.0, "integrity": 0.5, "damage": 0.5}
    )
    validator("envelope.schema.json").validate(envelope.as_dict())


def test_every_message_type_produces_a_conforming_envelope(validator) -> None:
    for message_type in MessageType:
        payload: dict[str, object] = {}
        if message_type is MessageType.JSONRPC:
            payload = request("noop", request_id=1)
        envelope = new_envelope(message_type, "conformance", payload)
        validator("envelope.schema.json").validate(envelope.as_dict())


def test_envelope_rejects_a_wrong_version(validator) -> None:
    payload = new_envelope(MessageType.HEARTBEAT, "x").as_dict()
    payload["v"] = "9.9.9"
    with pytest.raises(jsonschema.ValidationError):
        validator("envelope.schema.json").validate(payload)


def test_envelope_rejects_an_unknown_key(validator) -> None:
    payload = new_envelope(MessageType.HEARTBEAT, "x").as_dict()
    payload["extra"] = 1
    with pytest.raises(jsonschema.ValidationError):
        validator("envelope.schema.json").validate(payload)


def test_engine_tick_states_conform(validator) -> None:
    """The typed message the console renders must match sim-tick.schema.json."""
    engine = SimulationEngine(RunConfig(horizon_hours=5.0, dt_hours=0.5, focus_policy="always"))
    tick_validator = validator("sim-tick.schema.json")
    for _ in range(10):
        tick_validator.validate(engine.step())


def test_a_tick_with_mediators_and_rates_conforms(validator) -> None:
    engine = SimulationEngine(RunConfig(horizon_hours=5.0, dt_hours=0.5))
    result = engine.run()
    sample = result.samples[-1].as_dict()
    validator("sim-tick.schema.json").validate(
        {
            "t_hours": sample["t_hours"],
            "integrity": sample["integrity"],
            "damage": sample["damage"],
            "attention": sample["attention"],
            "focused": sample["focused"],
            "fatigued": sample["fatigued"],
            "perceived_progress": sample["perceived_progress"],
            "mediators": sample["mediators"],
            "rates": sample["rates"],
        }
    )


def test_stream_sample_payloads_conform(validator) -> None:
    device = SimulatedCardioDevice(config={"seed": 1})
    device.open()
    sample_validator = validator("stream-sample.schema.json")
    for _ in range(5):
        for sample in device.read():
            sample_validator.validate(sample.as_dict())


def test_device_hello_payloads_conform(validator) -> None:
    hello_validator = validator("device-hello.schema.json")
    devices = [
        SimulatedCardioDevice(),
        SerialBridgeDevice(),
        BleHeartRateDevice(),
        ReplayDevice(config={"path": __file__}),
    ]
    for device in devices:
        hello_validator.validate(device.hello_payload())


def test_sim_command_payloads_conform(validator) -> None:
    command_validator = validator("sim-command.schema.json")
    for payload in (
        {"command": "focus", "target": "muscle tissue"},
        {"command": "release"},
        {"command": "set_policy", "policy": "intermittent"},
        {"command": "step"},
        {"command": "snapshot"},
    ):
        command_validator.validate(payload)


def test_sim_command_rejects_a_write_to_integrity(validator) -> None:
    """The schema is a boundary: there is no command that sets tissue state."""
    with pytest.raises(jsonschema.ValidationError):
        validator("sim-command.schema.json").validate({"command": "set_integrity", "value": 1.0})
