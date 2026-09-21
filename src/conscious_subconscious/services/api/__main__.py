"""``python -m conscious_subconscious.services.api`` — run the service.

Startup validates the bind configuration *before* the socket is opened, so a
misconfigured deployment fails immediately and visibly rather than serving
anonymous requests to whatever can reach the port.
"""

from __future__ import annotations

import logging
import sys

from ..config import load_settings
from ..security import redact
from .app import create_app

__all__ = ["main"]


def main(argv: list[str] | None = None) -> int:
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("conscious_subconscious.api")

    try:
        app = create_app(settings)
    except Exception as exc:
        print(f"refusing to start: {redact(str(exc))}", file=sys.stderr)
        return 2

    for key, value in settings.describe().items():
        logger.info("config %s=%s", key, value)
    if not settings.auth_enabled:
        logger.warning(
            "CS_API_KEY is not set: authentication is DISABLED. This is only "
            "acceptable on a loopback interface."
        )

    try:
        import uvicorn  # noqa: PLC0415
    except ImportError:
        print(
            "uvicorn is not installed: pip install 'conscious-subconscious[api]'",
            file=sys.stderr,
        )
        return 2

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
