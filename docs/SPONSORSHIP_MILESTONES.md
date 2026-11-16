# LegacyGuard sponsorship and engineering milestones

**Planning snapshot: November 16, 2026.** This is the proposed tracking structure for GitHub Milestones; publishing this document does **not** create native GitHub milestone objects. No dates or funding amounts are promised.

LegacyGuard is internal-alpha software, with synthetic-data-only use authorized. The application is not approved for personal or sensitive real-world information. Source publication and funding do not change those limits.

## Proposed milestones and completion gates

| ID | Milestone | Status | Required completion evidence |
|---|---|---|---|
| A | Persisted malware verdict and fail-closed document access | Security review passed; [PR #87](https://github.com/LegacyGuardHQ/legacyguard/pull/87) remains draft and unmerged as of this snapshot | Owner-approved merge, post-merge required CI, PostgreSQL migration tests, and review of content-access boundaries |
| B | Trusted scanner integration and quarantine | Planned | Trusted scanner, supported platforms, quarantined storage, worker isolation, failure/timeout/retry tests, and release/delete runbook |
| C | Protected infrastructure and recovery | Planned | Managed data/key services, secure ingress, backup/restore and key-recovery exercises, retention/deletion and monitoring evidence |
| D | Independent security, privacy, and legal review | Planned | Independent reports, prioritized findings, remediation and retest evidence; appropriate legal/privacy guidance |
| E | Accessibility and controlled synthetic evaluation | Planned | Keyboard, screen-reader, zoom, contrast and plain-language testing; synthetic-only participant protocols |
| F | Controlled private-beta decision | Blocked | Separate owner go/no-go after prerequisite security, privacy, hosting, recovery, accessibility and support gates |
| G | Public-beta/general-availability decision | Not scheduled | Separate owner go/no-go with operational, capacity, security, privacy, reliability and support evidence |

## Implementation issue suggestions

**A:** Complete independent PR review; verify no bypass of `CLEAN`; validate database migrations and CI; document migration rollback and post-merge findings.

**B:** Decide scanner engines and licensing; develop Windows AMSI and cross-platform adapters; add trusted verdict provenance, isolated scanning workers, encrypted quarantine, retries, malware-safe synthetic tests and operational response procedures.

**C:** Choose managed infrastructure; implement key lifecycle; test encrypted backup/restore and recovery; implement retention/deletion, security monitoring, trusted ingress and incident runbooks.

**D:** Prepare threat model and independent assessment scope; obtain appropriate privacy/legal guidance; track findings, remediation, retesting and residual risks.

**E:** Test assistive technology, cognitive accessibility, error recovery and plain-language flows with strictly synthetic inputs.

**F and G:** Define and record release decision evidence. Neither milestone is a scheduled launch promise.

## Governance rules

- One coherent objective, owner, dependencies and acceptance gate per milestone.
- Record GitHub issue/PR links and evidence for each completion claim.
- Do not mark an in-review PR as a completed milestone.
- Do not invent delivery dates, completion percentages, budgets or donations.
- Sponsor funding does not purchase access, preferential vulnerability handling, hidden roadmap control or exceptions to security gates.
- Revise public status when verified facts materially change, retaining dated history.
- Use [the funding policy](../FUNDING.md) and [reporting template](FUNDING_REPORT_TEMPLATE.md) for public financial accountability.
