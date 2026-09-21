"""Hardening: a short, honest, self-applied rule set.

The audit exists because this repository is published and contains a token-fed
pipeline and a service that accepts commands. It is deliberately small enough
that a reader can check the rules against the code in a few minutes — a large
scanner that nobody reads is worse than a small one that everybody does.

It is not a security guarantee, and ``security/threat-model.md`` says so.
"""

from __future__ import annotations

from .audit import (
    RULES,
    AuditReport,
    Finding,
    Rule,
    Severity,
    audit_paths,
    audit_repository,
    iter_findings,
)

__all__ = [
    "RULES",
    "AuditReport",
    "Finding",
    "Rule",
    "Severity",
    "audit_paths",
    "audit_repository",
    "iter_findings",
]
