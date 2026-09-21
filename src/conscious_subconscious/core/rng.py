"""Deterministic random number generation.

A naive simulation shares one global ``random`` instance across every
subsystem. That makes results depend on the *order* in which unrelated code
happens to draw numbers: add a module, and every previously reproduced run
changes. This module avoids that by deriving an independent named substream
per consumer, from the root seed, with SHA-256.

Consequences worth knowing:

* Streams are stable across processes, platforms and Python versions
  (``hash()`` is deliberately not used — it is salted per process).
* Draws **within** a stream remain order-dependent. A stream is a sequence,
  not a bag.
"""

from __future__ import annotations

import hashlib
import random

__all__ = ["DeterministicRng"]

_MAX_SEED = 2**63 - 1


class DeterministicRng:
    """Root seed plus lazily created, independently seeded named substreams."""

    __slots__ = ("_seed", "_streams")

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError(f"seed must be an int, got {type(seed).__name__}")
        if seed < 0:
            raise ValueError("seed must be non-negative")
        self._seed = seed
        self._streams: dict[str, random.Random] = {}

    @property
    def seed(self) -> int:
        return self._seed

    def _derive(self, name: str) -> int:
        digest = hashlib.sha256(f"{self._seed}:{name}".encode()).digest()
        return int.from_bytes(digest[:8], "big") % _MAX_SEED

    def stream(self, name: str) -> random.Random:
        """Return the (sticky) substream called ``name``."""
        if not name:
            raise ValueError("stream name must be non-empty")
        existing = self._streams.get(name)
        if existing is not None:
            return existing
        created = random.Random(self._derive(name))
        self._streams[name] = created
        return created

    def stream_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._streams))

    def uniform(self, name: str, low: float, high: float) -> float:
        """Draw a uniform sample from substream ``name``."""
        if low > high:
            raise ValueError(f"low ({low}) must not exceed high ({high})")
        return self.stream(name).uniform(low, high)

    def normal(self, name: str, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Draw a normal sample from substream ``name``."""
        if sigma < 0:
            raise ValueError("sigma must be non-negative")
        return self.stream(name).gauss(mu, sigma)

    def choice(self, name: str, population: tuple[str, ...]) -> str:
        """Pick one item from ``population`` using substream ``name``."""
        if not population:
            raise ValueError("population must be non-empty")
        return self.stream(name).choice(population)

    def fork(self, name: str) -> DeterministicRng:
        """Create a child generator whose seed is derived from ``name``.

        Useful when handing a generator to a subsystem that must not be able
        to perturb the parent's streams.
        """
        return DeterministicRng(self._derive(name))

    def digest(self) -> str:
        """Hash of the root seed and the set of streams opened so far.

        The digest changes if a run draws from a different set of streams,
        which makes an accidental dependency between modules visible.
        """
        payload = f"{self._seed}|{'|'.join(self.stream_names())}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"DeterministicRng(seed={self._seed}, streams={list(self.stream_names())!r})"
