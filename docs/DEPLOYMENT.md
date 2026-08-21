# LegacyGuard deployment guide

## Architecture assumptions

This milestone keeps LegacyGuard on the existing single-instance architecture:

- one backend service
- one frontend build
- one PostgreSQL database (managed service or persistent self-hosted volume)
- one persistent document-storage volume
- environment-based configuration and secrets

## Prerequisites

- Python 3.12 runtime
- Node.js 24 for frontend builds
- PostgreSQL 16 or another currently supported PostgreSQL release
- a persistent filesystem or object-store mount for document storage
- a secret-management process for runtime secrets

## Production environment variables

Required:

- DATABASE_URL
- SECRET_KEY
- ENCRYPTION_KEY
- JWT_SECRET
- ENVIRONMENT
- CORS_ALLOWED_ORIGINS

Optional:

- DEBUG
- DOCUMENT_STORAGE_ROOT
- ACCESS_TOKEN_EXPIRE_MINUTES
- REFRESH_TOKEN_EXPIRE_DAYS
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

SQLite remains supported for local development and isolated tests. It is not
the recommended production database because it does not provide the concurrent
connection, managed-backup, and availability characteristics expected here.

## Secret generation

Generate secrets outside source control:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate a Fernet key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

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
- Re-run the production smoke test after rollback.
- Do not rely on automatic Alembic downgrade.

## Smoke tests

- app starts with production-style configuration
- /health/live succeeds
- /health/ready succeeds
- database and storage checks pass
- authentication still works
- frontend points to the intended API base URL
- run scripts/production_smoke_test.py against a safe temporary production-style configuration

## RC1 recovery verification tool

Use scripts/rc1_recovery_verification.py to execute deterministic backup, restore, and rollback proof using only temporary test artifacts.

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

4. Run the production smoke test:

```bash
python scripts/production_smoke_test.py
```

5. Record the result in the deployment ticket or release notes before sign-off.

## Incident handling

- treat logs as operational evidence only; do not copy secrets, tokens, raw request bodies, or document contents into incident tickets
- look for safe event categories such as startup_begin, startup_complete, ready_check_degraded, auth_failure, and shutdown
- if readiness degrades, verify the database and storage readiness checks and confirm the latest backup before attempting rollback
