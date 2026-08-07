# LegacyGuard Development Roadmap

## Current state (2026-08-07)
- Repository is stable on master at `8cfff7a`.
- Phase 5.4 and Phase 5.5 are complete and merged.
- Phase 5.6 extraction reliability is in progress.
- The current slice focuses on handling unsupported or empty document content without undermining scan completion semantics.

## Completed milestones
- Phase 5.1 — Dependency Baseline and CI Health
- Phase 5.2 — Discovery Reliability Hardening
- Phase 5.3 — Discovery Lifecycle Telemetry and Safe Status Visibility
- Phase 5.4 — Background Job Monitoring & Failure Surfacing
  - Added privacy-safe scan status fields for background monitoring: `background_job_state`, `background_job_message`, `retry_count`, `failure_count`, `last_failure_at`
  - Surfaced queue, retry, failure, and completion states consistently in API and UI
  - Expanded backend and frontend regression coverage for background status monitoring

## Upcoming milestones
- Phase 5.6 — Extraction Reliability
  - Improve handling for unsupported or low-quality document formats
  - Preserve clear warning semantics for skipped or failed documents
- Phase 5.7 — Review Queue UX Refinement
  - Improve the finding-review experience and status clarity
