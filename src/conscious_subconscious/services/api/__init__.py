"""The HTTP application (needs the ``api`` extra).

Imported lazily via :func:`~conscious_subconscious.services.api.create_app` so
that importing this package does not require FastAPI to be installed.
"""

from __future__ import annotations

from typing import Any

__all__ = ["create_app"]


def create_app(*args: Any, **kwargs: Any) -> Any:
    """Build the FastAPI app. See :mod:`conscious_subconscious.services.api.app`."""
    from .app import create_app as _create_app  # noqa: PLC0415

    return _create_app(*args, **kwargs)
