# LegacyGuard deployment guide

## Architecture assumptions

This milestone keeps LegacyGuard on the existing single-instance architecture:

- one backend service
- one frontend build
- one PostgreSQL database (managed service or persistent self-hosted volume)
- one private persistent document-storage backend
- environment-based configuration and secrets

## Prerequisites

- Python 3.12 runtime
- Node.js 24 for frontend builds
- PostgreSQL 16 or another currently supported PostgreSQL release
- a private S3-compatible object store for production document storage
- a secret-management process for runtime secrets

## Production environment variables

Required:

- DATABASE_URL
- SECRET_KEY
- ENCRYPTION_KEY
- JWT_SECRET
- ENVIRONMENT
- CORS_ALLOWED_ORIGINS
- DOCUMENT_STORAGE_BACKEND (`OBJECT` is mandatory in production)
- DOCUMENT_OBJECT_BUCKET

Optional:

- DEBUG
- DOCUMENT_STORAGE_ROOT
- DOCUMENT_OBJECT_PREFIX (default: `legacyguard`)
- DOCUMENT_OBJECT_REGION
- DOCUMENT_OBJECT_ENDPOINT_URL (for S3-compatible providers; HTTPS is required outside development/testing)
- DOCUMENT_OBJECT_ADDRESSING_STYLE (`auto`, `virtual`, or `path`; default: `auto`)
- DOCUMENT_OBJECT_CONNECT_TIMEOUT_SECONDS (default: 5)
- DOCUMENT_OBJECT_READ_TIMEOUT_SECONDS (default: 30)
- DOCUMENT_OBJECT_MAX_ATTEMPTS (default: 3)
- DOCUMENT_OBJECT_ACCESS_KEY_ID, DOCUMENT_OBJECT_SECRET_ACCESS_KEY, and DOCUMENT_OBJECT_SESSION_TOKEN (optional explicit credentials; prefer the provider SDK credential chain)
- DOCUMENT_MASTER_KEY_ID (non-secret identifier for the current document master key; defaults to `legacy-current-v1`)
- ACCESS_TOKEN_EXPIRE_MINUTES
- DISCOVERY_STALE_SCAN_THRESHOLD_SECONDS
- DATABASE_POOL_SIZE (default: 5)
- DATABASE_MAX_OVERFLOW (default: 10)
- DATABASE_POOL_TIMEOUT_SECONDS (default: 30)
- DATABASE_POOL_RECYCLE_SECONDS (default: 1800)

## PostgreSQL connection

Psycopg 3 is the supported PostgreSQL driver. LegacyGuard accepts provider URLs
beginning with `postgres://` or `postgresql://` and normalizes them to the
SQLAlchemy `postgresql+psycopg://` dialect. An explicit dialect URL is also
accepted:

```text
postgresql+psycopg://APP_USER:PERCENT_ENCODED_PASSWORD@DB_HOST:5432/DB_NAME?sslmode=require
```

Keep the complete URL in the deployment secret store. Percent-encode reserved
characters in credentials and never print the resolved URL in logs or CI output.

Require encrypted transport in production. `sslmode=require` prevents plaintext
transport; prefer `sslmode=verify-full` with the provider CA root when the
hosting platform exposes certificate configuration. Follow the provider's
certificate-rotation guidance rather than embedding certificates in the image.

The application uses SQLAlchemy's bounded queue pool with connection liveness
checks. The defaults allow 5 persistent connections and 10 temporary overflow
connections per backend process. Size the database connection limit for
`(pool size + max overflow) * backend process count`, leaving capacity for
migrations, administration, monitoring, and provider-reserved connections.

## Database roles and privileges

Use separate credentials when the hosting platform supports them:

- a migration role that owns the LegacyGuard schema and can create, alter, and
  drop schema objects during a reviewed deployment migration
- a runtime role with `CONNECT` on the database, `USAGE` on the application
  schema, and only the required `SELECT`, `INSERT`, `UPDATE`, and `DELETE` table
  privileges plus sequence usage

Neither role should be a PostgreSQL superuser or have `CREATEDB`/`CREATEROLE`.
Configure default privileges so new migration-created tables and sequences are
usable by the runtime role. Revoke broad `PUBLIC` schema creation rights where
the provider permits it. Store and rotate both credentials independently.

SQLite remains supported for local development and isolated tests. Production
startup rejects both in-memory and file-backed SQLite and requires a supported
PostgreSQL URL normalized to the Psycopg 3 driver.

## Secret generation

Generate secrets outside source control:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## S3-compatible document storage

Set `DOCUMENT_STORAGE_BACKEND=OBJECT` and configure a private bucket. The adapter
stores only application-encrypted ciphertext under
`<prefix>/documents/<document UUID>/<random UUID>.lgdoc`; it never creates public
URLs or returns bucket details through the API. Keep public access blocked, grant
the runtime identity only the required bucket/object operations, require TLS, and
use short-lived workload credentials or instance roles where the provider supports
them. Explicit access-key settings are optional and must come from the deployment
secret store, never source control.

For AWS S3, omit `DOCUMENT_OBJECT_ENDPOINT_URL` and configure the region. For
Cloudflare R2, set the account-specific HTTPS S3 endpoint and use the provider's
documented region value. For Backblaze B2, use its region-specific HTTPS S3
endpoint. Select path-style addressing only when the provider requires it.

LegacyGuard verifies each completed write with an exact-key `HEAD`, ciphertext
length, and ciphertext SHA-256 metadata, and verifies ciphertext again on reads
against database-authoritative size and SHA-256 values. A random object key and
conditional create prevent accidental overwrite. Provider object version IDs are
recorded when returned, but the current lifecycle operates on the exact object key.
If bucket versioning is enabled, deletion may create a delete marker rather than
erasing older versions; retention and permanent-version deletion therefore remain
an operator policy responsibility. Provider-side encryption and versioning are
useful defense in depth but do not replace LegacyGuard application encryption,
authorization, backup coordination, or key recovery.

## Deployment sequence

1. Provision PostgreSQL and persistent document storage.
2. Load production environment variables and secrets.
3. Create a backup of existing data before upgrading.
4. Run Alembic migrations:

```bash
cd backend
alembic upgrade head
```

The Alembic CLI reads `DATABASE_URL` from the deployment environment. Confirm
that it identifies the intended database before running the command; never
substitute a production URL in local smoke or migration tests.

For a new PostgreSQL database, first prove the same operation against an empty,
disposable database. The Backend CI `PostgreSQL migrations and tests` job runs
the entire migration chain from zero to head, verifies readiness, and executes
the backend suite against PostgreSQL 16 on every pull request.

5. Start the backend.
6. Verify /health/live.
7. Verify /health/ready.
8. Serve the frontend build with the correct API base URL.
9. Run smoke tests.

## Health verification

- /health/live should return 200 with {"status": "ok"}
- /health/ready should return 200 with ok checks for database, storage, and migrations
- degraded readiness returns 503 and should be logged as a safe operational event without exposing internals

## Backup and restore

`LocalDocumentStorage` remains intended for development, tests, and synthetic
single-instance validation; production startup rejects it. The S3-compatible
adapter supplies durable encrypted object persistence. Production uploads are
rejected with HTTP 503 unless a malware scanner is configured, but a real
scanner, quarantine workflow, coordinated blob/database backup and restore,
production key recovery, deployment monitoring, and an approved retention
policy are not implemented yet. Real sensitive documents must not be admitted.

Back up:

- the database persistence location
- the document-storage persistence location
- runtime secrets and the encryption key

Verify backups before deployment:

- confirm the backup files are readable
- confirm the latest backup timestamp is current
- confirm the encryption key is available in the secret store

Restore requires the same environment values and the same encryption key. Losing the encryption key may make encrypted data unrecoverable.

## Rollback

- Keep the previous release artifact available.
- Restore the last known-good backup if a deployment fails.
- Roll back the application build and restart the previous version.
- Verify /health/live and /health/ready after rollback.
- Re-run the isolated deployment smoke test after rollback, then run a separate
  environment-specific production verification against disposable resources.
- Do not rely on automatic Alembic downgrade.

## Isolated deployment smoke test

- app starts with isolated testing configuration
- /health/live succeeds
- /health/ready succeeds
- database and storage checks pass
- authentication still works
- run `scripts/production_smoke_test.py` only with synthetic temporary data

This harness intentionally uses SQLite and local storage under
`ENVIRONMENT=testing`. It validates packaging and basic runtime behavior; it
does not bypass production safeguards or prove a production deployment ready.

## RC1 recovery verification tool

Use scripts/rc1_recovery_verification.py to execute deterministic backup,
restore, and rollback proof under `ENVIRONMENT=testing` using only temporary
SQLite, local-storage, and synthetic test artifacts. It is not a production
backup/restore proof.

Requirements:

- Python 3.12.x
- repository backend dependencies installed in the known-good backend Python 3.12 environment

Run from repository root:

```bash
backend/.venv312/Scripts/python.exe scripts/rc1_recovery_verification.py
```

Expected success criteria:

- exit code is 0
- BACKUP_EXECUTED_AND_VERIFIED appears
- RESTORE_EXECUTED_AND_VERIFIED appears
- ROLLBACK_EXECUTED_AND_VERIFIED appears
- CLEANUP_SUCCESS appears

Safety constraints:

- uses temporary SQLite and temporary document storage only
- uses temporary generated test-only secrets and encryption key
- does not use real production data or credentials
- do not substitute production secrets, production databases, or production storage paths

## RC release gate

Treat the following as the minimum release gate before promoting a release candidate:

1. Run the backend test suite:

```bash
cd backend
python -m pytest
```

2. Run the frontend test suite and production build:

```bash
cd frontend
npm test
npm run build
```

3. Verify the database can be upgraded to the latest Alembic head:

```bash
cd backend
alembic upgrade head
```

4. Run the isolated deployment smoke test:

```bash
python scripts/production_smoke_test.py
```

5. Record the result in the deployment ticket or release notes before sign-off.

## Incident handling

- treat logs as operational evidence only; do not copy secrets, tokens, raw request bodies, or document contents into incident tickets
- look for safe event categories such as startup_begin, startup_complete, ready_check_degraded, auth_failure, and shutdown
- if readiness degrades, verify the database and storage readiness checks and confirm the latest backup before attempting rollback
