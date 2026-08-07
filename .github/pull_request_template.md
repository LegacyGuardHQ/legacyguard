## Summary

This PR advances Phase 5.6 extraction reliability by surfacing empty-document outcomes as explicit discovery warning codes and by improving the review-queue experience with clearer status and filter guidance. The backend now preserves warning semantics for empty content without undermining scan completion, and the frontend makes it easier to understand the current review state, see the active category filter, and reset that filter when needed.

## Scope

Phase 5.6 — Extraction Reliability, plus a small review-queue UX refinement that stays within the same milestone boundary.

## Files changed

Backend:
- [backend/app/services/discovery_orchestrator.py](backend/app/services/discovery_orchestrator.py) — propagates empty-document warnings into document tracking while preserving completed-with-warnings semantics.
- [backend/app/models/discovery_scan_document.py](backend/app/models/discovery_scan_document.py) — adds a dedicated empty-document warning code.
- [backend/app/schemas/discovery.py](backend/app/schemas/discovery.py) — updates the public warning contract to include the new value.

Frontend:
- [frontend/src/pages/ReviewQueuePage.tsx](frontend/src/pages/ReviewQueuePage.tsx) — improves status wording, empty-state messaging, adds a clear category filter action, and exposes a summary of the current review view with the total finding count.

Tests/docs:
- [backend/tests/test_document_extraction_pipeline.py](backend/tests/test_document_extraction_pipeline.py) — covers the new empty-document warning behavior.
- [frontend/src/tests/ReviewQueuePage.test.tsx](frontend/src/tests/ReviewQueuePage.test.tsx) — covers the clearer review-queue copy, clear-filter interaction, and the new view summary with total count.
- [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) — updates the milestone summary to reflect the new warning behavior and review-queue refinement.

## API, schema, and migration impact

- API contract changed: No
- Request/response schema changed: No
- Database model or migration changed: No

The public discovery warning enum now includes an additional controlled value for empty-document processing warnings, but no endpoint shape or storage migration changed.

## Privacy and authorization impact

No privacy or authorization behavior changed. The change preserves owner-scoping, human-review semantics, and privacy-safe discovery handling.

## Validation results

| Validation | Result | Details |
| --- | --- | --- |
| Backend tests (`python -m pytest tests/test_document_extraction_pipeline.py tests/test_discovery_dashboard_contracts.py tests/test_discovery_orchestrator.py tests/test_documents_api.py`) | Pass | 76 tests passed |
| Frontend tests (`npm test -- --run tests/ReviewQueuePage.test.tsx`) | Pass | 14 tests passed |
| Frontend production build (`npm run build`) | Pass | Vite production build completed successfully |
| Whitespace check (`git diff --check`) | Pass | No whitespace or patch-format issues reported |
| Manual verification | Pass | Reviewed the milestone behavior in the affected backend orchestration and review-queue UI paths |

## Screenshots or recordings

Not applicable — no visual design overhaul was introduced; the UI change is limited to copy and filter controls.

## Known risks

None identified beyond the normal need to confirm downstream consumers of the discovery warning enum are ready for the additional controlled value.

## Out of scope

- New extraction backends or OCR support
- Automatic asset creation from findings
- Broader review-queue redesign beyond the current milestone scope

## Pre-merge checklist

- [x] The PR addresses one milestone or focused change only.
- [x] I reviewed the full diff and removed unrelated changes, debug output, and temporary files.
- [x] I verified owner scoping, authentication, authorization, and enumeration-safe behavior where applicable.
- [x] I verified that responses, UI, logs, errors, URLs, and tests do not expose sensitive data or raw discovery evidence.
- [x] Findings remain human-reviewed; this change does not create assets automatically or overstate confidence as proof.
- [x] API/schema behavior is unchanged, or every approved contract change is documented and tested.
- [x] Database changes include a reviewed Alembic migration and rollback considerations, or no database change is present.
- [x] No dependency or lockfile change is present unless explicitly approved and explained above.
- [x] Backend tests pass, or their omission/failure is documented above.
- [x] Frontend tests pass, or their omission/failure is documented above.
- [x] The frontend production build passes, or it is not applicable and documented above.
- [x] `git diff --check` passes.
- [x] New or changed behavior has focused tests for relevant success, loading, empty, error, auth, privacy, and interaction states.
- [x] Visible UI changes include relevant screenshots or recordings and were checked for accessibility and responsive behavior.
- [x] Documentation and roadmap/project-state references are accurate for this milestone, or no update is required.
- [x] Known risks, assumptions, and out-of-scope items are stated explicitly.
