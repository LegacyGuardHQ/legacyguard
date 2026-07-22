# LegacyGuard Data Protection Architecture

## Purpose

LegacyGuard stores sensitive personal, financial, estate-planning, and continuity information. Before asset APIs are created, the backend needs a clear data protection model that separates searchable metadata from confidential values requiring encryption.

This document is a design review only. It does not introduce schema, endpoint, or authentication changes.

## Current Encryption Baseline

The backend currently includes `backend/app/services/encryption.py`, which provides a Fernet-based symmetric encryption service using `settings.encryption_key`.

Current implementation characteristics:

- Uses `cryptography.fernet.Fernet` for authenticated symmetric encryption.
- Encrypts and decrypts string values.
- Derives a Fernet-compatible key from `ENCRYPTION_KEY` by padding/truncating to 32 bytes and base64-url encoding it.
- Current encrypted model fields exist in `AssetDetail`:
  - `account_number_encrypted`
  - `policy_number_encrypted`
  - `notes_encrypted`

Current limitation: key derivation is simple and should be replaced before production with strong key generation and managed key storage.

## Data Classification

### Highly Sensitive Data: Encrypt at Field Level

The following data should be encrypted before persistence because it could expose financial accounts, private estate details, personal contact information, or recovery/security material.

#### Users

- Personal identifiers beyond the internal user ID.
- Future profile fields such as legal name, phone number, address, date of birth, tax identifiers, government identifiers, or emergency contact details.
- MFA recovery codes and security recovery material.

Email is sensitive personal data but usually needs login lookup and uniqueness checks. Recommended handling:

- Store a normalized email lookup value for authentication.
- Consider encrypting a display email copy if richer privacy requirements are introduced.
- For higher privacy, add a keyed email hash column for lookup and an encrypted email column for display.

#### Assets

- Account numbers.
- Policy numbers.
- Login references or credential vault references.
- Private notes.
- Detailed contact information associated with an asset.
- Any free-text description that may contain account-specific or personally identifying details.

Current encrypted fields already partially support this through `AssetDetail` encrypted columns.

#### Beneficiaries

- Contact details.
- Notes.
- Addresses, phone numbers, email addresses, dates of birth, tax identifiers, and relationship-specific sensitive details if added later.

Beneficiary name and relationship type may be searchable metadata, but names are still personal data and should be evaluated based on privacy requirements.

#### Documents

- Storage references, especially if they reveal bucket names, paths, object keys, or provider-specific URLs.
- Extracted document text.
- Document descriptions or notes.
- Any uploaded document content.
- Document metadata that reveals sensitive estate, financial, or legal context.

The current `documents.encrypted` flag is a good starting point but should be backed by a documented encryption workflow.

#### Reports and Tasks

- Report `content` should be encrypted because generated legacy reports may summarize sensitive assets, beneficiaries, and documents.
- Task descriptions may contain private planning details and should be encrypted if they can include sensitive free text.

### Searchable Metadata: May Remain Plaintext

Some fields can remain plaintext to support filtering, sorting, indexing, and ownership enforcement. These should be limited to non-secret classification data.

Examples:

- Internal IDs.
- `user_id` ownership fields.
- Foreign keys such as `asset_id`.
- Category/type fields such as:
  - `asset_category`
  - `document_type`
  - `report_type`
  - `task status`
  - `task priority`
- Timestamps:
  - `created_at`
  - `updated_at`
  - `last_login`
- Boolean flags:
  - `is_active`
  - `encrypted`
  - `mfa_enabled`
- Operational audit fields:
  - `created_by`
  - `modified_by`

Searchable fields must not contain secrets, account numbers, private notes, or document storage credentials.

## Encryption Boundaries

### Application-Level Field Encryption

Field-level encryption should happen in the application service/model boundary before data is committed to the database.

Recommended boundary:

1. API schema receives plaintext from an authenticated, authorized user.
2. Service layer validates ownership and input.
3. Sensitive fields are encrypted before ORM persistence.
4. Database stores ciphertext in `_encrypted` columns.
5. API response decrypts only when the current user is authorized to view the record.

Plaintext should not be logged, stored in audit details, or returned to unauthorized callers.

### Database Boundary

The database should be treated as a lower-trust storage layer. Sensitive values should already be encrypted before reaching the database.

Database-level encryption or encrypted disks are useful defense-in-depth, but they do not replace field-level encryption because database administrators, backups, or leaked database files could still expose plaintext.

### Search Boundary

Encrypted fields are not directly searchable. If search is needed over sensitive values, use one of the following patterns:

- Search only non-sensitive metadata.
- Store a keyed hash for exact-match lookup.
- Store carefully designed normalized search tokens only when necessary.
- Avoid partial search over sensitive values unless a dedicated privacy-preserving search design is created.

## Recommended Field-Level Encryption Approach

Use explicit encrypted columns for sensitive fields and keep searchable classification fields separate.

Recommended naming convention:

- `account_number_encrypted`
- `policy_number_encrypted`
- `notes_encrypted`
- `contact_information_encrypted`
- `storage_reference_encrypted`
- `content_encrypted`

Avoid ambiguous columns where plaintext and ciphertext could be mixed.

Recommended implementation approach:

1. Keep Pydantic request/response schemas separate from persistence models.
2. Accept plaintext only at API/service boundaries.
3. Encrypt before assigning ORM encrypted fields.
4. Decrypt only for authorized reads.
5. Never include decrypted values in logs, audit details, or exceptions.
6. Add tests verifying plaintext is not persisted.

## Key Management Approach

### Development

Development can use `ENCRYPTION_KEY` from `.env`, but it should be a generated high-entropy value, not a human-readable phrase.

### Production

Production should use managed key storage rather than hardcoded or repository-stored keys.

Recommended options:

- Cloud KMS, such as AWS KMS, Azure Key Vault, or Google Cloud KMS.
- Secrets manager for application key material.
- Envelope encryption:
  - A KMS-managed master key protects data encryption keys.
  - Application data is encrypted with data encryption keys.
  - Data encryption keys can be rotated without re-encrypting all key hierarchy material.

Recommended production requirements:

- `ENCRYPTION_KEY` must never be committed to source control.
- Key rotation procedure must be documented before production launch.
- Backups must include enough key metadata to support recovery, but not expose plaintext keys.
- Access to production encryption keys should be restricted and audited.

## Future Document Storage Encryption

Uploaded documents should be encrypted separately from database metadata.

Recommended document encryption model:

1. Generate a unique per-document data encryption key.
2. Encrypt the document content before writing to object storage or disk.
3. Store encrypted document bytes externally.
4. Store only encrypted storage references or opaque object IDs in the database.
5. Protect per-document keys using envelope encryption with a managed KMS key.
6. Verify document integrity using authenticated encryption or signed metadata.

Document metadata policy:

- Keep only minimal searchable metadata in plaintext, such as `document_type`.
- Encrypt storage references if they reveal provider paths or object keys.
- Do not expose raw storage URLs directly to clients unless using short-lived signed URLs and strict authorization checks.

## Backup and Recovery Considerations

Backups must be treated as sensitive because they contain ciphertext, searchable personal metadata, and potentially operational identifiers.

Recommendations:

- Encrypt database backups at rest.
- Encrypt object/document backups at rest.
- Store encryption keys separately from backups.
- Test restoration procedures regularly.
- Preserve key versions needed to decrypt historical backups.
- Define retention and deletion policies for user data.
- Ensure deleted user data is removed from active systems and handled appropriately in backups according to the retention policy.

## Implementation Priorities

### Priority 1: Stabilize Key Management

- Replace simple padding/truncation key derivation with explicit Fernet key generation or KMS-backed key loading.
- Validate key format at startup.
- Document production key generation and rotation.

### Priority 2: Encrypt Sensitive Existing Fields

- Continue using encrypted `AssetDetail` fields for account numbers, policy numbers, and notes.
- Add encrypted storage references for documents before document upload APIs are introduced.
- Encrypt beneficiary contact details and notes before beneficiary APIs are exposed.

### Priority 3: Protect Free-Text Fields

- Review all free-text fields because users may enter sensitive data unexpectedly.
- Encrypt report content and task descriptions if they include user-private planning information.

### Priority 4: Add Tests and Guardrails

- Add tests confirming sensitive plaintext is not stored in database rows.
- Add tests confirming unauthorized users cannot decrypt or retrieve another user’s data.
- Add logging tests or review to prevent accidental plaintext logging.

### Priority 5: Document Encryption Workflow

- Define object storage encryption before document APIs are created.
- Use per-document keys and envelope encryption.
- Use short-lived signed URLs only after authorization checks.

## Remaining Privacy Risks

- Email is currently stored plaintext for authentication lookup and uniqueness.
- Some free-text fields currently remain plaintext and may contain sensitive user-entered data.
- Current encryption key derivation is not production-grade.
- No key rotation strategy is implemented yet.
- Document content encryption workflow is not implemented yet.
- Backups and logs require operational policies to prevent accidental exposure.
- Search over encrypted values is not available without additional keyed-hash or tokenization design.
- Metadata such as categories, timestamps, ownership links, and document types can still reveal user behavior or sensitive context.
