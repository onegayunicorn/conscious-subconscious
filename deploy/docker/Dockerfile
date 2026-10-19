# syntax=docker/dockerfile:1
#
# conscious-subconscious service image.
#
# Build context is the REPOSITORY ROOT, not this directory, because the image
# needs pyproject.toml, src/ and i18n/ from the root:
#
#   docker build -f deploy/docker/Dockerfile -t conscious-subconscious:0.1.0 .
#
# (That is what `make docker` does. The same pairing is used by
# .github/workflows/docker.yml and by deploy/docker/docker-compose.yml.)
#
# What this image is NOT: a medical device or any part of one. The service it
# runs manipulates a deterministic simulation of a scalar tissue variable.
# See DISCLAIMER.md at the repository root.

# ---------------------------------------------------------------------------
# Stage 1 — builder. Compilers and build tooling live here and nowhere else.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Only wheels get built (no source distributions), so no compiler is needed
# beyond what a wheel-less dependency would require. build-essential is
# installed anyway because `cryptography`-class transitives can arrive through
# the `api` extra; it is removed with the stage.
RUN apt-get update \
 && apt-get install --no-install-recommends -y build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

# A dedicated virtualenv keeps site-packages separable from the interpreter, so
# the runtime stage can copy one directory and leave the toolchain behind.
RUN python -m venv /opt/venv \
 && /opt/venv/bin/python -m pip install --upgrade pip \
 && /opt/venv/bin/python -m pip install ".[api]"

# ---------------------------------------------------------------------------
# Stage 2 — runtime. No compilers, no build tooling, no shell scripts to audit.
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS runtime

# Python 3.12 is pinned deliberately: the CI matrix covers 3.10-3.13, but the
# image ships one interpreter so that behaviour is not platform-dependent.
# Pin the minor version rather than the patch so security patches can be picked
# up without an image rebuild decision.

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    # The container does not carry the repository layout, so the locale
    # catalogs are located explicitly. i18n.py checks CS_LOCALES_DIR first.
    CS_LOCALES_DIR=/app/i18n/locales \
    # Writable location for the SQLite data directory. Paired with a volume.
    CS_DATA_DIR=/data \
    CS_HOST=0.0.0.0 \
    CS_PORT=8080 \
    CS_LOG_LEVEL=INFO

# Fixed numeric UID/GID so that Kubernetes `runAsUser`/`runAsNonRoot` and
# `securityContext.fsGroup` can reference it without guessing.
RUN groupadd --system --gid 10001 cs \
 && useradd --system --uid 10001 --gid cs --home-dir /app --shell /usr/sbin/nologin cs \
 && mkdir -p /app /data \
 && chown -R cs:cs /app /data

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Locale catalogs are data, not code, and are mounted/copied separately so a
# translation can be updated without rebuilding the Python layer.
#
# NOTE FOR OPERATORS: `i18n/locales/` does not exist in the repository yet
# (tools/check_locales.py and the `locale-parity` pre-commit hook reference it).
# Until that directory exists, this COPY fails and the image cannot be built.
# See deploy/README.md.
COPY --chown=cs:cs i18n ./i18n

USER 10001:10001

EXPOSE 8080

# Uses the stdlib rather than curl or wget so the final image needs no extra
# packages. /healthz is liveness only and must not depend on the data volume;
# readiness is a separate endpoint (/readyz) used by the Kubernetes probes.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import sys, urllib.request;\
sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).status == 200 else 1)"]

# The API service does not exist in this repository yet; this entry point is the
# one pyproject.toml documents for it. Until it lands, the image starts and the
# container exits immediately with a module-not-found error — which is the
# correct, non-silent failure. `cs-sim` is installed and usable in the meantime:
#
#   docker run --rm conscious-subconscious:0.1.0 cs-sim version
CMD ["python", "-m", "conscious_subconscious.services.api"]
