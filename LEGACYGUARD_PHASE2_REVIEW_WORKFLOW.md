# LegacyGuard Phase 2 Review Workflow

Implemented review-decision correction and reopening for Discovery Intelligence.

- Pending findings may be confirmed or dismissed.
- Confirmed or dismissed findings may be reopened to `PENDING_REVIEW`.
- Confirmed and dismissed decisions may be corrected to the opposite final status.
- Reopened findings return to the default review queue.
- Repeating the same status is rejected with HTTP 409 and does not create a duplicate audit event.
- Audit metadata records only identifiers and status transitions.
- No review action creates an asset automatically.
- Ownership and privacy protections remain unchanged.
