# LegacyGuard Audit Metadata Fix

Corrected the SQLAlchemy declarative mapping error caused by using the reserved Python attribute name `metadata` on `AuditLog`.

Changes applied:

- The database column remains named `metadata`.
- The SQLAlchemy model attribute is now `event_metadata`.
- Audit logging writes sanitized structured data through `event_metadata`.
- Restored the tested Discovery Intelligence Phase 1 model, service, API, schema, and regression-test files that depended on this mapping.
- No `.env`, database file, virtual environment, or private storage content is included.

Validation performed in the build environment:

- Python bytecode compilation completed successfully.
- `AuditLog` mapping imported successfully with the database column named `metadata` and Python attribute named `event_metadata`.
- 61 backend model, discovery, reporting, reliability, and extraction tests passed.
- The full API suite was not run here because this environment does not include Passlib. Run `python -m pytest -q` in the existing Windows `.venv312` environment.
