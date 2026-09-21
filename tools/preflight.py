#!/usr/bin/env python3
"""Report which parts of the project can actually run on this machine.

Written because every optional extra in this project fails in a different way,
and "it does not work" is not a useful bug report. This prints exactly what is
present, what is absent, and the command that would fix each absence.
"""

from __future__ import annotations

import argparse
import importlib
import json
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PYTHON_MODULES: tuple[tuple[str, str, str], ...] = (
    ("core", "", "the simulation engine; always required"),
    ("yaml", "pip install PyYAML", "YAML pipeline definitions"),
    ("fastapi", "pip install 'conscious-subconscious[api]'", "HTTP service"),
    ("uvicorn", "pip install 'conscious-subconscious[api]'", "HTTP service runtime"),
    ("pydantic", "pip install 'conscious-subconscious[api]'", "request validation"),
    ("httpx", "pip install httpx", "API tests"),
    ("pyserial", "pip install 'conscious-subconscious[devices]'", "serial adapter"),
    ("pylsl", "pip install 'conscious-subconscious[devices]'", "LSL adapter"),
    ("bleak", "pip install 'conscious-subconscious[devices]'", "BLE heart-rate adapter"),
    ("numpy", "pip install 'conscious-subconscious[science]'", "optional heavy numerics"),
    ("matplotlib", "pip install 'conscious-subconscious[science]'", "optional plotting"),
    ("pytest", "pip install 'conscious-subconscious[dev]'", "test suite"),
    ("ruff", "pip install 'conscious-subconscious[dev]'", "linting"),
    ("mypy", "pip install 'conscious-subconscious[dev]'", "type checking"),
    ("jsonschema", "pip install 'conscious-subconscious[dev]'", "protocol schema conformance"),
    ("build", "pip install 'conscious-subconscious[dev]'", "sdist/wheel builds"),
)

EXECUTABLES: tuple[tuple[str, str, str], ...] = (
    ("git", "version control", "always required"),
    ("node", "web console and site", "install Node 20+"),
    ("npm", "web console and site", "ships with Node"),
    ("docker", "container images", "install Docker"),
    ("kubectl", "Kubernetes dry runs", "install kubectl"),
    ("mkdocs", "documentation site", "pip install mkdocs-material"),
)


def check_modules() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, fix, purpose in PYTHON_MODULES:
        if name == "core":
            present = (ROOT / "src" / "conscious_subconscious").is_dir()
            version = "local"
        else:
            try:
                module = importlib.import_module(name)
                present = True
                version = str(getattr(module, "__version__", "unknown"))
            except Exception:
                present = False
                version = ""
        results.append(
            {"name": name, "present": present, "version": version, "purpose": purpose, "fix": fix}
        )
    return results


def check_executables() -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for name, purpose, note in EXECUTABLES:
        path = shutil.which(name)
        results.append(
            {
                "name": name,
                "present": path is not None,
                "path": path or "",
                "purpose": purpose,
                "fix": "none needed" if path else note,
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "executable": sys.executable,
        "repo_root": str(ROOT),
        "modules": check_modules(),
        "executables": check_executables(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return 0

    print(f"python   {payload['python']} ({payload['executable']})")
    print(f"platform {payload['platform']}")
    print()
    print("python modules")
    for entry in payload["modules"]:
        mark = "yes" if entry["present"] else "NO "
        detail = entry["version"] if entry["present"] else entry["fix"]
        print(f"  [{mark}] {entry['name']:<12} {entry['purpose']:<28} {detail}")
    print()
    print("executables")
    for entry in payload["executables"]:
        mark = "yes" if entry["present"] else "NO "
        detail = entry["path"] if entry["present"] else entry["fix"]
        print(f"  [{mark}] {entry['name']:<9} {entry['purpose']:<28} {detail}")
    print()
    missing_core = [
        e for e in payload["modules"] if not e["present"] and e["name"] in {"yaml", "pytest"}
    ]
    if missing_core:
        print("Minimum useful setup:")
        for entry in missing_core:
            print(f"  {entry['fix']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
