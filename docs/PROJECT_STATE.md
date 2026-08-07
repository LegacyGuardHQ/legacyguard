# LegacyGuard Project State

## Repository

- Remote: https://github.com/jh505tt-create/legacyguard.git
- Current master: `04c4b44f08f7f6a2741f6f48733b7f4dd5af2995`
- Development continues from a clean master branch with one milestone per feature branch and pull request.

## Purpose

LegacyGuard is a privacy-first financial asset discovery platform designed to help owners locate retirement accounts, insurance policies, benefits, and estate-related records while preserving privacy, owner isolation, human review, and transparent reporting.

## Engineering Principles

- Privacy first
- Backend contracts before UI
- One feature per branch
- One milestone per PR
- Human review before merge
- No speculative features
- No scope creep
- No hidden technical debt

## Completed Milestones

- Authentication
- Asset Management
- Document Vault
- Discovery Engine
- Review Workflow
- Manual Asset Conversion backend contract
- Phase 4B.1 — Privacy-safe Dashboard Contracts
- Phase 4B.2 — Discovery Overview
- Phase 4B.3 — Scan History
- Phase 4B.4 — Scan Detail
- Phase 4B.5 — Finding Review Queue
- Phase 4B.6 — Finding Detail
- Phase 4B.7 — Review Queue Filtering
- Phase 4B.8 — Manual Asset Conversion UI
- GitHub Actions CI
- Phase 5.1 — Dependency Baseline and CI Health
- Phase 5.2 — Discovery Reliability Hardening
- Phase 5.3 — Discovery Lifecycle Telemetry and Safe Status Visibility
- Phase 5.4 — Background Job Monitoring & Failure Surfacing
- Phase 5.5 — API Contract Hardening

Manual asset conversion remains explicitly user-initiated. Converted assets stay `NEEDS_REVIEW`; LegacyGuard does not automatically verify them.

## Current APIs

- `GET /discovery/dashboard`
- `GET /discovery/scans`
- `GET /discovery/scans/{scan_id}`
- `GET /discovery/scans/{scan_id}/summary`
- `GET /discovery/scans/{scan_id}/report`
- `GET /discovery/scans/{scan_id}/documents`
- `GET /discovery/scans/{scan_id}/findings`
- `GET /discovery/findings/review-queue`
- `GET /discovery/findings/{finding_id}`
- `PATCH /discovery/findings/{finding_id}`
- `POST /discovery/findings/{finding_id}/assets`

`GET /discovery/scans/{scan_id}` now includes privacy-safe background job monitoring fields: `background_job_state`, `background_job_message`, `retry_count`, `failure_count`, and `last_failure_at`.

## Current Roadmap

Completed: Phase 5.4 and Phase 5.5.

Current milestone: Phase 5.6 — Extraction Reliability.

Phase 5.6 work in progress: extraction now treats empty or low-quality documents as completed-with-warnings, surfaces empty-document outcomes as explicit warning codes, and preserves clear semantics for unsupported or failed extraction paths. The review-queue experience also now exposes clearer status and filter guidance, including a summary of the current tab, any active category filter, and the total count of findings in the current view.

## Validation

- Backend: `pytest`
- Frontend: `npm test` and `npm run build`
- Repository: `git diff --check`
