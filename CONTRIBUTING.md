# Contributing to LegacyGuard

Thank you for helping build safer continuity tools for families. LegacyGuard
welcomes focused contributions from developers, security reviewers, designers,
documentation writers, accessibility specialists, and mission-aligned partners.

LegacyGuard is licensed under the GNU Affero General Public License v3.0
(AGPL-3.0) — see [LICENSE](LICENSE). Small, clearly scoped proposals are
welcome through the guided issue process. Contribution ownership terms have
not yet been published, so maintainers must not merge outside code or other
copyrightable contributions until the owner selects and documents an intake
policy. Do not begin substantial work without written confirmation that
contribution intake is open.

## Before you begin

- Never include real personal, financial, medical, estate, document, or
  credential data in issues, screenshots, logs, fixtures, or pull requests.
- Use synthetic test data only.
- Do not report exploitable security vulnerabilities in a public issue. Follow
  the private reporting guidance in [docs/SECURITY.md](docs/SECURITY.md).
- Keep each change focused and explain any privacy or authorization impact.

## Ways to contribute

- Fix a documented bug or improve test coverage.
- Propose an accessibility, usability, or documentation improvement.
- Review authentication, authorization, encryption, audit, or data-minimization
  behavior.
- Improve deployment safety and operational documentation.
- Suggest a partnership, pilot, or funding opportunity that respects the
  project's privacy-first mission.

## Contribution workflow

1. Search existing issues and pull requests before opening a new one.
2. Use the closest guided issue form and keep sensitive details out of it.
3. Agree on scope before beginning a large change.
4. Create a focused branch and include tests or documentation where relevant.
5. Complete the pull-request template, including privacy and validation notes.
6. Wait for review; a contribution is not accepted until it is merged.

## Development checks

Backend:

```powershell
Set-Location backend
python -m pytest
```

Frontend:

```powershell
Set-Location frontend
npm test -- --run
npm run build
```

Also run `git diff --check` before submitting. More focused checks are welcome
for documentation-only changes, but state exactly what you validated.

## Contribution standards

- Preserve owner scoping and least-privilege access.
- Keep findings and imported information subject to human review.
- Do not weaken encryption, authentication, authorization, auditing, or safe
  error handling for convenience.
- Avoid new dependencies unless their need, maintenance, license, and security
  impact are explained.
- Write plain-language documentation for behavior users must understand.

The owner must decide whether contribution intake will use a DCO, CLA, or
another documented approach before accepting outside copyrightable work. Once
intake opens, accepted contributions will be governed by the repository's
AGPL-3.0 license and the published contribution terms. Public visibility alone
does not grant reuse rights beyond the license.
