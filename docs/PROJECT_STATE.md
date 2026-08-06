# LegacyGuard Project State

## Repository

Remote: https://github.com/jh505tt-create/legacyguard.git

Current master: `d815bdc318e6cc0ccc4154626ef1df9e44ba1fce`

Development uses one feature branch and one pull request per milestone. Branches are created from an updated, clean `master` branch.

## Purpose

LegacyGuard is a privacy-first financial asset discovery platform designed to help users locate unknown retirement accounts, insurance policies, financial assets, benefits, and estate-related records while maintaining strict privacy, owner isolation, transparency, and human verification.

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

Manual asset conversion is explicitly user-initiated. Converted assets remain `NEEDS_REVIEW`; LegacyGuard does not automatically verify them.

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

## Current Roadmap

Completed: Phase 4A, Phase 4B.1 through Phase 4B.8, Phase 5.1, and Phase 5.2.

Next milestone: Phase 5.3 — Discovery Lifecycle Telemetry and Safe Status Visibility.

## Development Workflow

1. Update `master`.
2. Create the milestone feature branch.
3. Implement one milestone.
4. Run focused tests.
5. Run the frontend build.
6. Run `git diff --check`.
7. Perform a read-only review.
8. Fix review findings.
9. Commit.
10. Push.
11. Open a pull request.
12. Complete final review.
13. Merge.

## Validation

Backend: `pytest`

Frontend: `npm test` and `npm run build`

Repository: `git diff --check`
