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

The repository's GitHub Sponsors profile is active. The informational website
is separate from the application; this guidance does not publish or update it.
Use the official profile link below if the owner approves updating the website.
Keep the alpha and synthetic-data warnings visible alongside any funding appeal.

```text
Support responsible development through GitHub Sponsors:
https://github.com/sponsors/jh505tt-create

Sponsorship supports security and privacy review, accessibility, documentation,
and safe demonstration prerequisites. LegacyGuard is alpha software, is not a
public production service, and is not approved for real sensitive data. Use
synthetic data only. Sponsorship does not provide access to private data,
security exceptions, preferential vulnerability handling, or roadmap control.
Sponsorships are not represented as tax-deductible.

See the repository's funding guidance for the provisional goal and public
aggregate-use reporting approach. Current monthly and one-time sponsorship
options, if any, are shown on the linked GitHub Sponsors profile.
```

Do not imply users, partners, adoption, an independent audit, compliance,
production safety, tax deductibility, or guaranteed timelines without current
evidence.
