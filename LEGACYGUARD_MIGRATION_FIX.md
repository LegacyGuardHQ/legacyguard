# LegacyGuard SQLite Migration Fix

This build corrects the beneficiary migration so SQLite can upgrade from revision `8d3c2f1a9b70` without Alembic's batch-table circular dependency error.

Validated in the preparation environment:

- Fresh SQLite database migrated from base through `f1a2b3c4d5e6 (head)`.
- `python -m alembic check` reported `No new upgrade operations detected.`
- Full application tests should be run in the existing Windows `.venv312`, where project dependencies such as Passlib are installed.

For an existing database left partially modified by the failed migration, create a fresh development database rather than retrying against the partial file.
