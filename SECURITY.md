# Security Policy

LegacyGuard handles software concepts involving sensitive personal and
financial information. Security and privacy issues are therefore treated
seriously.

## Supported Versions

LegacyGuard is alpha software. Security fixes are prioritized for the current
`master` branch and the latest alpha prerelease. Older tags are not supported
as production releases.

| Version | Supported |
| ------- | --------- |
| Current `master` and latest alpha prerelease | Yes |
| Older tags | Best effort |

## Reporting a Vulnerability

**Do not post vulnerability details, exploit steps, credentials, personal or
financial information, estate information, uploaded documents, sensitive logs,
or other confidential material in a public issue, discussion, pull request,
website form, or social-media post.** Do not ask for a private reporting
address in a public issue.

GitHub Private Vulnerability Reporting is the preferred route once the owner
enables and tests it. It is not currently confirmed enabled. When **Report a
vulnerability** is visible on the repository's **Security** tab, use that
private advisory flow.

The currently operational private reporting route is email to
**legacyguard.project@gmail.com**. The owner controls this mailbox, it receives
external email, and it is monitored for security reports.

Include, when safely available:

- the affected version or commit
- a concise impact statement
- prerequisites and safe reproduction steps using synthetic data
- relevant sanitized logs or screenshots
- a suggested remediation or mitigation, if known

Do not send real user records or credentials as evidence. There is no fixed
response-time guarantee. The maintainer will acknowledge and triage reports as
capacity permits and will coordinate remediation and disclosure through the
same private channel.

## Do Not Submit Sensitive Personal Information

Security reports must not contain real:

- passwords
- authentication tokens
- encryption keys
- Social Security numbers
- financial account numbers
- medical information
- private estate documents
- personal documents
- credentials belonging to another person

Use synthetic or appropriately redacted test data whenever possible.

## Bugs and Support

Use the public bug-report issue form only for ordinary, reproducible problems
with synthetic data and sanitized evidence. Use repository Discussions for
non-security questions when available. Do not use either channel for private
support or sensitive information; see [SUPPORT.md](SUPPORT.md).

## Responsible Disclosure

Please allow reasonable time for investigation and remediation before public
disclosure. Do not test against systems or data you do not own or have explicit
authorization to assess.

Thank you for helping improve LegacyGuard's security.
