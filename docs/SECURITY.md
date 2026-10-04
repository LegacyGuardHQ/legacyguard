# LegacyGuard Security Design

## Status

LegacyGuard is a temporary project name for pre-production software. Use
synthetic data only. Implemented controls are not a claim that the application
is production-safe, independently audited, compliant, or free of risk.

## Reporting a vulnerability

Do not post vulnerability details, credentials, personal or financial
information, estate information, uploaded documents, sensitive logs, or other
confidential material in public issues, discussions, pull requests, or website
forms.

GitHub Private Vulnerability Reporting is enabled for this repository and is the
preferred private reporting method. The owner-controlled, monitored mailbox
documented in the root [security policy](../SECURITY.md) remains an alternate,
fallback private route.

Include the affected version or commit, a concise impact statement,
prerequisites, safe reproduction steps using synthetic data, sanitized logs or
screenshots, and a possible remediation when known. There is no fixed response
SLA; the maintainer will acknowledge and triage reports as capacity permits.

## Authentication and sessions

LegacyGuard uses short-lived HS256 JWT access tokens paired with server-side
session records. Each login creates a unique token identifier (`jti`) shared by
the access token and its revocable database session. Protected routes accept
access tokens only and reject missing, malformed, expired, or revoked sessions
with generic errors.

The access-token lifetime is controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` and
defaults to 15 minutes in development. The browser stores the access token in
`sessionStorage`. Refresh tokens, refresh rotation, and a refresh endpoint are
not implemented; users must sign in again after expiration. MFA remains future
work.

Registration attempts and failed logins use hashed database-backed client keys.
The key currently derives from the request peer address, so trusted-proxy
configuration, distributed edge controls, and abuse monitoring remain
production requirements.

## Encryption and persistence

`ENCRYPTION_KEY` must be a valid Fernet key. Outside testing, startup rejects a
missing key, the known development default, or invalid key material. The
application does not pad or truncate arbitrary values into a key.

Designated asset, beneficiary, and document fields are encrypted before
persistence. Uploaded document content uses a generated per-document Fernet
data key; the encrypted key reference is protected by the application
encryption service. Production must obtain key material from an approved secret
manager or KMS-backed process. Rotation, recovery, and historical-backup key
retention remain unresolved operational requirements.

## Documents

Uploads are owner-scoped, bounded to 20 MiB, validated for filename, extension,
declared MIME type, and selected magic bytes, then encrypted before storage.
Production requires PostgreSQL, S3-compatible object storage, and a configured
malware scanner. Without a scanner, production uploads fail with HTTP 503.

Filename/MIME validation is not malware detection. A real scanner, quarantine
workflow, timeout/failure behavior, monitoring, coordinated backup/restore,
and retention policy remain required before real documents can be accepted.

## CORS

Browser access uses an explicit environment-configured origin allowlist.
Production rejects wildcard or empty origin configuration. Credentialed
responses are returned only to an exact allowed origin. For an allowed origin,
preflight responses reflect the browser's requested headers; the origin
allowlist, not a separate header allowlist, is the controlling browser boundary.

## Authorization and privacy invariants

- Owner-controlled reads and writes must include authenticated `user_id`
  scoping at the query boundary.
- Generic not-found and authentication responses must prevent account and
  cross-owner record enumeration.
- Decrypted content, storage locators, keys, tokens, credentials, and private
  free text must not appear in logs or unnecessary responses.
- Discovery confidence is signal strength, not proof of ownership, identity,
  value, or legal validity.
- Findings require human confirmation and must never create assets
  automatically.

## Known limitations

- no MFA
- no refresh-token workflow
- no real malware scanner or quarantine integration
- request-peer IP handling is not a complete trusted-proxy/edge rate limit
- no managed key rotation or recovery procedure
- no proven coordinated production backup/restore or retention process
- in-process Discovery work is not a durable isolated worker system
- no public production service is approved for real sensitive data
- no final commercial product name has been selected
