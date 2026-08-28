# Release candidate validation

This checklist records the validation model used for the published
`v1.1.0-rc.1` alpha prerelease and later candidates. Use synthetic data only.
LegacyGuard is not approved for real sensitive data.

## Identity and clean-clone checks

- Record the approved commit SHA and clone the canonical repository into a new directory on both Windows and a Unix-like system.
- Fetch the exact candidate tag, verify its signature with the documented allowed signers, and confirm its peeled commit equals the approved SHA.
- Follow `README.md` from the clean checkout. Replace every development placeholder with newly generated synthetic values.
- On Windows PowerShell, begin with the documented environment preflight. Confirm an inherited `DEBUG` value is removed from the current process and that no other process environment variable unexpectedly overrides the synthetic `.env` configuration.
- Confirm `app.version.__version__`, FastAPI OpenAPI metadata, `frontend/package.json`, and the root package entries in `frontend/package-lock.json` all report `1.1.0-rc.1`.

## Automated validation

- Install backend dependencies in a new Python 3.12 virtual environment and run `python -m pytest`.
- Install frontend dependencies with `npm ci`, run `npm test`, and run `npm run build`.
- Create a fresh SQLite database and run `python -m alembic upgrade head`; start the backend and verify `/health/live` and `/health/ready`.
- Create a disposable PostgreSQL database, run Alembic zero-to-head, verify migration readiness, and run the backend suite against PostgreSQL.
- Run `python scripts/production_smoke_test.py` as an isolated
  `ENVIRONMENT=testing` packaging/runtime check with disposable SQLite and local
  storage. Do not describe this as a production-configuration test.
- Separately prove production configuration against disposable PostgreSQL and
  object storage. Production must reject SQLite, local document storage, and
  uploads without a configured malware scanner.
- Run `python scripts/rc1_recovery_verification.py` under its isolated
  `ENVIRONMENT=testing` configuration and require all backup, restore,
  rollback, and cleanup success markers. This is not production recovery proof.

## Synthetic end-to-end validation

Using only disposable synthetic records, validate registration, login, Workspace, asset creation, beneficiary creation and association, Document Vault metadata/upload, Discovery processing, Review Queue, finding detail, confirmed-finding-to-asset conversion, and logout. Confirm the converted asset remains marked for review.

## Release artifacts

- Generate the backend and frontend inventories described in `RELEASE_PROCESS.md` from the exact commit.
- Confirm repeated generation produces byte-identical files.
- Inspect generated files for credentials, keys, tokens, environment values, local user paths, private storage paths, logs, databases, and recovery data.
- Generate and independently verify `SHA256SUMS`; record commands and results in the release notes.

## Deferred publication checks

The following cannot complete while the repository remains private or ineligible and must not block the private RC checkpoint:

- verify successful Python and JavaScript/TypeScript CodeQL analysis on the
  exact candidate (custom workflows are active; default setup is unconfigured)
- validate anonymous public cloning
- validate public documentation, security-reporting, issue, and release links
- validate final public repository identity and settings
