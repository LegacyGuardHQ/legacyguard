# Public Website Copy and Activation Gate

The informational website is hosted separately from this repository and the
application. It has no application account or document-storage integration.
This file is review guidance only; changing it does not deploy or modify that
website. LegacyGuard is temporary project branding; no final commercial name
has been selected.

Do not deploy the copy below until:

- the owner has explicitly approved repository publication and verified that
   `LegacyGuardHQ/legacyguard` is public and anonymously reachable
- repository history/privacy and legal/provenance owner decisions are complete
- the root security policy's fallback route has been verified operationally
- GitHub private vulnerability reporting is enabled and tested, if available

## Required link replacements

Use the current canonical repository owner, `LegacyGuardHQ`, for repository,
issue, release, and security-policy links. Do not publish links to an obsolete
owner or claim that source or releases are public before anonymous verification:

```text
https://github.com/LegacyGuardHQ/legacyguard
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
Current prerelease and CI claims must be checked against the exact public
release and commit. Do not state that CodeQL runs while `CODEQL_ENABLED=false`.
```

Do not publish a hard-coded test count unless it is generated from the exact
linked commit and updated automatically.

## Inspectable development

```text
The source, tests, release history, security design, and operating limitations
may be described as public only after anonymous verification. Source publication
and passing checks do not mean a hosted product is production-ready or approved
for real data.
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
repository security policy, which prefers GitHub private vulnerability
reporting and lists a private fallback mailbox. Never send real user data,
credentials, or private documents as evidence.
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
