# Phase 5.5 Review and Merge Runbook

## Goal

Provide a consistent, privacy-safe merge process for Phase 5.5 API contract hardening.

## Scope covered by this runbook

- Discovery scan status contract hardening and background monitoring fields
- Contract tightening for discovery, documents, assets, beneficiaries, asset-beneficiary links, and legacy compatibility schemas
- Test and build verification for backend and frontend

## Go/No-Go decision

Use **Go** when all items below are true:

1. Backend test suite passes.
2. Frontend test suite passes.
3. Frontend production build passes.
4. `git diff --check` is clean.
5. Review confirms no privacy leaks and owner scoping remains unchanged.
6. Review confirms no DB migrations or dependency changes slipped in.

Use **No-Go** if any of the above fails.

## Reviewer order (recommended)

1. `backend/app/api/discovery.py`
2. `backend/app/schemas/discovery.py`
3. `backend/tests/test_discovery_api.py`
4. `backend/app/schemas/documents.py`
5. `backend/app/schemas/assets.py`
6. `backend/app/schemas/beneficiaries.py`
7. `backend/app/schemas/asset_beneficiaries.py`
8. `backend/tests/test_asset_beneficiaries_api.py`
9. `backend/app/schemas/legacy.py`
10. `backend/tests/test_legacy_schemas.py`
11. `frontend/src/pages/ScanDetailPage.tsx`
12. `frontend/src/tests/ScanDetailPage.test.tsx`
13. `frontend/src/types/discovery.ts`

## Privacy and authorization checks

Confirm all of the following:

1. No decrypted document content or raw evidence in API responses.
2. No storage paths, object keys, or sensitive identifiers exposed.
3. Owner scoping is enforced for reads and mutations.
4. Not-found/auth behavior remains enumeration-safe.

## Validation commands

Run from repository root:

```powershell
Set-Location backend
python -m pytest -q

Set-Location ../frontend
npm test -- --run
npm run build

Set-Location ..
git diff --check
```

## Post-merge watch window

Monitor for the first 30 to 60 minutes:

1. Increased HTTP 422 rates on contract-touched endpoints.
2. Discovery status UI regressions (queued/running/retrying/failed messaging).
3. Support reports tied to stricter contract validation.

## Rollback strategy

Prefer targeted rollback by slice:

1. Discovery contract regressions: revert the discovery contract commits first.
2. Linking regressions: revert asset-beneficiary link hardening commit.
3. Legacy compatibility regressions: revert legacy schema hardening commit.

Only perform full branch rollback if targeted rollback does not stabilize behavior.
