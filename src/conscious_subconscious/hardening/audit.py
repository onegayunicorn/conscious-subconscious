"""A small, self-contained repository self-audit.

This is not a replacement for a real SAST tool. It is a short list of mistakes
that a project like this one is genuinely likely to make — a committed token, a
wildcard CORS origin, an ``eval`` that crept in during debugging — checked with
plain regexes so that the rules themselves are readable, reviewable and
testable.

Two design choices matter:

* **Rules are data, not code.** A rule is a name, a severity, a pattern and the
  remediation text. Nobody has to read an AST visitor to know what is checked.
* **Allow-listing is explicit and reasoned.** Patterns that detect secrets match
  their own definitions, so some files must be skipped. Each exemption names its
  reason. A blanket "skip anything that looks complicated" would make the audit
  decorative.
"""

from __future__ import annotations

import fnmatch
import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..core.errors import ConfigurationError

__all__ = ["Severity", "Rule", "Finding", "AuditReport", "RULES", "audit_paths", "audit_repository"]


class Severity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def rank(self) -> int:
        return {"high": 0, "medium": 1, "low": 2, "info": 3}[self.value]


@dataclass(frozen=True, slots=True)
class Rule:
    """One check, expressed as a set of regular expressions."""

    name: str
    severity: Severity
    description: str
    remediation: str
    patterns: tuple[tuple[str, str], ...]  # (code, regex)
    suffixes: tuple[str, ...] = (".py",)
    allowlist: tuple[str, ...] = ()
    ignore_case: bool = False

    def compiled(self) -> tuple[tuple[str, re.Pattern[str]], ...]:
        flags = re.IGNORECASE if self.ignore_case else 0
        return tuple((code, re.compile(pattern, flags)) for code, pattern in self.patterns)

    def is_allowed(self, relative_path: str) -> bool:
        return any(fnmatch.fnmatch(relative_path, pattern) for pattern in self.allowlist)


@dataclass(frozen=True, slots=True)
class Finding:
    """One rule violation."""

    rule: str
    severity: Severity
    path: str
    line: int
    code: str
    excerpt: str
    remediation: str

    def as_dict(self) -> dict[str, object]:
        return {
            "rule": self.rule,
            "severity": self.severity.value,
            "path": self.path,
            "line": self.line,
            "code": self.code,
            "excerpt": self.excerpt,
            "remediation": self.remediation,
        }

    def __str__(self) -> str:
        return f"[{self.severity.value:<6}] {self.path}:{self.line} {self.rule} ({self.code})"


@dataclass(slots=True)
class AuditReport:
    """Everything the audit found, plus what it skipped."""

    root: str
    files_scanned: int
    findings: list[Finding] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    def by_severity(self, severity: Severity) -> list[Finding]:
        return [f for f in self.findings if f.severity is severity]

    @property
    def blocking(self) -> list[Finding]:
        """High-severity findings: these fail the build."""
        return self.by_severity(Severity.HIGH)

    def counts(self) -> dict[str, int]:
        counts = {severity.value: 0 for severity in Severity}
        for finding in self.findings:
            counts[finding.severity.value] += 1
        return counts

    def as_dict(self) -> dict[str, object]:
        ordered = sorted(self.findings, key=lambda f: (f.severity.rank, f.path, f.line))
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "counts": self.counts(),
            "blocking": len(self.blocking),
            "findings": [f.as_dict() for f in ordered],
            "skipped": list(self.skipped),
        }


#: The file that defines the patterns necessarily contains them as strings, so it
#: trips every pattern-based rule. Exempting it is not a loophole: the rules
#: cannot be both defined and absent from their own source.
_RULE_DEFINITIONS = ("src/conscious_subconscious/hardening/audit.py",)

#: Rules that must never fire in a shipped tree.
RULES: tuple[Rule, ...] = (
    Rule(
        name="no-hardcoded-secrets",
        severity=Severity.HIGH,
        description="A credential-shaped string is present in a tracked file.",
        remediation=(
            "Remove the value, rotate it immediately (it is already in history), and "
            "load it from the environment instead."
        ),
        patterns=(
            ("github_pat", r"github_pat_[A-Za-z0-9_]{20,}"),
            ("github_classic", r"gh[pousr]_[A-Za-z0-9]{16,}"),
            ("anthropic", r"sk-ant-[A-Za-z0-9_\-]{16,}"),
            ("openai", r"sk-[A-Za-z0-9]{20,}"),
            ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
            ("slack", r"xox[abprs]-[A-Za-z0-9\-]{10,}"),
            ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
            # Requires a long token after the assignment, so that a type
            # annotation such as `api_key: str | None = None` does not trip it.
            (
                "assigned_secret",
                r"(?i)\b(api[_-]?key|client[_-]?secret|access[_-]?token|password)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{16,}",
            ),
        ),
        suffixes=(
            ".py",
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".md",
            ".env",
            ".example",
            ".sh",
            ".ini",
            ".cfg",
            ".ino",
        ),
        allowlist=(
            # The redaction patterns and the audit rules necessarily contain
            # credential-shaped regular expressions. They are not credentials.
            "src/conscious_subconscious/services/security.py",
            "src/conscious_subconscious/hardening/audit.py",
            "security/threat-model.md",
            "security/hardening-checklist.md",
            # Test fixtures deliberately include fake credentials to prove the
            # redactor works. They are not real, and they are not secrets.
            "tests/*",
        ),
    ),
    Rule(
        name="no-shell-injection",
        severity=Severity.HIGH,
        description="A subprocess is launched through a shell, which allows command injection.",
        remediation="Pass an argument list and leave shell=False (the default).",
        patterns=(("shell_true", r"shell\s*=\s*True"),),
        suffixes=(".py",),
        allowlist=_RULE_DEFINITIONS,
    ),
    Rule(
        name="no-dynamic-execution",
        severity=Severity.HIGH,
        description="eval/exec compiles arbitrary input at runtime.",
        remediation="Use a mapping of allowed callables, or an explicit parser.",
        patterns=(
            ("eval_call", r"(?<![\w.])eval\s*\("),
            ("exec_call", r"(?<![\w.])exec\s*\("),
        ),
        suffixes=(".py",),
        allowlist=_RULE_DEFINITIONS,
    ),
    Rule(
        name="no-disabled-tls-verification",
        severity=Severity.HIGH,
        description="TLS certificate verification is disabled.",
        remediation="Remove verify=False; fix the trust store instead.",
        patterns=(("verify_false", r"verify\s*=\s*False"),),
        suffixes=(".py",),
        allowlist=_RULE_DEFINITIONS,
    ),
    Rule(
        name="no-wildcard-cors",
        severity=Severity.HIGH,
        description="CORS is configured to accept any origin.",
        remediation="List the origins that are actually needed.",
        patterns=(
            ("wildcard_origin", r"allow_origins\s*=\s*\[\s*[\"']\*[\"']"),
            ("wildcard_origin_var", r"CS_ALLOWED_ORIGINS\s*=\s*\*"),
        ),
        suffixes=(".py", ".ts", ".tsx", ".js", ".yaml", ".yml", ".env", ".example"),
        allowlist=("src/conscious_subconscious/services/config.py", *_RULE_DEFINITIONS),
    ),
    Rule(
        name="no-unauthenticated-non-loopback-bind",
        severity=Severity.MEDIUM,
        description="A host binding is hard-coded to a wildcard address.",
        remediation="Default to 127.0.0.1 and require an API key before binding publicly.",
        patterns=(("bind_all", r"(host|HOST)\s*[:=]\s*[\"']0\.0\.0\.0[\"']"),),
        suffixes=(".py", ".ts", ".toml", ".yaml", ".yml"),
        allowlist=(
            # Inside a container the pod network is the boundary, and the manifest
            # that sets CS_HOST=0.0.0.0 ships alongside a secret holding CS_API_KEY.
            # Binding all interfaces there is correct; `assert_safe_bind` still
            # refuses that combination when no key is configured.
            "deploy/k8s/*",
            # Tests assert that the guard refuses a public bind without a key.
            "tests/*",
        ),
    ),
    Rule(
        name="no-debug-mode",
        severity=Severity.MEDIUM,
        description="A web framework is running in debug mode.",
        remediation="Drive debug mode from an environment variable that is off in production.",
        patterns=(
            ("debug_true", r"debug\s*=\s*True"),
            ("flask_debug", r"app\.run\([^)]*debug\s*=\s*True"),
        ),
        suffixes=(".py",),
        allowlist=_RULE_DEFINITIONS,
    ),
    Rule(
        name="no-silent-exception",
        severity=Severity.LOW,
        description="An exception is swallowed without a log or a comment.",
        remediation="Log it, or add a comment explaining why silence is correct here.",
        patterns=(("swallowed", r"except\s+Exception[^\n]*:\s*\n\s*pass\s*$"),),
        suffixes=(".py",),
        allowlist=_RULE_DEFINITIONS,
    ),
    Rule(
        name="no-print-in-library",
        severity=Severity.LOW,
        description="print() is used outside a CLI entry point.",
        remediation="Use the logging module, or write to an explicit stream.",
        patterns=(("print_call", r"^\s*print\("),),
        suffixes=(".py",),
        allowlist=(
            "src/conscious_subconscious/sim/cli.py",
            "src/conscious_subconscious/hardening/cli.py",
            "src/conscious_subconscious/services/api/__main__.py",
            "tools/*",
            "tests/*",
        ),
    ),
)

#: Extensions the scanner will open. Anything else is reported as skipped.
_SCANNABLE = (
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
    ".sh",
    ".cbuild",
    ".ini",
    ".cfg",
    ".ino",
    ".example",
)

_SKIP_DIRECTORIES = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "dist",
        "build",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        "site",
        "out",
        "runs",
        ".vite",
    }
)

#: Files larger than this are skipped: generated bundles produce noise, not signal.
_MAX_FILE_BYTES = 2_000_000


def audit_repository(root: str | Path, *, rules: Sequence[Rule] = RULES) -> AuditReport:
    """Scan a repository tree and return the findings."""
    location = Path(root)
    if not location.is_dir():
        raise ConfigurationError(f"not a directory: {location}")

    files: list[Path] = []
    skipped: list[str] = []
    for path in sorted(location.rglob("*")):
        if any(part in _SKIP_DIRECTORIES for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() not in _SCANNABLE and path.name not in ("Makefile", ".env.example"):
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                skipped.append(
                    f"{path.relative_to(location)} (larger than {_MAX_FILE_BYTES} bytes)"
                )
                continue
        except OSError:
            skipped.append(f"{path.relative_to(location)} (stat failed)")
            continue
        files.append(path)

    report = AuditReport(root=str(location), files_scanned=0, skipped=skipped)
    report.findings.extend(audit_paths(files, root=location, rules=rules))
    report.files_scanned = len(files)
    return report


def audit_paths(
    paths: Iterable[Path], *, root: Path, rules: Sequence[Rule] = RULES
) -> list[Finding]:
    """Run every rule over the given files."""
    findings: list[Finding] = []
    compiled = [(rule, rule.compiled()) for rule in rules]
    for path in paths:
        relative = _relative(path, root)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        for rule, patterns in compiled:
            if path.suffix.lower() not in rule.suffixes and path.name not in (
                "Makefile",
                ".env.example",
            ):
                continue
            if rule.is_allowed(relative):
                continue
            for code, pattern in patterns:
                for match in pattern.finditer(text):
                    line_number = text.count("\n", 0, match.start()) + 1
                    excerpt = lines[line_number - 1].strip() if line_number <= len(lines) else ""
                    findings.append(
                        Finding(
                            rule=rule.name,
                            severity=rule.severity,
                            path=relative,
                            line=line_number,
                            code=code,
                            excerpt=excerpt[:160],
                            remediation=rule.remediation,
                        )
                    )
    # De-duplicate: one line tripping two patterns of the same rule is one problem.
    seen: set[tuple[str, str, int]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.rule, finding.path, finding.line)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:  # pragma: no cover - only when root is not a parent
        return path.as_posix()


def iter_findings(report: AuditReport) -> Iterator[str]:
    """Render findings as stable, greppable lines."""
    for finding in sorted(report.findings, key=lambda f: (f.severity.rank, f.path, f.line)):
        yield str(finding)
