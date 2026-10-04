# Repository Map

## Current project

- Canonical repository: `LegacyGuardHQ/legacyguard`
- Default branch: `master`
- Project stage: pre-production alpha; development and testing use synthetic data only
- Repository visibility: public source repository; the product is not publicly launched
- Product name: LegacyGuard is temporary project branding; no final commercial name has been selected

The application is not approved for real personal, financial, estate, document,
or other sensitive data. Publishing source code does not mean a hosted
application is production-ready. The informational website is maintained
separately and is not connected to application accounts or document storage.

## Source layout

- `backend/app/`: FastAPI application, API routes, schemas, models, database,
	security, and services
- `backend/alembic/`: database migration environment and revisions
- `backend/tests/`: backend unit, API, migration, storage, and security tests
- `frontend/src/`: React and TypeScript application, API client, routes,
	components, hooks, styles, and tests
- `docs/`: architecture, data protection, deployment, project state, release,
  and security guidance
- `scripts/`: release-artifact, smoke, recovery-validation, and security-gate
  tooling
- `.github/`: CI workflows, issue templates, and repository guidance

## Development and validation

Use the setup and synthetic-data instructions in the root `README.md`. The
normal local validation is the backend pytest suite, frontend Vitest suite,
frontend production build, dependency audits, and the pinned local security gate
documented by `scripts/security/Invoke-LegacyGuardSecurityGate.ps1`.

Pull requests target `master`; GitHub Actions run backend, PostgreSQL migration,
frontend, release, and configured security checks. Check current repository
settings and workflow results before relying on a required check. CodeQL remains
disabled unless the owner separately enables the repository variable.
