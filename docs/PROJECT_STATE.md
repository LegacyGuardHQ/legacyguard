# LegacyGuard Project State

## Repository status

The canonical repository is `LegacyGuard/legacyguard`, with `master` as the
default branch. The repository remains private while public-launch blockers and
owner decisions are resolved.

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

The source repository is being prepared for public visibility, but it is not
yet approved for publication. History privacy, a verified private security
contact, legal/provenance decisions, external website corrections, and final
repository-setting verification remain launch gates.

## Production application readiness

The application is **not ready or approved for real personal or sensitive data**, and no public production application is available. Use synthetic data only.

Production configuration now fails closed unless PostgreSQL and object storage
are selected, and production uploads are unavailable unless a malware scanner
is configured. Production readiness still requires a real scanner and
quarantine workflow, tested backup/restore and key recovery, managed
infrastructure, trusted ingress/proxy configuration, distributed proxy-aware
rate limiting, privacy-safe observability, staging and security testing,
production domains, managed key rotation, retention/deletion policies, and
independent security/privacy review.

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
