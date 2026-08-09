# LegacyGuard deployment guide

## Architecture assumptions

This milestone keeps LegacyGuard on the existing single-instance architecture:

- one backend service
- one frontend build
- one persistent database volume
- one persistent document-storage volume
- environment-based configuration and secrets

## Prerequisites

- Python 3.12 runtime
- Node.js 24 for frontend builds
- a persistent filesystem for the database and document storage
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

1. Provision persistent storage for the database and documents.
2. Load production environment variables and secrets.
3. Create a backup of existing data before upgrading.
4. Run Alembic migrations:

```bash
cd backend
alembic upgrade head
```

5. Start the backend.
6. Verify /health/live.
7. Verify /health/ready.
8. Serve the frontend build with the correct API base URL.
9. Run smoke tests.

## Health verification

- /health/live should return 200 with {"status": "ok"}
- /health/ready should return 200 with ok checks for database, storage, and migrations

## Backup and restore

Back up:

- the database persistence location
- the document-storage persistence location
- runtime secrets and the encryption key

Restore requires the same environment values and the same encryption key. Losing the encryption key may make encrypted data unrecoverable.

## Rollback

- Keep the previous release artifact available.
- Restore the last known-good backup if a deployment fails.
- Roll back the application build and restart the previous version.
- Do not rely on automatic Alembic downgrade.

## Smoke tests

- app starts with production-style configuration
- /health/live succeeds
- /health/ready succeeds
- database and storage checks pass
- authentication still works
- frontend points to the intended API base URL
