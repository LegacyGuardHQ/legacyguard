#!/usr/bin/env python3
"""Build deterministic release inventories and checksum manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_REQUIREMENTS = ROOT / "backend" / "requirements.txt"
VERSION_FILE = ROOT / "backend" / "app" / "version.py"
FRONTEND_LOCK = ROOT / "frontend" / "package-lock.json"
EXCLUDED_PARTS = {
    ".env",
    ".venv",
    "node_modules",
    "private_storage",
    "recovery-bundles",
    "venv",
}
EXCLUDED_SUFFIXES = {".db", ".key", ".log", ".pem", ".sqlite", ".sqlite3"}


def _component(name: str, version: str, ecosystem: str) -> dict[str, str]:
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:{ecosystem}/{name}@{version}",
    }


def backend_components() -> list[dict[str, str]]:
    components: list[dict[str, str]] = []
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)(?:\[[^]]+\])?==([^\s;]+)$")
    for raw_line in BACKEND_REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise SystemExit(f"backend requirement is not exactly pinned: {line}")
        components.append(_component(match.group(1).lower(), match.group(2), "pypi"))
    return sorted(components, key=lambda item: (item["name"], item["version"]))


def frontend_components() -> list[dict[str, str]]:
    lock = json.loads(FRONTEND_LOCK.read_text(encoding="utf-8"))
    components: list[dict[str, str]] = []
    for package_path, metadata in lock["packages"].items():
        if not package_path or "version" not in metadata:
            continue
        name = metadata.get("name") or package_path.removeprefix("node_modules/")
        components.append(_component(name, metadata["version"], "npm"))
    return sorted(components, key=lambda item: (item["name"], item["version"], item["purl"]))


def application_version() -> str:
    match = re.search(r'^__version__ = "([^"]+)"$', VERSION_FILE.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise SystemExit("authoritative application version was not found")
    return match.group(1)


def write_sbom(path: Path, name: str, components: list[dict[str, str]]) -> None:
    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": name, "version": application_version()}},
        "components": components,
    }
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def generate_sboms(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_sbom(output_dir / "backend.cdx.json", "legacyguard-backend", backend_components())
    write_sbom(output_dir / "frontend.cdx.json", "legacyguard-frontend", frontend_components())


def _prohibited(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    contains_env_file = any(part == ".env" or part.startswith(".env.") for part in lowered_parts)
    return contains_env_file or bool(lowered_parts & EXCLUDED_PARTS) or path.suffix.lower() in EXCLUDED_SUFFIXES


def generate_checksums(artifact_dir: Path, output: Path) -> None:
    artifact_dir = artifact_dir.resolve()
    output = output.resolve()
    files = sorted(
        (path for path in artifact_dir.rglob("*") if path.is_file() and path.resolve() != output),
        key=lambda path: path.relative_to(artifact_dir).as_posix(),
    )
    if not files:
        raise SystemExit("artifact directory contains no files")
    prohibited = [path for path in files if _prohibited(path.relative_to(artifact_dir))]
    if prohibited:
        names = ", ".join(path.relative_to(artifact_dir).as_posix() for path in prohibited)
        raise SystemExit(f"refusing to checksum prohibited artifact paths: {names}")
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(artifact_dir).as_posix()}")
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    sbom = subparsers.add_parser("sbom")
    sbom.add_argument("--output-dir", type=Path, required=True)
    checksums = subparsers.add_parser("checksums")
    checksums.add_argument("--artifact-dir", type=Path, required=True)
    checksums.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "sbom":
        generate_sboms(args.output_dir)
    else:
        generate_checksums(args.artifact_dir, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
