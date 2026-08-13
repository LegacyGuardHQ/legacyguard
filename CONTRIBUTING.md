# Contributing to LegacyGuard

Thank you for helping build safer continuity tools for families. LegacyGuard
welcomes focused contributions from developers, security reviewers, designers,
documentation writers, accessibility specialists, and mission-aligned partners.

The source license and contribution terms have not yet been selected. Until
they are published, maintainers may discuss and review proposals but must not
merge outside code or other copyrightable contributions. Do not begin
substantial work without written confirmation that contribution intake is open.

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

When contribution intake opens, every contribution will be governed by the
published repository license and contribution terms. Public visibility alone
does not grant reuse rights.
