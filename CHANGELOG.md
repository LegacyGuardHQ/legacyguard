# Changelog

This file records notable changes supported by repository history. LegacyGuard
remains alpha software; a version tag does not indicate production approval.

## Unreleased

### Public-launch safety

- Require PostgreSQL/Psycopg and object document storage when
  `ENVIRONMENT=production`.
- Reject production document uploads when no malware scanner is configured.
- Remove the unused refresh-token response and browser storage; authenticated
  sessions now expire with their short-lived access token.
- Move registration-attempt limiting from process memory to shared database
  state while leaving trusted-proxy/edge enforcement as an operational task.
- Correct public documentation to reflect alpha maturity, the canonical
  repository, and unresolved production requirements.

## 1.1.0-rc.1 - 2026-08-26 prerelease

This prerelease is an alpha development snapshot. It is not a stable or
production-ready release and includes no packaged release artifacts.

### Features

- Added the Workspace dashboard and Asset Management, Beneficiary Management, and Document Vault interfaces.
- Integrated Discovery overview, scan history/detail, Review Queue, finding detail, and confirmed-finding-to-asset conversion into the workspace. Converted assets remain marked for review.
- Added frontend design tokens, accessibility improvements, component guidance, Storybook configuration, reusable state components, and loading skeletons.

### Security and reliability

- Rejected default cryptographic keys outside tests.
- Bounded document upload reads, registration inputs, registration attempts, and concurrent Discovery scan processing.
- Moved login-failure limiting to shared database state.
- Corrected document storage so all relevant services honor the configured storage root.
- Added dependency auditing, immutable GitHub Action pins, disabled checkout credential persistence, Dependabot, and custom CodeQL workflows. CodeQL analysis is active and successful on the canonical revision; GitHub default setup remains unconfigured.
- Expanded backend and frontend regression coverage and corrected frontend CI reliability.

### Database

- Added PostgreSQL/Psycopg compatibility, connection-pool controls, and production-oriented database guidance. This does not mean the application is approved for production or real sensitive data.
- Made Alembic honor the deployment `DATABASE_URL` and made migrations dialect-aware.
- Added PostgreSQL zero-to-head migration, readiness, and backend test coverage in CI. SQLite remains supported for local development and isolated tests.

### Release and CI

- Added backend and frontend release checks, an RC readiness gate, and isolated synthetic deployment smoke testing. The smoke harness does not prove production readiness.
- Added public-readiness licensing, governance, contribution, support, issue, and security guidance.

### Compatibility notes

- Registration now enforces email lengths of 3–254 characters and password lengths of 12–128 characters.
- Registration and login may return HTTP 429 when rate limits are reached.
- Authenticated users now land on `/workspace`; `/discovery` remains available.
- SQLite remains supported for local development and isolated tests.

## v1.0.1

`v1.0.1` is an earlier tagged release. This changelog does not reconstruct
release details that were not recorded at the time; consult the tag and its
reachable Git history for the authoritative historical contents.
