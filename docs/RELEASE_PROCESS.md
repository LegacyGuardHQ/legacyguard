# Release process

## Version authority

`backend/app/version.py` is the authoritative application-version source. FastAPI imports that constant directly. The version fields in `frontend/package.json` and the root package entries in `frontend/package-lock.json` are synchronized mirrors required by frontend tooling. Release review must reject a mismatch.

The document-content encryption format constant and Alembic revision identifiers are independent compatibility identifiers and must never be changed as part of application-version reconciliation.

## Dependency inventories

From the exact release commit, run:

```text
python scripts/release_artifacts.py sbom --output-dir release-artifacts
```

This standard-library tool emits deterministic CycloneDX 1.5 JSON inventories for exactly pinned direct backend requirements and resolved frontend lockfile packages. It requires no application secrets and does not inspect databases, storage, logs, environment files, or local dependency caches. Run it twice in clean temporary directories and compare the bytes before publication. Generated output is release material and is not committed.

## Checksums

Place only approved publication artifacts in an otherwise empty directory, then run:

```text
python scripts/release_artifacts.py checksums --artifact-dir release-artifacts --output release-artifacts/SHA256SUMS
```

Entries are SHA-256 hashes ordered by normalized relative path. Verify on a Unix-like system with `sha256sum --check SHA256SUMS`; on PowerShell, compare each entry with `Get-FileHash -Algorithm SHA256`. The tool refuses known sensitive file/directory forms, but human review of the explicit input directory remains mandatory.

Never include `.env`, databases, private or document storage, logs, recovery bundles or refs, credentials, keys, tokens, `node_modules`, virtual environments, or dependency caches.

## Signing policy

- Authored release commits use SSH signatures. GitHub-verified signatures are acceptable for merge commits created by GitHub.
- Future release tags are annotated, SSH-signed, verified before push, and immutable after publication.
- Historical unsigned tags remain untouched; do not recreate, replace, or move them.
- The executed release process publishes `SHA256SUMS` with a signature or attestation. No new signing key is created solely for a release.

## Artifact policy

Include GitHub source archives from the signed tag, backend/frontend SBOM or dependency inventories, `SHA256SUMS`, its signature or attestation when implemented, release notes, the exact commit SHA, and recorded validation results.

Exclude recovery bundles/private recovery refs, databases, document-storage contents, environment files, credentials, keys/tokens, user/recovery-bearing logs, dependency caches, virtual environments, and `node_modules`. Exclude frontend `dist` until approved as a reproducible deployment artifact, backend wheels until a packaging contract exists, and Docker images until a container/provenance policy exists.
