#!/usr/bin/env python3
"""Build deterministic release inventories and checksum manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import quote

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
    if ecosystem == "npm" and name.startswith("@"):
        scope, package = name.split("/", 1)
        purl_name = f"{quote(scope, safe='')}/{quote(package, safe='')}"
    else:
        purl_name = quote(name, safe="._-")
    return {
        "type": "library",
        "name": name,
        "version": version,
        "purl": f"pkg:{ecosystem}/{purl_name}@{quote(version, safe='._-+')}",
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


def _validate_npm_package_name(name: str, package_path: str) -> str:
    if not name or any(character.isspace() for character in name) or "\\" in name:
        raise SystemExit(f"package-lock entry has an invalid package name: {package_path}")
    if name.startswith("@"):
        scope_and_name = name.split("/")
        if len(scope_and_name) != 2 or scope_and_name[0] == "@" or not scope_and_name[1]:
            raise SystemExit(f"package-lock entry has a malformed scoped package name: {package_path}")
    elif "/" in name:
        raise SystemExit(f"package-lock entry has a malformed package name: {package_path}")
    return name


def package_name_from_lock_path(package_path: str) -> str:
    parts = package_path.split("/")
    node_modules_positions = [index for index, part in enumerate(parts) if part == "node_modules"]
    if not node_modules_positions:
        raise SystemExit(f"package-lock path has no node_modules segment: {package_path}")
    identity = parts[node_modules_positions[-1] + 1 :]
    if not identity or not identity[0]:
        raise SystemExit(f"package-lock path has no package name: {package_path}")
    if identity[0].startswith("@"):
        if len(identity) != 2 or identity[0] == "@" or not identity[1]:
            raise SystemExit(f"package-lock path has a malformed scoped package name: {package_path}")
        return _validate_npm_package_name(f"{identity[0]}/{identity[1]}", package_path)
    if len(identity) != 1:
        raise SystemExit(f"package-lock path has a malformed package name: {package_path}")
    return _validate_npm_package_name(identity[0], package_path)


def frontend_package_name(package_path: str, metadata: dict[str, object]) -> str:
    if "name" in metadata:
        name = metadata["name"]
        if not isinstance(name, str) or not name.strip():
            raise SystemExit(f"package-lock entry has an invalid explicit name: {package_path}")
        return _validate_npm_package_name(name, package_path)
    return package_name_from_lock_path(package_path)


def frontend_components() -> list[dict[str, str]]:
    lock = json.loads(FRONTEND_LOCK.read_text(encoding="utf-8"))
    components: list[dict[str, str]] = []
    for package_path, metadata in lock["packages"].items():
        if not package_path or "version" not in metadata:
            continue
        name = frontend_package_name(package_path, metadata)
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


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _validate_candidate(artifact_root: Path, candidate: Path) -> tuple[Path, Path]:
    try:
        relative = candidate.relative_to(artifact_root)
    except ValueError as exc:
        raise SystemExit(f"artifact path is outside the artifact root: {candidate}") from exc
    if relative == Path(".") or ".." in relative.parts:
        raise SystemExit(f"artifact path escapes the artifact root: {relative.as_posix()}")
    if _is_link_like(candidate):
        raise SystemExit(f"refusing symbolic link or junction: {relative.as_posix()}")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SystemExit(f"artifact path cannot be resolved safely: {relative.as_posix()}") from exc
    if resolved == artifact_root or not resolved.is_relative_to(artifact_root):
        raise SystemExit(f"resolved artifact path escapes the artifact root: {relative.as_posix()}")
    if _prohibited(relative):
        raise SystemExit(f"refusing to checksum prohibited artifact path: {relative.as_posix()}")
    return resolved, relative


def generate_checksums(artifact_dir: Path, output: Path) -> None:
    if _is_link_like(artifact_dir):
        raise SystemExit("artifact root must not be a symbolic link or junction")
    try:
        artifact_root = artifact_dir.resolve(strict=True)
    except OSError as exc:
        raise SystemExit("artifact root does not exist or cannot be resolved") from exc
    if not artifact_root.is_dir():
        raise SystemExit("artifact root is not a directory")

    if _is_link_like(output):
        raise SystemExit("checksum output must not be a symbolic link or junction")
    output_resolved = output.resolve(strict=False)
    if output_resolved == artifact_root or not output_resolved.is_relative_to(artifact_root):
        raise SystemExit("checksum output must remain beneath the artifact root")

    files: list[tuple[Path, Path, Path]] = []
    for current_root, directory_names, file_names in os.walk(artifact_root, topdown=True, followlinks=False):
        current = Path(current_root)
        for directory_name in sorted(directory_names):
            _validate_candidate(artifact_root, current / directory_name)
        for file_name in sorted(file_names):
            candidate = current / file_name
            resolved, relative = _validate_candidate(artifact_root, candidate)
            if resolved != output_resolved:
                files.append((candidate, resolved, relative))
    files.sort(key=lambda item: item[2].as_posix())
    if not files:
        raise SystemExit("artifact directory contains no files")
    lines = []
    for candidate, expected_resolved, relative in files:
        # Recheck immediately before reading to narrow the link-swap window.
        resolved, checked_relative = _validate_candidate(artifact_root, candidate)
        if resolved != expected_resolved or checked_relative != relative or not resolved.is_file():
            raise SystemExit(f"artifact changed during checksum generation: {relative.as_posix()}")
        digest = hashlib.sha256()
        with resolved.open("rb") as artifact:
            for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
                digest.update(chunk)
        lines.append(f"{digest.hexdigest()}  {relative.as_posix()}")
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
