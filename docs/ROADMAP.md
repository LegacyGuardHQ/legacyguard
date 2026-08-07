# LegacyGuard Development Roadmap

## Current state (2026-08-06)
- Repository is stable on master at `04c4b44f08f7f6a2741f6f48733b7f4dd5af2995`.
- Phase 5.4 is complete and ready for PR.
- The next milestone focuses on API contract hardening for consistency and deterministic behavior.

## Completed milestones
- Phase 5.1 — Dependency Baseline and CI Health
- Phase 5.2 — Discovery Reliability Hardening
- Phase 5.3 — Discovery Lifecycle Telemetry and Safe Status Visibility
- Phase 5.4 — Background Job Monitoring & Failure Surfacing
  - Added privacy-safe scan status fields for background monitoring: `background_job_state`, `background_job_message`, `retry_count`, `failure_count`, `last_failure_at`
  - Surfaced queue, retry, failure, and completion states consistently in API and UI
  - Expanded backend and frontend regression coverage for background status monitoring

## Upcoming milestones
- Phase 5.5 — API Contract Hardening
  - Standardize validation, pagination, and error behavior
  - Keep responses privacy-safe and deterministic
- Phase 5.6 — Extraction Reliability
  - Improve handling for unsupported or low-quality document formats
  - Preserve clear warning semantics for skipped or failed documents
