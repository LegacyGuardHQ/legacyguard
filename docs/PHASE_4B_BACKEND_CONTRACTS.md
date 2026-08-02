# Phase 4B Backend Dashboard Contracts

This increment supplies owner-scoped, privacy-limited data for the discovery dashboard. It does not expose decrypted evidence, matched terms, original filenames, checksums, storage references, document bytes, or extracted document text.

## Endpoints

### `GET /discovery/dashboard`

Returns aggregate counts and at most five recent scans owned by the authenticated user.

The response includes:

- `total_scans` and a zero-filled `scans_by_status` object covering `PENDING`, `RUNNING`, `COMPLETE`, `COMPLETED_WITH_WARNINGS`, and `FAILED`.
- `total_findings`, category counts, and a zero-filled `findings_by_review_status` object covering `PENDING_REVIEW`, `CONFIRMED`, and `DISMISSED`.
- `pending_reviews`, which is the `PENDING_REVIEW` finding count; it is not a count of documents still being processed.
- `recent_scans`, containing at most five scans ordered by creation time descending and scan ID descending.

An account with no discovery data receives zero totals, complete zero-filled status objects, an empty category object, and an empty recent-scan list.

### `GET /discovery/scans/{scan_id}/documents`

Returns safe display metadata for documents attached to an owned scan.

Document processing states:

- `PENDING`: queued but processing has not started.
- `PROCESSING`: extraction or discovery processing is underway.
- `COMPLETED`: processing finished without a recorded warning.
- `SKIPPED`: processing could not be performed because of a known, non-fatal capability limitation.
- `FAILED`: processing encountered a failure. The response provides only a controlled warning code, never internal exception details.

Controlled warning codes:

- `UNSUPPORTED_EXTRACTION`: the document format or content could not be extracted by the current pipeline.
- `PROCESSING_FAILED`: processing failed; internal error details remain server-side.

These states describe discovery processing only. They do not assert that a document is legally valid, verified by the user, or converted into an asset.

### `GET /discovery/findings/{finding_id}`

Returns the finding category, confidence score, human-review state, and safe source-document identity for an owned finding. Confidence represents the rule engine's extraction or relevance strength; it does not establish ownership, authenticity, value, or legal certainty.

The contract deliberately excludes decrypted evidence and matched terms. Any later source-context feature requires a separate, narrowly authorized contract and must not broaden this response implicitly.

## Privacy and authorization invariants

- Every query is scoped to the authenticated owner.
- A resource owned by another user is indistinguishable from a missing resource and returns `404`.
- Aggregate responses cannot include another user's records.
- Storage locations, filenames, document contents, extracted text, encrypted fields, and internal errors are not returned.
- These contracts do not claim zero-knowledge processing or regulatory compliance.
