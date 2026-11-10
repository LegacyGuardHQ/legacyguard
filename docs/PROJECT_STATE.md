# LegacyGuard Project State

## Repository status

The canonical repository is `LegacyGuardHQ/legacyguard`, with `master` as the
default branch. The source repository is public; the product itself is not
publicly launched or production-ready, and public-launch blockers and owner
decisions remain separate work.

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

The source repository is public; the product itself is not publicly launched or
production-ready. GitHub Private Vulnerability Reporting is enabled and is the
preferred private security-reporting route; the owner-controlled, monitored
mailbox documented in `SECURITY.md` remains a verified fallback. The owner has
attested project provenance and publication authority and retained AGPL-3.0
(James Herrera is the current individual copyright holder; this is not formal
legal clearance). Terms for future outside code contributions are not yet
established.

LegacyGuard is temporary project branding; no final commercial name has been
selected. The separate informational website is not the application and does
not provide accounts or document storage. Publishing source code would not
approve the hosted application for production or real data.

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

## Dependency modernization — November 9, 2026

The seven-PR application dependency modernization effort is complete and merged into `master`.

| PR | Upgrade | Merge commit |
|---|---|---|
| #63 | React Router | `ca4305158a0a67a0c40f71c5941217ee73de78c8` |
| #79 | Frontend testing dependencies | `4103909f231ff5dd70396bf77f19b2e8b987045e` |
| #80 | Vite and frontend tooling | `cead0b3551e3dddbaa5ce5ecb767c849785c1c9d` |
| #81 | React and React type definitions | `4de018f044e6369943cc1cade602cda467353d3e` |
| #83 | GitHub Actions | `b69ed83d15b71b66d8a59804356af84ddfa0613b` |
| #82 | Backend dependencies | `a0b4e3d1f497d0e0e769750ce5f887df93032ede` |
| #84 | TypeScript 7 migration | `c21d36e3b4c3f749bf8f00df11c882cabcffeb30` |

The corresponding merge commits were verified in the ancestry of `master`.

### Frontend dependency baseline

The frontend lockfile at the verified commit resolves:

- React and React DOM 19.3.1
- React Router and React Router DOM 7.18.5
- TanStack React Query 5.106.1
- Vite 8.3.6 and `@vitejs/plugin-react` 6.2.1
- Vitest 4.1.12
- TypeScript 7.0.2
- React Testing Library 16.3.3
- User Event 14.6.8
- jsdom 30.1.3

The TypeScript configuration uses:

- `module: "ESNext"`
- `moduleResolution: "bundler"`
- `strict: true`

The coordinated TypeScript 7 migration resolved the historical `TS5108` error caused by legacy `node10` module resolution.

### Backend dependency baseline

The backend requirements at the verified commit include:

- FastAPI 0.162.0
- Starlette 1.10.0
- Uvicorn 0.54.0
- SQLAlchemy 2.1.6
- Alembic 1.20.1
- psycopg 3.3.6
- Pydantic 2.14.1
- pydantic-settings 2.16.2
- PyJWT 2.15.1
- cryptography 50.0.2
- boto3 1.43.121
- pytest 9.2.0
- moto 5.2.5

These represent the verified dependency baseline, not an approval for production deployment.

## Post-merge CI verification — November 9, 2026

The verified `master` commit is:

`c21d36e3b4c3f749bf8f00df11c882cabcffeb30`

Five GitHub workflow runs associated with this exact commit completed successfully:

| Workflow | Run | Result |
|---|---|---|
| Backend CI | [42553656856](https://github.com/LegacyGuardHQ/legacyguard/actions/runs/42553656856) | Success |
| Frontend CI | [42553656809](https://github.com/LegacyGuardHQ/legacyguard/actions/runs/42553656809) | Success |
| Release verification | [42553656879](https://github.com/LegacyGuardHQ/legacyguard/actions/runs/42553656879) | Success |
| CodeQL | [42553657044](https://github.com/LegacyGuardHQ/legacyguard/actions/runs/42553657044) | Success |
| Code Quality: Push on master | [42553656587](https://github.com/LegacyGuardHQ/legacyguard/actions/runs/42553656587) | Success |

All eight required checks completed successfully on this merge commit:

1. Backend tests
2. PostgreSQL migrations and tests
3. Frontend tests and build
4. Backend release checks
5. Frontend release checks
6. RC readiness gate
7. Analyze (python)
8. Analyze (javascript-typescript)

**Classification: Post-merge automated CI baseline healthy.**

This verifies automated integration and release-check results for the specified commit. It does not establish successful production deployment, complete supply-chain security assurance, or permission to process sensitive real-world data.

## Open maintenance follow-ups

The following items remain separate from the completed dependency modernization:

- **Security inventory:** Reconfirm active Dependabot, code-scanning, and secret-scanning alerts using an authorized security interface. The available read-only GitHub connection did not provide the required alert inventory.
- **Superseded dependency PR:** PR #66 remains open. Its TypeScript upgrade was superseded by merged PR #84. Closure requires separate explicit owner authorization.
- **Test-client compatibility:** Review the previously observed Starlette/HTTPX `TestClient` deprecation warning as a non-blocking maintenance issue.
- **Documentation review:** Reconcile historical CodeQL and repository-publication language in `docs/RC_VALIDATION.md` and `docs/PUBLICATION_READINESS.md` through separately reviewed changes.
- **Branch housekeeping:** Review obsolete dependency branches before considering individually approved deletion.

The separate informational website repository and its PR #7 are excluded from this application maintenance work.

## Operational status

Dependency modernization and its automated post-merge validation are complete.

The application remains an internal alpha, with synthetic-data-only use authorized. Outstanding production infrastructure, recovery, operational security, privacy, and independent-review requirements remain unchanged.

No public production application is approved by this dependency modernization milestone.
