# LegacyGuard Development Roadmap

## Current state (2026-08-27)

- Canonical repository: `LegacyGuard/legacyguard`
- Audited baseline: `df05377b1cbec521d5c46b29ad2b7efc40f162ea`
- Maturity: Alpha
- Repository visibility: Private pending public-launch review
- Real sensitive data: Not approved; use synthetic data only
- Current work: public-launch blocker remediation, history/privacy owner
  decisions, accurate documentation, and fail-closed production configuration

## Completed milestones
- Phase 5.1 — Dependency Baseline and CI Health
- Phase 5.2 — Discovery Reliability Hardening
- Phase 5.3 — Discovery Lifecycle Telemetry and Safe Status Visibility
- Phase 5.4 — Background Job Monitoring & Failure Surfacing
  - Added privacy-safe scan status fields for background monitoring: `background_job_state`, `background_job_message`, `retry_count`, `failure_count`, `last_failure_at`
  - Surfaced queue, retry, failure, and completion states consistently in API and UI
  - Expanded backend and frontend regression coverage for background status monitoring

## Upcoming milestones

- Public-source candidate
  - resolve historical identity and user-machine path exposure
  - establish a verified private vulnerability-reporting fallback
  - complete legal/provenance and contribution-intake decisions
  - correct and independently review the external project website
- Production prerequisites
  - integrate real malware scanning and quarantine
  - prove coordinated PostgreSQL/object-storage backup and restore
  - establish managed key recovery and rotation
  - add proxy-aware distributed abuse controls and operational monitoring
- Product reliability
  - improve extraction handling for unsupported or low-quality formats
  - refine review-queue status clarity and accessibility
