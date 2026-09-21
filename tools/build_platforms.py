#!/usr/bin/env python3
"""Build the platform artefacts this project can build *on this machine*.

The important behaviour is what happens when a toolchain is absent. It is
reported as skipped with the reason, not as a failure and certainly not as a
success. A build script that prints "done" after silently building nothing is
how a release ends up missing an artefact nobody notices until install time.

Artefacts
---------
- ``wheel`` and ``sdist`` via ``python -m build`` (all platforms)
- ``docker`` image via ``docker buildx``, for the requested platforms
- ``web`` bundles via ``npm run build`` for ``apps/console`` and ``apps/site``

The matrix in ``deploy/platforms.yaml`` records what is *supported*; this script
records what was *actually built here*.
"""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "deploy" / "out"

WEB_APPS = ("console", "site")
DEFAULT_PLATFORMS = ("linux/amd64", "linux/arm64")


def run(command: list[str], *, cwd: Path, timeout: int = 1800) -> dict[str, Any]:
    """Run a command and capture a structured outcome. Never raises."""
    try:
        completed = subprocess.run(  # noqa: S603 - fixed argv, no shell
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return {"command": " ".join(command), "status": "skipped", "reason": "executable not found"}
    except subprocess.TimeoutExpired:
        return {"command": " ".join(command), "status": "failed", "reason": "timed out"}
    tail = (completed.stdout or "").strip().splitlines()[-12:]
    error_tail = (completed.stderr or "").strip().splitlines()[-12:]
    return {
        "command": " ".join(command),
        "status": "ok" if completed.returncode == 0 else "failed",
        "returncode": completed.returncode,
        "stdout_tail": tail,
        "stderr_tail": error_tail,
    }


def build_python(results: dict[str, Any]) -> None:
    if not (ROOT / "pyproject.toml").is_file():
        results["wheel"] = {"status": "skipped", "reason": "pyproject.toml not found"}
        return
    results["wheel"] = run([sys.executable, "-m", "build", "--wheel"], cwd=ROOT)
    results["sdist"] = run([sys.executable, "-m", "build", "--sdist"], cwd=ROOT)


def build_docker(results: dict[str, Any], platforms: tuple[str, ...]) -> None:
    if shutil.which("docker") is None:
        results["docker"] = {"status": "skipped", "reason": "docker is not on PATH"}
        return
    if shutil.which("buildx") is None:
        # buildx is normally a docker subcommand; check via docker itself.
        probe = run(["docker", "buildx", "version"], cwd=ROOT, timeout=60)
        if probe.get("status") != "ok":
            results["docker"] = {
                "status": "skipped",
                "reason": "docker buildx is unavailable; multi-arch builds need it",
            }
            return
    dockerfile = ROOT / "deploy" / "docker" / "Dockerfile"
    if not dockerfile.is_file():
        results["docker"] = {"status": "skipped", "reason": f"{dockerfile} not found"}
        return
    output = OUT / "images"
    output.mkdir(parents=True, exist_ok=True)
    results["docker"] = run(
        [
            "docker",
            "buildx",
            "build",
            "--file",
            str(dockerfile),
            "--platform",
            ",".join(platforms),
            "--output",
            f"type=oci,dest={output / 'image.tar'}",
            "--tag",
            "conscious-subconscious:local",
            ".",
        ],
        cwd=ROOT,
    )


def build_web(results: dict[str, Any]) -> None:
    if shutil.which("npm") is None:
        results["web"] = {"status": "skipped", "reason": "npm is not on PATH"}
        return
    outcomes: dict[str, Any] = {}
    for app in WEB_APPS:
        app_dir = ROOT / "apps" / app
        if not (app_dir / "package.json").is_file():
            outcomes[app] = {"status": "skipped", "reason": f"apps/{app} has no package.json"}
            continue
        if not (app_dir / "node_modules").is_dir():
            install = run(
                ["npm", "install", "--no-audit", "--no-fund", "--prefer-offline"], cwd=app_dir
            )
            if install.get("status") != "ok":
                outcomes[app] = {"status": "failed", "reason": "npm install failed", **install}
                continue
        outcomes[app] = run(["npm", "run", "build"], cwd=app_dir)
    results["web"] = outcomes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="build every artefact type")
    parser.add_argument("--wheel", action="store_true")
    parser.add_argument("--docker", action="store_true")
    parser.add_argument("--web", action="store_true")
    parser.add_argument(
        "--platforms", default=",".join(DEFAULT_PLATFORMS), help="comma-separated docker platforms"
    )
    parser.add_argument("--out", default="deploy/out/manifest.json")
    args = parser.parse_args(argv)

    if not any([args.all, args.wheel, args.docker, args.web]):
        args.all = True

    platforms = tuple(part.strip() for part in args.platforms.split(",") if part.strip())
    results: dict[str, Any] = {}
    if args.all or args.wheel:
        build_python(results)
    if args.all or args.docker:
        build_docker(results, platforms)
    if args.all or args.web:
        build_web(results)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "requested_platforms": list(platforms),
        "results": results,
        "note": (
            "This records what was built on the machine that ran the script. It is not "
            "a statement that the artefacts have been tested on their target platforms."
        ),
    }

    target = Path(args.out)
    if not target.is_absolute():
        target = ROOT / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    for name, outcome in results.items():
        if isinstance(outcome, dict) and "status" in outcome:
            print(f"{name:<10} {outcome['status']:<8} {outcome.get('reason', '')}")
        elif isinstance(outcome, dict):
            for sub, sub_outcome in outcome.items():
                print(
                    f"{name}.{sub:<8} {sub_outcome.get('status', '?'):<8} {sub_outcome.get('reason', '')}"
                )
    print(f"\nwrote {target}")
    failed = _any_failed(results)
    return 1 if failed else 0


def _any_failed(results: dict[str, Any]) -> bool:
    for value in results.values():
        if not isinstance(value, dict):
            continue
        if value.get("status") == "failed":
            return True
        if "status" not in value and _any_failed(value):
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
