"""``cs-hardening`` — run the repository self-audit.

Exit codes
----------
0
    No high-severity findings (medium and below are reported, not fatal).
1
    At least one high-severity finding.
2
    The audit could not run.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ..core.errors import ConfigurationError, ConsciousSubconsciousError
from .audit import RULES, AuditReport, Severity, audit_repository

__all__ = ["main", "build_parser", "render_report"]


def render_report(report: AuditReport, *, verbose: bool = True) -> str:
    """Render an :class:`~conscious_subconscious.hardening.audit.AuditReport`."""
    counts = report.counts()
    lines = [
        "conscious-subconscious hardening self-audit",
        "===========================================",
        f"root:          {report.root}",
        f"files scanned: {report.files_scanned}",
        (
            "findings:      "
            + ", ".join(f"{severity.value}={counts[severity.value]}" for severity in Severity)
        ),
        "",
    ]
    blocking = report.blocking
    if blocking:
        lines.append(f"{len(blocking)} high-severity finding(s) — these fail the audit:")
        lines.append("")
        for finding in blocking:
            lines.append(f"  {finding}")
            lines.append(f"      {finding.excerpt}")
            lines.append(f"      fix: {finding.remediation}")
        lines.append("")

    lower = [f for f in report.findings if f.severity is not Severity.HIGH]
    if lower and verbose:
        lines.append(f"{len(lower)} lower-severity finding(s):")
        lines.append("")
        for finding in sorted(lower, key=lambda f: (f.severity.rank, f.path, f.line)):
            lines.append(f"  {finding}")
            if finding.severity is Severity.INFO:
                continue
            lines.append(f"      {finding.excerpt}")
        lines.append("")

    if not report.findings:
        lines.append("No findings. This is a short rule list, not a security guarantee.")
        lines.append("")

    if report.skipped:
        lines.append(f"{len(report.skipped)} path(s) skipped:")
        for entry in report.skipped:
            lines.append(f"  {entry}")
        lines.append("")

    lines.append(
        "Scope: this audit checks a fixed list of common mistakes in this "
        "repository's own source. It is not a SAST tool and it cannot show that "
        "the project is secure."
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cs-hardening",
        description="Run the conscious-subconscious self-audit over a repository tree.",
    )
    parser.add_argument("--root", default=".", help="repository root to scan")
    parser.add_argument("--json", action="store_true", help="emit machine-readable findings")
    parser.add_argument("--out", default=None, help="write output to a file")
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="only print high-severity findings",
    )
    parser.add_argument("--rules", action="store_true", help="list the rules and exit")
    parser.add_argument(
        "--severity",
        choices=[s.value for s in Severity],
        default=None,
        help="fail the run on this severity or above (default: high)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.rules:
        for rule in sorted(RULES, key=lambda r: r.severity.rank):
            print(f"{rule.severity.value:<6} {rule.name:<36} {rule.description}")
        return 0

    try:
        report = audit_repository(Path(args.root))
    except (ConsciousSubconsciousError, ConfigurationError) as exc:
        print(f"audit failed: {exc}", file=sys.stderr)
        return 2

    if args.json:
        payload = json.dumps(report.as_dict(), indent=2, sort_keys=True)
    else:
        payload = render_report(report, verbose=not args.quiet)

    if args.out:
        target = Path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload, encoding="utf-8")
        print(f"wrote {target}")
    else:
        print(payload)

    threshold = Severity(args.severity) if args.severity else Severity.HIGH
    failures = [f for f in report.findings if f.severity.rank <= threshold.rank]
    if failures and not args.json:
        print(f"\n{len(failures)} finding(s) at or above '{threshold.value}'.", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
