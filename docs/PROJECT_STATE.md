# LegacyGuard Project State

## Repository status

Development is currently hosted in a private recovery repository while restoration of the original `LegacyGuard/legacyguard` repository remains unresolved. This is an operational hosting status, not a decision about the permanent canonical repository name or owner.

Recovery-repository PRs #5 through #12 are merged into `master`. PRs #5 through #10 added the Asset Management UI, Beneficiary Management UI, Document Vault UI, Workspace Dashboard, deployment-aware Alembic database configuration, and PostgreSQL compatibility. PR #11 prepared public/canonical repository onboarding documentation, and PR #12 hardened GitHub security automation.

## Current product capabilities

Current `master` provides:

- authentication, protected routes, session restoration, and logout
- workspace home
- asset and beneficiary management
- Document Vault metadata and encrypted document upload for development use
- Discovery overview and processing
- scan history and scan detail
- Review Queue and finding detail
- user-initiated reviewed-finding-to-asset conversion
- SQLite local-development support and PostgreSQL compatibility

Manual conversion requires a confirmed finding and produces an asset that remains `NEEDS_REVIEW`. Discovery output is evidence for human review, not automatic verification.

## Public source repository readiness

The source repository is being prepared for possible public visibility. CI, documentation, licensing, contribution boundaries, history safety, security reporting, and repository settings are evaluated separately from application production readiness.

The repository remains private. Its permanent location and public-visibility decision are deferred until the original repository restoration outcome is known.

## Production application readiness

The application is **not ready or approved for real personal or sensitive data**, and no public production application is available. Use synthetic data only.

Production readiness still requires managed encrypted document storage, malware scanning and quarantine, tested backup/restore and key recovery, managed PostgreSQL infrastructure, trusted ingress/proxy configuration, production rate limiting, privacy-safe observability, staging and security testing, production domains, managed key rotation, retention/deletion policies, and independent security/privacy review.

## Current API areas

- authentication and session endpoints
- asset and beneficiary endpoints
- document metadata and upload endpoints
- Discovery dashboard, scans, reports, findings, and review queue
- manual confirmed-finding-to-asset conversion

See the source schemas and [architecture documentation](ARCHITECTURE.md) for the detailed contracts.

## Validation

- Backend: `python -m pytest`
- Frontend: `npm test` and `npm run build`
- PostgreSQL: migration chain, readiness check, and backend suite in Backend CI
- Release: release-verification workflow and RC readiness gate
- Repository: `git diff --check`
