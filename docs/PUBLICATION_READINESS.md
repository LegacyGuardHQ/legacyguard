# Public Source Publication Readiness

This document records preparation guidance only. The repository remains
private. LegacyGuard is a temporary project name; no final commercial name has
been selected. Source publication would not approve a hosted application for
production or real sensitive data. Development and testing use synthetic data
only. The separate informational website is not the application and has no
account or document-storage integration.

## Security reporting

- Do not post vulnerability details, credentials, personal information,
  financial or estate information, uploaded documents, sensitive logs, or other
  confidential material in public issues, discussions, pull requests, or
  website forms.
- GitHub Private Vulnerability Reporting is preferred if the owner can enable
  and test it. The repository API returned 404 during the 2026-10-04 review;
  availability under the current plan is **unknown**, not confirmed available
  or unavailable. The owner must verify the feature in repository settings and
  test the route before relying on it.
- The existing fallback contact is recorded in `SECURITY.md` and the issue
  chooser. Repository text alone does not verify mailbox ownership, private
  access, delivery, or monitoring. The owner must verify those operational
  properties before public source publication. Do not invent or substitute a
  contact address.
- Ordinary bugs belong in the bug form with synthetic data and sanitized logs.
  Non-security questions may use Discussions. Neither public route is for
  confidential information.

## Contribution and provenance policy

Issues and Discussions may accept non-sensitive feedback. Unsolicited code
contributions and pull requests are not accepted. A pull request requires a
specific written request or authorization from the project owner. Opening an
issue or discussion does not transfer ownership or grant rights to incorporate
submitted material. No DCO or CLA has been selected.

The repository contains an AGPL-3.0 license. Before publication, the owner must
confirm authority and provenance for existing project code, assets, and other
copyrightable materials, and decide whether to keep this license. This document
does not determine ownership or make a legal claim.

## Recommended `master` protection

The settings below are recommendations only; this task does not change GitHub
settings. Recheck the exact available checks immediately before applying them.

- Require a pull request before merging.
- Require at least one approval from an independent reviewer. A sole owner
  cannot provide meaningful independent approval; arrange an eligible reviewer
  before relying on this rule.
- Dismiss stale approvals when new commits are pushed.
- Require all review conversations to be resolved (already enabled at review
  time).
- Require the branch to be up to date before merging (strict status checks are
  already enabled at review time).
- Require these existing passing checks: `Backend tests`, `Frontend tests and
  build`, `PostgreSQL migrations and tests`, `Backend release checks`,
  `Frontend release checks`, and `RC readiness gate`.
- Do not require `Analyze (python)` or `Analyze (javascript-typescript)` while
  `CODEQL_ENABLED=false`; do not require any check that is not producing a
  successful status on current pull requests.
- Enforce protections for administrators.
- Continue blocking force pushes and branch deletion (both were blocked at
  review time).

There is no `CODEOWNERS` file. In a single-owner repository it would not create
independent review and could route approval back to the same owner. Revisit
CODEOWNERS after a verified independent maintainer or team exists; do not invent
a GitHub username.

## Publication audit record

At the Stage 1 baseline review, the canonical repository was private and clean.
The known history remediation was complete; inspected current refs did not
reach the known sensitive documentation commits or contain their exact path
tokens. Tracked-file checks found no absolute personal filesystem paths,
private keys, common cloud/API tokens, local databases, uploaded documents,
logs, or private storage. These checks do not replace the required pinned
security gate or final owner review of every publication artifact.

The public informational website is a separate project. Its source and live
content must be reviewed separately; it currently has stale repository links
and must not be treated as evidence that the application or source repository
is public.

## Owner decisions before publication

1. Verify and test one private vulnerability intake route.
2. Resolve legal/provenance authority and the existing license decision.
3. Approve the contribution-intake policy above or publish replacement terms.
4. Review the pinned security gate and publication scan results.
5. Apply and verify the approved `master` protection settings.
6. Independently review and correct the separate informational website.
7. Make a separate, deliberate decision about repository visibility.