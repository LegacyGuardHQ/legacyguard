# LegacyGuard Data Protection Architecture

## Purpose and maturity

LegacyGuard models personal, financial, estate-planning, and continuity
information. This document describes the current alpha implementation and its
remaining limits. Use synthetic data only; the project is not approved for a
real-data production service.

## Data classification

### Encrypted application data

The current backend encrypts designated sensitive values before persistence,
including:

- asset account numbers, policy numbers, and private notes
- beneficiary contact information and notes
- document descriptions and storage references
- per-document encryption-key references
- uploaded document content

Uploaded content is encrypted with a generated per-document Fernet data key.
The data key is included in a document-bound key reference protected by the
application encryption service. Only encrypted bytes are sent to the configured
document-storage backend.

### Plaintext/searchable metadata

Some operational and classification fields remain plaintext to support
authentication, ownership checks, filtering, ordering, and lifecycle state.
Examples include:

- internal identifiers and owner foreign keys
- normalized login email
- asset names/categories and selected high-level descriptions
- beneficiary names and relationship types
- document names/types, timestamps, status, and verification state
- audit event categories and privacy-safe identifiers

Plaintext metadata can still reveal sensitive context. It must be minimized,
owner-scoped, excluded from unnecessary logs, and covered by retention and
access-control policy. Free-text fields require particular care because users
may enter information more sensitive than the field name suggests.

## Encryption boundary

`backend/app/services/encryption.py` accepts only a valid Fernet key. The
application fails startup outside testing when the encryption key is missing,
uses the development default, or is invalid. It does not pad, truncate, or
derive a replacement from arbitrary text.

The expected boundary is:

1. An authenticated route validates input and ownership.
2. Sensitive plaintext is encrypted before ORM persistence.
3. The database stores ciphertext in explicitly named encrypted columns.
4. Decryption occurs only after authorization for an allowed response or
   internal processing operation.
5. Plaintext is excluded from audit details, operational logs, object locators,
   and error messages.

Encrypted fields are not used for partial search. A future exact-match need
would require a separately reviewed keyed-hash/token design.

## Document upload boundary

The document-upload route:

1. verifies authentication, ownership, lifecycle state, and related-record
   ownership
2. reads at most 20 MiB
3. validates filename structure, extension, declared MIME type, and selected
   magic bytes
4. requires a configured malware scanner in production
5. encrypts content before the storage write
6. stores an opaque, encrypted locator and ciphertext integrity metadata
7. avoids persisting a new global plaintext content fingerprint

If no malware scanner is configured, production uploads fail with HTTP 503.
Development and isolated tests may omit the scanner, but that behavior must not
be used as a production configuration.

Filename, MIME, and magic-byte checks are not malware detection. A real scanner
must define timeout, failure, quarantine, audit, update, and operator-response
behavior before uploads can be approved for real data.

## Storage boundary

SQLite and local document storage are development/test facilities. When
`ENVIRONMENT=production`, configuration requires PostgreSQL/Psycopg and
S3-compatible object storage. Object endpoint URLs must be HTTPS outside
development/testing and must not embed credentials, query strings, or
fragments.

Provider-side encryption and versioning are defense in depth; they do not
replace application encryption, owner authorization, lifecycle deletion,
backup coordination, or key recovery.

## Key management

Development may load a generated Fernet key from an ignored `.env` file.
Production must load key material from an approved secret manager or KMS-backed
process and must restrict and audit access.

The current document design records a non-secret master-key identifier, but a
complete managed key hierarchy, rotation procedure, recovery ceremony, and
historical-backup key-retention policy are not implemented. Losing the active
key can make encrypted database values and document key references
unrecoverable.

## Backup, retention, and deletion

Database and object-storage backups contain ciphertext plus potentially
sensitive metadata. Before real-data operation, the owner must define and test:

- coordinated point-in-time database/object restore
- encryption-key availability during restore
- backup encryption and access controls
- object-version and delete-marker handling
- retention, deletion, legal-hold, and backup-expiry policy
- recovery testing without real user records

The isolated recovery and smoke scripts use temporary synthetic SQLite/local
storage. They do not prove a production PostgreSQL/object-storage recovery.

## Remaining privacy and production requirements

- email and some high-level metadata remain plaintext
- some free-text fields may contain unexpectedly sensitive information
- no real malware scanner or quarantine workflow is integrated
- no managed key rotation/recovery process is implemented
- coordinated backup/restore and deletion are unproven
- trusted ingress, proxy handling, distributed rate limiting, and operational
  monitoring remain deployment responsibilities
- a durable isolated Discovery worker is not implemented
- independent security, privacy, accessibility, and legal review remain
  outstanding

These limitations must remain visible in public documentation and release
messaging. They are not waived by open-source publication.
