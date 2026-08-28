# Public Website Copy and Activation Gate

The existing website is hosted outside this repository. This file is the
reviewable source for its next public update; changing this file does not deploy
the website.

Do not deploy the copy below until:

- `LegacyGuard/legacyguard` is public and anonymously reachable
- the repository history/privacy and legal owner decisions are complete
- the root security policy contains a tested private fallback route
- GitHub private vulnerability reporting is enabled and tested

## Required link replacements

Replace every repository, issue, and release URL under
`github.com/jh505tt-create/legacyguard` with its canonical equivalent under:

```text
https://github.com/LegacyGuard/legacyguard
```

Use the repository root for the primary source link, `/issues` for public
non-security feedback, `/security/policy` for security instructions, and the
actual current prerelease URL only after anonymous verification.

## Hero

Eyebrow:

```text
Alpha open-source continuity project
```

Headline:

```text
Continuity, with care.
```

Body:

```text
LegacyGuard is a privacy-first alpha project for organizing assets,
beneficiaries, important documents, and discovery results for human review.
Use synthetic data only. No public production service is available or approved
for real personal, financial, medical, estate, credential, or document data.
```

Primary action:

```text
View the canonical repository
```

Secondary action:

```text
Read the alpha roadmap
```

## Status strip

Replace release and test-count claims with:

```text
Current prerelease: v1.1.0-rc.1 · Alpha · Automated backend, frontend,
PostgreSQL, and CodeQL checks run in GitHub Actions
```

Do not publish a hard-coded test count unless it is generated from the exact
linked commit and updated automatically.

## Inspectable development

```text
The source, tests, release history, security design, and operating limitations
are public for review. Passing checks and implemented encryption are evidence of
development quality, not a claim of production readiness or zero risk.
```

## Roadmap

Replace “Stable open-source release” and “production-readiness validation” with:

```text
1. Alpha source release
   Publish reviewed source, history, documentation, and security-reporting
   paths without representing the application as production-ready.

2. Safe synthetic demonstration
   Provide an informational or synthetic-data experience with no real accounts,
   documents, or personal information.

3. Fund production prerequisites
   Support independent review, protected hosting, malware quarantine,
   backup/recovery, managed keys, accessibility, and operational monitoring.

4. Consider a controlled pilot
   Proceed only after documented security, privacy, legal, operational, and
   user-safety gates are satisfied.
```

## Security reporting

```text
Do not report a vulnerability in a public issue or website form. Follow the
repository security policy and use GitHub private vulnerability reporting. If
that interface is unavailable, use the verified fallback listed in the policy.
Never send real user data, credentials, or private documents as evidence.
```

## Funding

Replace the GitHub Sponsors approval claim with:

```text
No verified public funding channel is active. Do not send money or payment
details through issues, pull requests, discussions, or unsolicited messages.
If funding opens later, the repository and this site will link only to a
verified official destination and will publish how funds are intended to be
used. Sponsorship will not buy access to user data, security exceptions, or
roadmap control.
```

Do not imply tax deductibility, Sponsors approval, users, partners, adoption,
independent audit, compliance, production safety, or guaranteed timelines
without current evidence.
