#!/usr/bin/env python3
"""Generate a CycloneDX-style SBOM for the project.

Written by hand rather than pulled from a library for one reason: the interesting
part of this project's dependency story is which packages are *optional*, and
that information lives in ``pyproject.toml`` under ``[project.optional-dependencies]``.
A generic scanner reports a flat list and loses it.

The core package has no runtime dependencies at all. That is a deliberate
property worth making visible in the SBOM.

Output is CycloneDX-shaped JSON. It is not claimed to be schema-valid: no
CycloneDX validator is run against it, and the field names are a subset.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import sys
import sysconfig
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11
    tomllib = None  # type: ignore[assignment]

_SPEC_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+)\s*(.*)$")


def read_pyproject() -> dict:
    if tomllib is None:
        raise RuntimeError("generating the SBOM needs Python 3.11+ (tomllib)")
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def parse_requirement(requirement: str) -> dict[str, str]:
    match = _SPEC_RE.match(requirement)
    if not match:
        return {"name": requirement, "version": "unknown"}
    name, specifier = match.group(1), match.group(2).strip()
    return {"name": name, "version": specifier or "any"}


def installed_version(name: str) -> str | None:
    try:
        from importlib.metadata import PackageNotFoundError, version  # noqa: PLC0415
    except ImportError:  # pragma: no cover
        return None
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def build_sbom() -> dict:
    data = read_pyproject()
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {})
    runtime = [entry for entry in project.get("dependencies", []) if entry.strip()]

    components: list[dict] = []
    core_has_no_dependencies = not runtime

    for requirement in runtime:
        parsed = parse_requirement(requirement)
        parsed["scope"] = "runtime"
        parsed["resolved"] = installed_version(parsed["name"]) or ""
        components.append(parsed)

    for extra, requirements in sorted(optional.items()):
        for requirement in requirements:
            parsed = parse_requirement(requirement)
            parsed["scope"] = f"optional:{extra}"
            parsed["resolved"] = installed_version(parsed["name"]) or ""
            components.append(parsed)

    seen: set[tuple[str, str]] = set()
    unique: list[dict] = []
    for component in components:
        key = (component["name"].lower(), component["scope"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(component)

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:conscious-subconscious-{project.get('version', '0.0.0')}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "component": {
                "type": "application",
                "name": project.get("name", "conscious-subconscious"),
                "version": project.get("version", "0.0.0"),
                "description": project.get("description", ""),
                "licenses": [{"license": {"id": "MIT"}}],
            },
            "properties": [
                {"name": "cs:core_runtime_dependencies", "value": len(runtime)},
                {
                    "name": "cs:core_has_no_dependencies",
                    "value": str(core_has_no_dependencies).lower(),
                },
                {"name": "cs:python", "value": platform.python_version()},
                {"name": "cs:platform", "value": sysconfig.get_platform()},
            ],
        },
        "components": [
            {
                "type": "library",
                "name": component["name"],
                "version": component["resolved"] or component["version"],
                "properties": [
                    {"name": "cs:scope", "value": component["scope"]},
                    {"name": "cs:specifier", "value": component["version"]},
                ],
            }
            for component in unique
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="sbom.json", help="output path")
    parser.add_argument("--json", action="store_true", help="print to stdout instead")
    args = parser.parse_args(argv)

    try:
        sbom = build_sbom()
    except Exception as exc:
        print(f"could not build the SBOM: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(sbom, indent=2, sort_keys=False)
    if args.json:
        print(payload)
        return 0

    target = Path(args.out)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload + "\n", encoding="utf-8")

    scopes: dict[str, int] = {}
    for component in sbom["components"]:
        scope = next(
            prop["value"] for prop in component["properties"] if prop["name"] == "cs:scope"
        )
        scopes[scope] = scopes.get(scope, 0) + 1
    print(f"wrote {target}")
    print(f"  components: {len(sbom['components'])}")
    for scope, count in sorted(scopes.items()):
        print(f"    {scope}: {count}")
    if sbom["metadata"]["properties"][1]["value"] == "true":
        print("  core runtime dependencies: none (by design)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
