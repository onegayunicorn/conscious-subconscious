"""JSON-RPC 2.0 control messages.

Control is separated from streaming on purpose: commands are request/response
and must be answerable ("did the focus command apply?"), while samples are
fire-and-forget. Mixing them makes both harder to reason about.

This module only builds and validates dictionaries. It never opens a socket, so
it is testable without any network or event loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..core.errors import ProtocolError

__all__ = [
    "JSONRPC_VERSION",
    "ErrorCode",
    "request",
    "response",
    "error",
    "notification",
    "validate_jsonrpc",
    "is_request",
    "is_response",
    "is_error",
]

JSONRPC_VERSION = "2.0"


class ErrorCode:
    """Standard JSON-RPC codes plus the application range."""

    # Standard
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    # Application-defined (-32000..-32099 is reserved for implementations)
    SESSION_NOT_FOUND = -32001
    SIMULATION_FINISHED = -32002
    DEVICE_UNAVAILABLE = -32003
    RATE_LIMITED = -32004
    UNAUTHORISED = -32005


def request(
    method: str, params: Mapping[str, Any] | None = None, request_id: Any = None
) -> dict[str, Any]:
    """Build a request object."""
    if not method:
        raise ProtocolError("method must be non-empty")
    message: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "method": method}
    if params is not None:
        message["params"] = dict(params)
    message["id"] = request_id
    return message


def notification(method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a notification (a request with no id, so no reply is expected)."""
    message: dict[str, Any] = {"jsonrpc": JSONRPC_VERSION, "method": method}
    if params is not None:
        message["params"] = dict(params)
    return message


def response(result: Any, request_id: Any) -> dict[str, Any]:
    """Build a success response."""
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}


def error(
    code: int,
    message: str,
    request_id: Any = None,
    data: Any = None,
) -> dict[str, Any]:
    """Build an error response."""
    body: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        body["data"] = data
    return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "error": body}


def validate_jsonrpc(message: Mapping[str, Any]) -> tuple[str, ...]:
    """Return every structural problem with a JSON-RPC message."""
    problems: list[str] = []
    if not isinstance(message, Mapping):
        return ("jsonrpc message must be a mapping",)

    if message.get("jsonrpc") != JSONRPC_VERSION:
        problems.append(f"jsonrpc must be {JSONRPC_VERSION!r}")

    has_id = "id" in message
    has_result = "result" in message
    has_error = "error" in message

    if has_result and has_error:
        problems.append("a response cannot carry both result and error")

    if (has_result or has_error) and not has_id:
        problems.append("a response must carry an id (use null for 'unknown request')")

    if "method" in message:
        method = message["method"]
        if not isinstance(method, str) or not method:
            problems.append("method must be a non-empty string")
        if has_result or has_error:
            problems.append("a request cannot also be a response")
        params = message.get("params")
        if params is not None and not isinstance(params, (Mapping, list)):
            problems.append("params must be an object or an array when present")
    elif not (has_result or has_error):
        problems.append("message must be a request (has method) or a response (has result/error)")

    if has_id:
        identifier = message["id"]
        if identifier is not None and not isinstance(identifier, (str, int)):
            problems.append("id must be a string, an integer or null")
        if isinstance(identifier, bool):
            problems.append("id must not be a boolean")

    if has_error:
        body = message["error"]
        if not isinstance(body, Mapping):
            problems.append("error must be an object")
        else:
            code = body.get("code")
            if not isinstance(code, int) or isinstance(code, bool):
                problems.append("error.code must be an integer")
            text = body.get("message")
            if not isinstance(text, str) or not text:
                problems.append("error.message must be a non-empty string")

    return tuple(problems)


def is_request(message: Mapping[str, Any]) -> bool:
    """True for a request or notification (has ``method``)."""
    return "method" in message


def is_response(message: Mapping[str, Any]) -> bool:
    """True for any response, success or error."""
    return "result" in message or "error" in message


def is_error(message: Mapping[str, Any]) -> bool:
    """True for an error response."""
    return "error" in message
