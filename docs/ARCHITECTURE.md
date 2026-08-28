# LegacyGuard Architecture

## Status and scope

LegacyGuard is an alpha, privacy-first personal asset continuity and
legacy-planning application. The implemented system supports one authenticated
owner per account. Trusted-contact, emergency-access, multi-household, and
production operations described as future work are not current capabilities.

The repository is suitable for development with synthetic data only. A public
source release is separate from approval to operate a production service with
real sensitive information.

## Technology stack

### Frontend

- React 19 and TypeScript
- React Router 7
- Vite 8
- TanStack Query 5
- Vitest 4, Testing Library, and jsdom

The browser application lives under `frontend/src`. It uses a shared API client
and protected routes. Server state is managed through TanStack Query. The
browser stores only the short-lived access token in `sessionStorage`; no refresh
workflow is implemented.

### Backend

- Python 3.12
- FastAPI REST API
- Pydantic request and response schemas
- SQLAlchemy 2 and Alembic migrations
- PyJWT access tokens with server-side session records
- Fernet-based application encryption
- Pytest

Backend code lives under `backend/app`, with routes, schemas, models, services,
and security boundaries kept separate where practical.

### Persistence

- SQLite is supported only for local development and isolated tests.
- Production configuration requires PostgreSQL through Psycopg 3.
- Local document storage is supported only for development and tests.
- Production configuration requires private S3-compatible object storage.

Production configuration rejects SQLite and local document storage. Those
checks do not by themselves establish production readiness.

## Request and authorization boundaries

FastAPI routes authenticate access tokens and resolve the associated active
server-side session. Owner-controlled reads and mutations are scoped by both
record identifier and authenticated `user_id`. Generic authentication and
not-found responses are used where more detailed errors could reveal account
or record existence.

The current API surface includes:

- registration, login, logout, session listing, and session revocation
- assets and asset details
- beneficiaries and asset-beneficiary links
- document metadata and encrypted upload
- Discovery scans, reports, findings, review queues, and manual conversion of a
  confirmed finding into an asset that remains marked for review
- liveness and readiness probes

There is no current administrator API. FastAPI OpenAPI documentation is part of
the development surface and must not be treated as a security boundary.

## Data and document protection

Designated sensitive database fields are encrypted before persistence. Document
content uses a generated per-document Fernet data key; encrypted content is
written to the selected storage backend and the key reference is protected by
the application encryption key. Opaque storage locators, encrypted key
references, ciphertext size, version, and integrity metadata are recorded in
the database.

Uploads are bounded and validated for filename, extension, declared MIME type,
and selected magic bytes before encryption. In production, uploads return HTTP
503 unless a malware scanner is configured. The repository provides only the
scanner interface; a real scanner and quarantine workflow remain operational
requirements.

See [DATA_PROTECTION.md](DATA_PROTECTION.md) for field-level boundaries and
[DEPLOYMENT.md](DEPLOYMENT.md) for deployment requirements.

## Authentication and session lifecycle

Successful login returns one short-lived HS256 access token containing a unique
session identifier (`jti`). The server stores the same identifier in a
revocable session record. The session expires with the access-token policy.
Protected routes accept access tokens only.

Refresh tokens and token rotation are not implemented. A new login is required
after access-token expiry. MFA is also not implemented.

Registration attempts and failed-login attempts use database-backed counters.
The current client key is derived from the request peer address, so trusted
proxy handling and edge/distributed abuse protection remain deployment work.

## Discovery model

Discovery analyzes encrypted document content only after authorization and
decryption inside the service boundary. Processing is bounded, and findings are
signals for human review rather than proof of identity, ownership, value, or
legal validity. Assets are never created automatically from a finding.

Background Discovery work currently runs in-process. A durable queue, worker
isolation, and production workload controls are future operational work.

## Operational boundaries and known gaps

Before any real-data service is offered, operators still need:

- real malware scanning and quarantine
- coordinated PostgreSQL/object-storage backup and restore
- managed encryption-key recovery and rotation
- trusted ingress, HTTPS, and proxy configuration
- distributed rate limiting and abuse monitoring
- privacy-safe logs, metrics, alerts, and incident response
- retention, deletion, and backup-expiry policies
- independent security, privacy, accessibility, and legal review

Source availability, passing tests, encryption features, or a version tag must
not be described as production approval.
