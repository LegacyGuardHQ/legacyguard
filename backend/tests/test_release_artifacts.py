import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("release_artifacts", REPO_ROOT / "scripts" / "release_artifacts.py")
assert SPEC and SPEC.loader
release_artifacts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release_artifacts)


@pytest.mark.parametrize(
    ("package_path", "expected"),
    [
        ("node_modules/lru-cache", "lru-cache"),
        ("node_modules/@scope/pkg", "@scope/pkg"),
        ("node_modules/foo/node_modules/bar", "bar"),
        ("node_modules/foo/node_modules/@scope/bar", "@scope/bar"),
        ("deep/nested/node_modules/foo/node_modules/@scope/bar", "@scope/bar"),
    ],
)
def test_package_name_from_lock_path(package_path: str, expected: str) -> None:
    assert release_artifacts.package_name_from_lock_path(package_path) == expected


def test_explicit_frontend_package_name_takes_precedence() -> None:
    metadata = {"name": "explicit-package", "version": "1.0.0"}
    assert release_artifacts.frontend_package_name("node_modules/wrong", metadata) == "explicit-package"


@pytest.mark.parametrize("name", ["", "@scope", "@/package", "scope/package", "bad name"])
def test_malformed_explicit_frontend_package_names_are_rejected(name: str) -> None:
    with pytest.raises(SystemExit):
        release_artifacts.frontend_package_name("node_modules/package", {"name": name, "version": "1.0.0"})


@pytest.mark.parametrize(
    "package_path",
    ["package-without-node-modules", "node_modules/", "node_modules/@scope", "node_modules/@/pkg"],
)
def test_malformed_package_lock_paths_are_rejected(package_path: str) -> None:
    with pytest.raises(SystemExit):
        release_artifacts.package_name_from_lock_path(package_path)


def test_checksum_generation_accepts_normal_and_nested_files(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    nested = artifacts / "nested"
    nested.mkdir(parents=True)
    (artifacts / "alpha.txt").write_text("alpha", encoding="utf-8")
    (nested / "beta.txt").write_text("beta", encoding="utf-8")
    output = artifacts / "SHA256SUMS"

    release_artifacts.generate_checksums(artifacts, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        f"{hashlib.sha256(b'alpha').hexdigest()}  alpha.txt",
        f"{hashlib.sha256(b'beta').hexdigest()}  nested/beta.txt",
    ]


def _make_symlink_or_skip(link: Path, target: Path) -> None:
    try:
        link.symlink_to(target, target_is_directory=target.is_dir())
    except OSError as exc:
        pytest.skip(f"symbolic-link creation is unavailable on this platform: {exc}")


def test_checksum_generation_rejects_in_root_file_symlink(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    target = artifacts / "target.txt"
    target.write_text("safe", encoding="utf-8")
    _make_symlink_or_skip(artifacts / "alias.txt", target)
    with pytest.raises(SystemExit, match="symbolic link or junction"):
        release_artifacts.generate_checksums(artifacts, artifacts / "SHA256SUMS")


def test_checksum_generation_rejects_outside_file_symlink(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    outside = tmp_path / ".env"
    outside.write_text("SECRET=synthetic", encoding="utf-8")
    _make_symlink_or_skip(artifacts / "safe-name.txt", outside)
    with pytest.raises(SystemExit, match="symbolic link or junction"):
        release_artifacts.generate_checksums(artifacts, artifacts / "SHA256SUMS")


def test_candidate_containment_escape_is_rejected(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    with pytest.raises(SystemExit, match="escapes the artifact root"):
        release_artifacts._validate_candidate(artifacts.resolve(), artifacts / ".." / "outside.txt")


@pytest.mark.parametrize("relative", [".env", ".env.production", "data.db", "private_storage/file.txt", "logs/app.log"])
def test_prohibited_artifact_paths_are_rejected(tmp_path: Path, relative: str) -> None:
    artifacts = tmp_path / "artifacts"
    candidate = artifacts / relative
    candidate.parent.mkdir(parents=True, exist_ok=True)
    candidate.write_text("synthetic", encoding="utf-8")
    with pytest.raises(SystemExit, match="prohibited artifact path"):
        release_artifacts.generate_checksums(artifacts, artifacts / "SHA256SUMS")


def test_actual_frontend_lockfile_nested_names_and_purls_are_correct() -> None:
    components = {component["name"]: component for component in release_artifacts.frontend_components()}
    for name in ("lru-cache", "dom-accessibility-api", "rrweb-cssom"):
        assert name in components
        assert "/node_modules/" not in components[name]["name"]
        assert components[name]["purl"].startswith(f"pkg:npm/{name}@")
    assert components["@tanstack/react-query"]["purl"].startswith("pkg:npm/%40tanstack/react-query@")


def test_generated_sboms_are_reproducible_and_path_free(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    release_artifacts.generate_sboms(first)
    release_artifacts.generate_sboms(second)
    for filename in ("backend.cdx.json", "frontend.cdx.json"):
        first_bytes = (first / filename).read_bytes()
        second_bytes = (second / filename).read_bytes()
        assert first_bytes == second_bytes
        document = json.loads(first_bytes)
        assert document["bomFormat"] == "CycloneDX"
        assert document["specVersion"] == "1.5"
        serialized = first_bytes.decode("utf-8").lower()
        assert str(Path.home()).lower() not in serialized
        assert "onedrive" not in serialized
        assert "private_storage" not in serialized
        assert "recovery-bundles" not in serialized
