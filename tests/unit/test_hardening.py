"""The self-audit.

Two kinds of test here:

1. **Rule tests** against synthetic text, to prove each rule can fire at all. A
   rule that never fires in a test is a rule nobody knows is broken.
2. **A gate on this repository.** The shipped tree must have no high-severity
   findings. That is what makes the audit load-bearing rather than decorative.

Dangerous strings are assembled at runtime so that this test file does not trip
the rules it is testing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conscious_subconscious.core.errors import ConfigurationError
from conscious_subconscious.hardening import (
    RULES,
    Severity,
    audit_paths,
    audit_repository,
)
from conscious_subconscious.hardening.cli import main as hardening_main

SHELL_TRUE = "shell" + "=True"
EVAL_CALL = "eval" + "("
EXEC_CALL = "exec" + "("
VERIFY_FALSE = "verify" + "=False"
WILDCARD_ORIGINS = "allow_origins=[" + '"*"' + "]"
DEBUG_TRUE = "debug" + "=True"
BIND_ALL = 'host="' + "0.0.0.0" + '"'
SWALLOWED = "try:\n    pass\nexcept Exception:\n    pass\n"
PRINT_CALL = "print" + '("hello")\n'
FAKE_TOKEN = "github_pat_" + "Z" * 24


def scan(tmp_path: Path, source: str, *, name: str = "sample.py") -> set[str]:
    """Write ``source`` to a temp file and return the rule names that fired."""
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return {finding.rule for finding in audit_paths([path], root=tmp_path)}


class TestRulesFire:
    def test_detects_shell_injection(self, tmp_path: Path) -> None:
        assert "no-shell-injection" in scan(tmp_path, f"subprocess.run(cmd, {SHELL_TRUE})")

    def test_detects_dynamic_execution(self, tmp_path: Path) -> None:
        assert "no-dynamic-execution" in scan(tmp_path, f"result = {EVAL_CALL}x)")

    def test_detects_exec(self, tmp_path: Path) -> None:
        assert "no-dynamic-execution" in scan(tmp_path, f"{EXEC_CALL}code)")

    def test_detects_disabled_tls_verification(self, tmp_path: Path) -> None:
        assert "no-disabled-tls-verification" in scan(
            tmp_path, f"requests.get(url, {VERIFY_FALSE})"
        )

    def test_detects_wildcard_cors(self, tmp_path: Path) -> None:
        assert "no-wildcard-cors" in scan(tmp_path, f"app.add_middleware(CORS, {WILDCARD_ORIGINS})")

    def test_detects_debug_mode(self, tmp_path: Path) -> None:
        assert "no-debug-mode" in scan(tmp_path, f"app.run({DEBUG_TRUE})")

    def test_detects_a_wildcard_bind_address(self, tmp_path: Path) -> None:
        assert "no-unauthenticated-non-loopback-bind" in scan(
            tmp_path, f"uvicorn.run(app, {BIND_ALL})"
        )

    def test_detects_a_hardcoded_secret(self, tmp_path: Path) -> None:
        assert "no-hardcoded-secrets" in scan(tmp_path, f'token = "{FAKE_TOKEN}"')

    def test_detects_an_assigned_password(self, tmp_path: Path) -> None:
        assert "no-hardcoded-secrets" in scan(tmp_path, 'password = "' + "u" * 20 + '"')

    def test_detects_a_swallowed_exception(self, tmp_path: Path) -> None:
        assert "no-silent-exception" in scan(tmp_path, SWALLOWED)

    def test_detects_print_in_a_library_module(self, tmp_path: Path) -> None:
        assert "no-print-in-library" in scan(tmp_path, PRINT_CALL)


class TestRulesStayQuiet:
    def test_clean_module_produces_nothing(self, tmp_path: Path) -> None:
        source = "import subprocess\ndef run(cmd):\n    return subprocess.run(cmd, check=True)\n"
        assert scan(tmp_path, source) == set()

    def test_a_type_annotation_is_not_a_secret(self, tmp_path: Path) -> None:
        assert "no-hardcoded-secrets" not in scan(tmp_path, "api_key: str | None = None\n")

    def test_an_empty_env_example_value_is_not_a_secret(self, tmp_path: Path) -> None:
        assert "no-hardcoded-secrets" not in scan(tmp_path, "CS_API_KEY=\n", name=".env.example")

    def test_the_rule_definitions_do_not_trip_the_secret_rule(self) -> None:
        """The patterns are credential-shaped by necessity, not by accident."""
        from conscious_subconscious.hardening.audit import audit_paths as run

        rules_module = (
            Path(__file__).resolve().parents[2]
            / "src"
            / "conscious_subconscious"
            / "hardening"
            / "audit.py"
        )
        findings = run([rules_module], root=rules_module.parents[4])
        assert not [f for f in findings if f.rule == "no-hardcoded-secrets"]

    def test_removing_the_allowlist_would_fire(self, tmp_path: Path) -> None:
        """Proves the allowlist is doing work rather than the pattern being toothless."""
        path = tmp_path / "security.py"
        path.write_text(f'token = "{FAKE_TOKEN}"\n', encoding="utf-8")
        assert "no-hardcoded-secrets" in {
            finding.rule for finding in audit_paths([path], root=tmp_path)
        }


class TestReport:
    def test_is_allowed_matches_globs(self) -> None:
        rule = next(r for r in RULES if r.name == "no-hardcoded-secrets")
        assert rule.is_allowed("tests/unit/test_x.py")
        assert not rule.is_allowed("src/thing.py")

    def test_severity_ranks_are_ordered(self) -> None:
        assert Severity.HIGH.rank < Severity.MEDIUM.rank < Severity.LOW.rank < Severity.INFO.rank

    def test_report_counts_and_dict(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(f"x = {EVAL_CALL}y)\n", encoding="utf-8")
        report = audit_repository(tmp_path)
        assert report.files_scanned >= 1
        assert report.counts()["high"] >= 1
        assert len(report.blocking) >= 1
        payload = json.loads(json.dumps(report.as_dict()))
        assert payload["findings"][0]["severity"] == "high"

    def test_findings_are_deduplicated_per_line(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").write_text(f"x = {EVAL_CALL}y)\n", encoding="utf-8")
        report = audit_repository(tmp_path)
        keys = [(f.rule, f.path, f.line) for f in report.findings]
        assert len(keys) == len(set(keys))

    def test_rejects_a_missing_root(self) -> None:
        with pytest.raises(ConfigurationError):
            audit_repository("/definitely/not/here")

    def test_large_files_are_skipped_with_a_reason(self, tmp_path: Path) -> None:
        (tmp_path / "big.py").write_text("x = 1\n" * 500_000, encoding="utf-8")
        report = audit_repository(tmp_path)
        assert report.skipped and "larger than" in report.skipped[0]
        # The skipped file must not be counted as scanned.
        assert report.files_scanned == 0


class TestRepositoryGate:
    def test_the_shipped_tree_has_no_high_severity_findings(self, repo_root: Path) -> None:
        """The load-bearing assertion: this repository must pass its own audit."""
        report = audit_repository(repo_root)
        blocking = report.blocking
        message = "\n".join(f"{f.path}:{f.line} {f.rule} — {f.excerpt}" for f in blocking)
        assert not blocking, f"high-severity findings:\n{message}"

    def test_the_tree_is_actually_scanned(self, repo_root: Path) -> None:
        report = audit_repository(repo_root)
        assert report.files_scanned > 50

    def test_cli_passes_on_this_repository(self, repo_root: Path) -> None:
        assert hardening_main(["--root", str(repo_root), "--quiet"]) == 0

    def test_cli_json_output_is_valid(self, repo_root: Path, capsys) -> None:
        assert hardening_main(["--root", str(repo_root), "--json"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["blocking"] == 0

    def test_cli_can_list_rules(self, capsys) -> None:
        assert hardening_main(["--rules"]) == 0
        assert "no-hardcoded-secrets" in capsys.readouterr().out
