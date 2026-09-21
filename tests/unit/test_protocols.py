"""The wire protocol: envelope, JSON-RPC, topics, framing, transports."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from conscious_subconscious.core.errors import ProtocolError
from conscious_subconscious.protocols import (
    SCHEMA_VERSION,
    Envelope,
    ErrorCode,
    InProcessTransport,
    MessageType,
    NdjsonDecoder,
    decode,
    device_topic,
    device_wildcard,
    encode,
    error,
    make_pair,
    new_envelope,
    notification,
    parse_topic,
    request,
    response,
    session_topic,
    session_wildcard,
    validate_envelope,
    validate_identifier,
    validate_jsonrpc,
)

FIXED_TIME = datetime(2026, 9, 21, 12, 0, 0, tzinfo=timezone.utc)


def sample_envelope(**kwargs: object) -> Envelope:
    defaults: dict[str, object] = {
        "message_id": "abc123",
        "timestamp": FIXED_TIME,
    }
    defaults.update(kwargs)
    return new_envelope(MessageType.SIM_TICK, "engine", {"t_hours": 1.0}, **defaults)  # type: ignore[arg-type]


class TestEnvelope:
    def test_new_envelope_is_valid(self) -> None:
        assert validate_envelope(sample_envelope().as_dict()) == ()

    def test_round_trip_through_dict(self) -> None:
        original = sample_envelope(session="sess-1")
        assert Envelope.from_dict(original.as_dict()) == original

    def test_round_trip_through_json(self) -> None:
        original = sample_envelope()
        assert Envelope.from_json(original.to_json()) == original

    def test_timestamp_is_normalised_to_utc_z(self) -> None:
        envelope = new_envelope(
            MessageType.HEARTBEAT,
            "engine",
            timestamp=datetime(2026, 9, 21, 14, 0, 0, tzinfo=timezone.utc),
        )
        assert envelope.ts.endswith("Z")

    def test_naive_timestamp_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            new_envelope(MessageType.HEARTBEAT, "engine", timestamp=datetime(2026, 9, 21))

    def test_ids_are_unique_by_default(self) -> None:
        assert sample_envelope(message_id=None).id != sample_envelope(message_id=None).id

    def test_rejects_a_missing_key(self) -> None:
        payload = sample_envelope().as_dict()
        del payload["source"]
        assert any("missing required key" in p for p in validate_envelope(payload))

    def test_rejects_an_unknown_key(self) -> None:
        payload = sample_envelope().as_dict()
        payload["surprise"] = True
        assert any("unknown key" in p for p in validate_envelope(payload))

    def test_rejects_an_unknown_version(self) -> None:
        payload = sample_envelope().as_dict()
        payload["v"] = "2.0.0"
        assert any("unsupported protocol version" in p for p in validate_envelope(payload))

    def test_rejects_an_unknown_message_type(self) -> None:
        payload = sample_envelope().as_dict()
        payload["type"] = "mind.meld"
        assert any("unknown message type" in p for p in validate_envelope(payload))

    def test_rejects_a_timestamp_without_a_timezone(self) -> None:
        payload = sample_envelope().as_dict()
        payload["ts"] = "2026-09-21T12:00:00"
        assert any("timezone" in p for p in validate_envelope(payload))

    def test_rejects_a_non_mapping_payload(self) -> None:
        payload = sample_envelope().as_dict()
        payload["payload"] = [1, 2, 3]
        assert any("payload must be a mapping" in p for p in validate_envelope(payload))

    def test_rejects_an_oversized_payload(self) -> None:
        payload = sample_envelope().as_dict()
        payload["payload"] = {"blob": "x" * 300_000}
        assert any("exceeds" in p for p in validate_envelope(payload))

    def test_rejects_an_empty_id(self) -> None:
        payload = sample_envelope().as_dict()
        payload["id"] = ""
        assert any("id must be" in p for p in validate_envelope(payload))

    def test_reports_every_problem_not_just_the_first(self) -> None:
        payload = sample_envelope().as_dict()
        payload["v"] = "9.9.9"
        payload["type"] = "nope"
        problems = validate_envelope(payload)
        assert len(problems) >= 2

    def test_rejects_a_bad_session_identifier(self) -> None:
        payload = sample_envelope().as_dict()
        payload["session"] = "has a space"
        assert validate_envelope(payload) != ()
        # Note: session shape is checked by the topic layer too; the envelope only
        # requires it to be a non-empty string when present.

    def test_jsonrpc_payloads_are_validated(self) -> None:
        """A jsonrpc-typed envelope must actually carry a JSON-RPC message."""
        payload = sample_envelope().as_dict()
        payload["type"] = MessageType.JSONRPC.value
        payload["payload"] = {"not": "jsonrpc"}
        problems = validate_envelope(payload)
        assert any("jsonrpc" in p for p in problems)

    def test_building_a_jsonrpc_envelope_with_a_bad_payload_raises(self) -> None:
        with pytest.raises(ProtocolError):
            new_envelope(MessageType.JSONRPC, "client", {"not": "jsonrpc"})

    def test_a_valid_jsonrpc_envelope_is_accepted(self) -> None:
        envelope = new_envelope(MessageType.JSONRPC, "client", request("noop", request_id=1))
        assert validate_envelope(envelope.as_dict()) == ()

    def test_constructing_an_invalid_envelope_raises(self) -> None:
        with pytest.raises(ProtocolError):
            Envelope(v="0.0.1", id="a", ts="2026-09-21T00:00:00Z", type="sim.tick", source="x")

    def test_every_message_type_is_accepted(self) -> None:
        for message_type in MessageType:
            payload: dict[str, object] = {}
            if message_type is MessageType.JSONRPC:
                payload = request("noop", request_id=1)
            envelope = new_envelope(message_type, "test", payload)
            assert validate_envelope(envelope.as_dict()) == ()


class TestJsonRpc:
    def test_request_shape(self) -> None:
        message = request("sim.step", {"count": 1}, request_id=7)
        assert message == {"jsonrpc": "2.0", "method": "sim.step", "params": {"count": 1}, "id": 7}
        assert validate_jsonrpc(message) == ()

    def test_notification_has_no_id(self) -> None:
        message = notification("sim.tick")
        assert "id" not in message
        assert validate_jsonrpc(message) == ()

    def test_response_shape(self) -> None:
        assert validate_jsonrpc(response({"ok": True}, 1)) == ()

    def test_error_shape(self) -> None:
        message = error(ErrorCode.SESSION_NOT_FOUND, "no such session", 1)
        assert message["error"]["code"] == -32001
        assert validate_jsonrpc(message) == ()

    def test_response_may_not_carry_both_result_and_error(self) -> None:
        bad = {"jsonrpc": "2.0", "id": 1, "result": {}, "error": {"code": 1, "message": "x"}}
        assert any("both result and error" in p for p in validate_jsonrpc(bad))

    def test_response_requires_an_id(self) -> None:
        assert any(
            "must carry an id" in p for p in validate_jsonrpc({"jsonrpc": "2.0", "result": 1})
        )

    def test_boolean_id_is_rejected(self) -> None:
        bad = {"jsonrpc": "2.0", "method": "x", "id": True}
        assert any("boolean" in p for p in validate_jsonrpc(bad))

    def test_error_requires_an_integer_code(self) -> None:
        bad = {"jsonrpc": "2.0", "id": 1, "error": {"code": "nope", "message": "x"}}
        assert any("error.code" in p for p in validate_jsonrpc(bad))

    def test_request_rejects_empty_method(self) -> None:
        with pytest.raises(ProtocolError):
            request("")


class TestTopics:
    def test_session_topic_round_trip(self) -> None:
        topic = session_topic("sess-1", "events")
        assert topic == "cs/v1/sessions/sess-1/events"
        assert parse_topic(topic) == {"session": "sess-1", "kind": "events"}

    def test_device_topic_round_trip(self) -> None:
        topic = device_topic("sess-1", "hr-01", "stream")
        assert topic == "cs/v1/sessions/sess-1/devices/hr-01/stream"
        assert parse_topic(topic) == {
            "session": "sess-1",
            "kind": "devices",
            "device": "hr-01",
            "leaf": "stream",
        }

    def test_wildcards(self) -> None:
        assert device_wildcard("s", "stream").endswith("/devices/+/stream")
        assert session_wildcard().endswith("/sessions/+/events")

    def test_session_id_cannot_contain_a_topic_separator(self) -> None:
        """Otherwise a peer could publish into another session's namespace."""
        with pytest.raises(ProtocolError):
            session_topic("../../other", "events")

    def test_session_id_cannot_contain_a_wildcard(self) -> None:
        with pytest.raises(ProtocolError):
            validate_identifier("sess+1", what="session")

    def test_device_id_cannot_contain_a_wildcard(self) -> None:
        with pytest.raises(ProtocolError):
            device_topic("s", "dev#", "stream")

    def test_rejects_an_unknown_leaf(self) -> None:
        with pytest.raises(ProtocolError):
            device_topic("s", "d", "secret")

    def test_rejects_an_unknown_session_kind(self) -> None:
        with pytest.raises(ProtocolError):
            session_topic("s", "everything")

    def test_parse_rejects_a_wrong_root(self) -> None:
        with pytest.raises(ProtocolError):
            parse_topic("other/v1/sessions/s/events")

    def test_parse_rejects_a_wrong_version(self) -> None:
        with pytest.raises(ProtocolError):
            parse_topic("cs/v2/sessions/s/events")

    def test_parse_rejects_trailing_levels(self) -> None:
        with pytest.raises(ProtocolError):
            parse_topic("cs/v1/sessions/s/events/extra")

    def test_parse_rejects_a_wildcard_topic(self) -> None:
        with pytest.raises(ProtocolError):
            parse_topic("cs/v1/sessions/+/events")

    def test_parse_rejects_a_short_device_topic(self) -> None:
        with pytest.raises(ProtocolError):
            parse_topic("cs/v1/sessions/s/devices/d")


class TestCodec:
    def test_encode_is_one_line(self) -> None:
        assert encode({"a": 1}).count(b"\n") == 1

    def test_encode_is_key_sorted(self) -> None:
        assert encode({"b": 1, "a": 2}) == b'{"a":2,"b":1}\n'

    def test_decode_rejects_an_array(self) -> None:
        with pytest.raises(ProtocolError):
            decode("[1,2,3]")

    def test_decode_rejects_empty_input(self) -> None:
        with pytest.raises(ProtocolError):
            decode("")

    def test_decode_tolerates_a_trailing_newline(self) -> None:
        assert decode(b'{"a":1}\n') == {"a": 1}

    def test_decoder_handles_split_chunks(self) -> None:
        decoder = NdjsonDecoder()
        payload = encode({"message": "hello"}) + encode({"message": "world"})
        first_half, second_half = payload[:10], payload[10:]
        assert decoder.feed(first_half) == []
        assert decoder.feed(second_half) == [{"message": "hello"}, {"message": "world"}]

    def test_decoder_skips_blank_lines(self) -> None:
        decoder = NdjsonDecoder()
        assert decoder.feed(b'\n\n{"a":1}\n\n') == [{"a": 1}]

    def test_decoder_refuses_to_truncate_an_oversized_partial_message(self) -> None:
        """A truncated message that still parses is worse than a rejected one."""
        decoder = NdjsonDecoder(max_line_bytes=64)
        with pytest.raises(ProtocolError):
            decoder.feed(b"x" * 200)
        assert decoder.buffered_bytes == 0

    def test_decoder_counts_lines(self) -> None:
        decoder = NdjsonDecoder()
        decoder.feed(encode({"a": 1}) + encode({"a": 2}))
        assert decoder.lines_decoded == 2

    def test_decoder_rejects_non_bytes(self) -> None:
        with pytest.raises(ProtocolError):
            NdjsonDecoder().feed("a string")  # type: ignore[arg-type]


class TestTransport:
    def test_pair_delivers_in_both_directions(self) -> None:
        client, server = make_pair()
        client.send(sample_envelope())
        server.send(sample_envelope(message_id="reply"))
        assert server.receive() is not None
        assert client.receive() is not None

    def test_receive_returns_none_when_empty(self) -> None:
        client, _ = make_pair()
        assert client.receive() is None

    def test_accepts_a_raw_mapping(self) -> None:
        client, server = make_pair()
        client.send(sample_envelope().as_dict())
        assert isinstance(server.receive(), Envelope)

    def test_invalid_mapping_is_rejected_on_send(self) -> None:
        client, _ = make_pair()
        with pytest.raises(ProtocolError):
            client.send({"nope": True})

    def test_bounded_queue_refuses_rather_than_dropping(self) -> None:
        client, _ = make_pair(max_queue=2)
        client.send(sample_envelope())
        client.send(sample_envelope())
        with pytest.raises(ProtocolError, match="queue is full"):
            client.send(sample_envelope())

    def test_send_after_close_is_rejected(self) -> None:
        client, _ = make_pair()
        client.close()
        with pytest.raises(ProtocolError):
            client.send(sample_envelope())

    def test_receive_after_close_returns_none(self) -> None:
        client, _ = make_pair()
        client.close()
        assert client.receive() is None

    def test_close_is_idempotent_and_context_manager_works(self) -> None:
        client, _ = make_pair()
        with client as transport:
            assert isinstance(transport, InProcessTransport)
        client.close()
        assert client.closed

    def test_unconnected_transport_refuses_to_send(self) -> None:
        lonely = InProcessTransport()
        with pytest.raises(ProtocolError, match="not connected"):
            lonely.send(sample_envelope())


def test_protocol_version_is_pinned() -> None:
    """Bumping this is a breaking change and must be deliberate."""
    assert SCHEMA_VERSION == "1.0.0"
    assert json.loads(sample_envelope().to_json())["v"] == SCHEMA_VERSION
