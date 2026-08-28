# LegacyGuard

LegacyGuard is a privacy-first personal asset continuity and legacy-planning application. It helps people organize assets, beneficiaries, important documents, and discovery results so that information can be reviewed and maintained in one workspace.

> **Alpha status:** Development is active, but LegacyGuard is not production-ready or approved for real personal, financial, medical, estate, credential, or other sensitive data. Use synthetic data only. No public production application is currently available.

LegacyGuard is software, not legal, financial, tax, medical, or estate-planning advice. Consult qualified professionals for decisions in those areas.

The canonical source repository is `LegacyGuard/legacyguard`. It remains private
while public-launch blockers and owner decisions are resolved.

## Implemented in the alpha

The current `master` branch includes:

- registration, login, protected routes, session restoration, and logout
- a workspace home dashboard
- asset and beneficiary management
- the Document Vault, including encrypted document upload for development use
- Discovery overview and document discovery processing
- scan history and scan detail
- the Review Queue and finding detail
- user-initiated conversion of a confirmed, reviewed finding into an asset that remains marked for review
- SQLite support for local development and PostgreSQL compatibility for deployment

Discovery confidence represents signal strength, not proof of ownership, authenticity, value, or legal validity. Production storage, malware scanning, backup and recovery, managed key handling, operational controls, and independent security/privacy review remain required before real-data use.

## Local development

### Prerequisites

- Python 3.12
- Node.js 24 and npm

### Backend

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

On macOS or Linux, use `source .venv/bin/activate` instead. Install the
development/test dependencies and create a local configuration:

```bash
python -m pip install -r requirements-test.txt
cp .env.example .env
```

Runtime-only environments install `requirements.txt`; that file intentionally
excludes validation frameworks and the local S3 emulator. The isolated
deployment smoke harness uses `requirements-smoke.txt`, which adds only its HTTP
test client. That harness uses synthetic SQLite/local-storage settings and is
not evidence of production readiness.

On Windows Command Prompt, use `copy .env.example .env`. Replace every `CHANGE_ME` value in `.env`; generate the Fernet key using the command documented in the template. The template is for development only and is intentionally not a usable production configuration.

Operating-system and process environment variables override values in `.env`. In PowerShell, inspect and remove an inherited `DEBUG` value before continuing with local setup:

```powershell
Get-ChildItem Env:DEBUG
Remove-Item Env:DEBUG -ErrorAction SilentlyContinue
```

`Remove-Item Env:DEBUG` affects only the current PowerShell process; it does not delete a user-level or system-level setting. Other recognized LegacyGuard variables can override the local file in the same way: `APP_NAME`, `ENVIRONMENT`, `DATABASE_URL`, `DATABASE_POOL_SIZE`, `DATABASE_MAX_OVERFLOW`, `DATABASE_POOL_TIMEOUT_SECONDS`, `DATABASE_POOL_RECYCLE_SECONDS`, `SECRET_KEY`, `ENCRYPTION_KEY`, `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `CORS_ALLOWED_ORIGINS`, `DOCUMENT_STORAGE_ROOT`, `DOCUMENT_STORAGE_BACKEND`, and `DISCOVERY_STALE_SCAN_THRESHOLD_SECONDS`. Inspect any unexpected local behavior with `Get-ChildItem Env:` and remove only the conflicting variable from the current process, using the same command pattern, so the synthetic `.env` value is used.

Apply migrations and start the API:

```bash
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

### Frontend

In another terminal, from the repository root:

```bash
cd frontend
npm ci
npm run dev
```

## Validation

Run the backend suite:

```bash
cd backend
python -m pytest
```

Run frontend tests and the production build:

```bash
cd frontend
npm test
npm run build
```

PostgreSQL migration and test coverage also runs in Backend CI. See [the deployment guide](docs/DEPLOYMENT.md) for its synthetic test configuration and production-oriented requirements.

## Security and privacy

- Never commit `.env` files, keys, tokens, credentials, databases, uploaded documents, or real user information.
- Use encrypted transport and an approved secrets manager for any deployed environment.
- Apply least-privilege access and retain privacy-safe audit trails.
- Read [SECURITY.md](SECURITY.md) before reporting a vulnerability.
- Read [the security design](docs/SECURITY.md) and [data-protection guidance](docs/DATA_PROTECTION.md) before evaluating deployment.

## Contributing and project information

LegacyGuard is licensed under the [GNU Affero General Public License v3.0](LICENSE). Focused proposals are welcome, but outside code contributions are not yet accepted because contribution ownership terms remain an owner decision. See the contributing guide before beginning work.

- [Contributing guidance](CONTRIBUTING.md)
- [Project state](docs/PROJECT_STATE.md)
- [Roadmap](docs/ROADMAP.md)
- [Changelog](CHANGELOG.md)
- [Support policy](SUPPORT.md)
- [Funding and sponsor ethics](FUNDING.md)
