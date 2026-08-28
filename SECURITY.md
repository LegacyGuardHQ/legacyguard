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

Do not report a suspected vulnerability through a public GitHub issue,
discussion, pull request, website form, or social-media post. Do not include
vulnerability details in a public request for contact.

Send private reports to **legacyguard.project@gmail.com**, the project's
dedicated security and operations mailbox (not a personal address). This email
is the fallback route whenever GitHub private reporting is unavailable.

Immediately after the repository becomes public, the owner will enable and
test GitHub private vulnerability reporting. When enabled, use **Report a
vulnerability** on the repository's **Security** tab. If that interface is
unavailable, use the verified fallback route documented in this policy; do not
open a public issue.

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

## Responsible Disclosure

Please allow reasonable time for investigation and remediation before public
disclosure. Do not test against systems or data you do not own or have explicit
authorization to assess.

Thank you for helping improve LegacyGuard's security.
