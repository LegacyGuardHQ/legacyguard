# LegacyGuard Phase 2 — Manual Asset Conversion

Implemented a deliberate, user-controlled path for creating an unverified asset record from a confirmed discovery finding.

## Endpoint

`POST /discovery/findings/{finding_id}/assets`

## Safety behavior

- Only a finding owned by the authenticated user can be used.
- The finding must already be `CONFIRMED`.
- The user must explicitly submit the asset name, category, and any optional details.
- Discovery evidence, matched terms, excerpts, filenames, and document content are never copied into the asset.
- The resulting asset is always created with `is_verified = false` and `verification_status = NEEDS_REVIEW`.
- A finding can create at most one asset.
- Review-status changes still never create assets automatically.
- The conversion action is recorded with safe identifier-only audit metadata.

## Database

Added the `discovery_finding_asset_links` table through Alembic revision `a2b3c4d5e6f7`. The separate one-to-one link table avoids coupling findings directly to asset fields and prevents duplicate conversions.

## Validation

- Fresh SQLite migration reached `a2b3c4d5e6f7 (head)`.
- `alembic check` reported no pending schema operations.
- 29 targeted conversion, asset, and review tests passed.
- Full-suite execution reached 200 passing tests; two password-format assertions failed only because the isolated Linux validation used a temporary non-bcrypt authentication stub. Run the complete suite in the project Windows `.venv312` for final validation.
