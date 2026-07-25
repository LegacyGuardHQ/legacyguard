# LegacyGuard Discovery Intelligence Phase 2 — Safe Report API

Implemented:

- `GET /discovery/scans/{scan_id}/report`
- Ownership enforcement through the existing owned-scan lookup
- Strict Pydantic response schema
- Safe report output containing only scan status, safe timestamps, document/finding counts, category counts, and review-status counts
- No raw evidence, matched terms, document IDs, filenames, account data, or encrypted fields in the response
- API regression tests for response privacy and cross-user access denial
