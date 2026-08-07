# LegacyGuard Development Roadmap

## Current state (2026-08-06)
- Repository is stable on master at `04c4b44f08f7f6a2741f6f48733b7f4dd5af2995`.
- Phase 5.3 is complete and merged.
- The next milestone focuses on background job observability and failure surfacing.

## Completed milestones
- Phase 5.1 — Dependency Baseline and CI Health
- Phase 5.2 — Discovery Reliability Hardening
- Phase 5.3 — Discovery Lifecycle Telemetry and Safe Status Visibility

## Upcoming milestones
- Phase 5.4 — Background Job Monitoring & Failure Surfacing
  - Improve visibility into background discovery and upload-driven scans
  - Surface queue, retry, and failure states consistently
  - Reduce silent failures during background processing
- Phase 5.5 — API Contract Hardening
  - Standardize validation, pagination, and error behavior
  - Keep responses privacy-safe and deterministic
- Phase 5.6 — Extraction Reliability
  - Improve handling for unsupported or low-quality document formats
  - Preserve clear warning semantics for skipped or failed documents
