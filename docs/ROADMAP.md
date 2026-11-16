# LegacyGuard Development Roadmap

LegacyGuard is temporary project branding; no final commercial product name
has been selected. The application is pre-production software. Use synthetic
data only; real sensitive data is not approved. Source publication and product
production readiness are separate decisions.

## Current stage

- Product maturity: internal alpha
- Canonical repository: `LegacyGuardHQ/legacyguard`, default branch `master`
- Repository visibility: public source repository; the product is not publicly launched
- Safe use: local development and testing with synthetic data
- Public production service: none is available or approved

See [PROJECT_STATE.md](PROJECT_STATE.md) for the current implementation and
operational gaps. See [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md) for
the source-publication owner actions and branch-protection recommendations.

## Completed engineering milestones

- Phase 5.1 - Dependency baseline and CI health
- Phase 5.2 - Discovery reliability hardening
- Phase 5.3 - Discovery lifecycle telemetry and safe status visibility
- Phase 5.4 - Background job monitoring and failure surfacing
  - Added privacy-safe background job state, retry, failure, and completion
    reporting in the API and UI.
  - Added backend and frontend regression coverage for these states.

## Next stages

1. **Public source readiness:** provenance and publication authority have been
   reviewed and owner-attested (AGPL-3.0 retained); the source repository is
   now public, GitHub Private Vulnerability Reporting is enabled, and the
   verified private mailbox remains a fallback route. The product itself is not
   publicly launched or production-ready. Remaining work: review the separate
   informational website.
2. **Safe demonstration:** offer only informational or synthetic-data
   demonstrations. Do not collect real accounts, documents, or personal data.
3. **Controlled private beta:** only after private hosting, verified
   authentication and abuse controls, malware scanning/quarantine, managed key
   lifecycle, coordinated backup/restore, retention/deletion, monitoring, and
   independent security/privacy/legal review are complete.
4. **Public beta and general availability:** require additional capacity,
   incident response, support, accessibility, reliability, and operational
   evidence appropriate to the user population and data risk.

## Product reliability work

- Improve handling and user messaging for unsupported or low-quality document
  extraction.
- Continue review-queue clarity and accessibility improvements.
- Keep discovery findings as signals for human review; do not automatically
  create or verify assets.

## Security and sponsorship milestone tracking — proposed November 16, 2026

See [Sponsorship and engineering milestones](SPONSORSHIP_MILESTONES.md) for seven evidence-gated milestones covering: (A) persisted scan-state and document-access protection, (B) trusted scanning and quarantine, (C) protected operations and recovery, (D) independent security/privacy/legal review, (E) accessibility and synthetic-data evaluation, (F) a private-beta decision, and (G) a separate public-beta decision. These milestone definitions are **proposed tracking records**, not native GitHub milestones or release promises.

Security Foundation A has passed reported CI and independent review at [draft PR #87](https://github.com/LegacyGuardHQ/legacyguard/pull/87), but is **not merged or complete** as of this dated update. The production scanner, Windows AMSI integration, isolated quarantine workers, monitoring and recovery controls remain future engineering work.

Each milestone should track actual issues, linked PRs, acceptance evidence, blockers and dated status. Funding receipt never substitutes for security review or completion evidence. Details of proposed quarterly financial disclosure are in [the funding report template](FUNDING_REPORT_TEMPLATE.md). Do not process real sensitive data or claim production readiness on the basis of these milestones.
