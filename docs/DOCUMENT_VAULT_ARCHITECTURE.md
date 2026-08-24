# Document Vault Architecture

## Purpose

This document designs a secure document-management system for LegacyGuard that allows authenticated users to associate supporting records with assets, beneficiaries, and their overall legacy plan.

This phase is architecture only. It does **not** create document upload/download endpoints, modify document models, create frontend changes, or implement cloud storage.

## 1. Current Model Review

### Current `Document` model

Current file: `backend/app/models/document.py`

Existing fields:

| Field | Current behavior | Review |
|---|---|---|
| `id` | Primary key string, indexed | Safe as internal identifier. Should be opaque UUID/ULID generated server-side. |
| `user_id` | FK to `users.id`, indexed, required, `ondelete="CASCADE"` | Required ownership anchor. Every document must belong to exactly one user. |
| `asset_id` | Optional FK to `assets.id`, indexed, `ondelete="SET NULL"` | Supports asset-linked documents. Ownership must be verified through both `Document.user_id` and `Asset.user_id`. |
| `document_type` | Required string, indexed | Should become controlled stable internal value before API exposure. Current legacy schema uses display labels. |
| `document_name` | Required string, indexed | User-facing label; may reveal sensitive content. Can remain searchable only with caution. Stronger privacy would use encrypted display name plus search token. |
| `storage_reference` | Nullable plaintext text | Unsafe before API exposure. Replace with `storage_reference_encrypted`; never return in list/detail responses. |
| `encrypted` | Boolean flag | Useful operational flag but insufficient alone. Prefer explicit encryption metadata: `content_encryption_algorithm`, `encryption_key_reference`, `storage_reference_encrypted`. |
| `created_at` / `updated_at` | Timestamp audit fields | Safe operational metadata. |
| `created_by` / `modified_by` | Actor audit fields | Safe internal metadata; should be populated on future mutations. |

Relationships:

- `Document.user` uses `User.documents` with cascade delete-orphan.
- `Document.asset` uses `Asset.documents` with cascade delete-orphan on the asset side.
- There is currently no `beneficiary_id` relationship, but the vault should support optional beneficiary-linked documents in the future.
- There is currently no direct overall-plan object, so user-level documents should use `user_id` with both `asset_id` and `beneficiary_id` null.

Document Model Preparation decision: documents may link to neither an asset nor a beneficiary, to an asset only, to a beneficiary only, or to both an asset and a beneficiary. In all cases the document remains directly owned by one `user_id`, and future APIs must verify every linked record belongs to that same user.

### Current encryption field map

Current file: `docs/ENCRYPTION_FIELD_MAP.md`

The existing encryption field map already classifies `Document.storage_reference` as **highly sensitive** and recommends replacement with `storage_reference_encrypted` before document APIs.

### Current encryption service

Current file: `backend/app/services/encryption.py`

- Uses Fernet authenticated encryption through `cryptography.fernet.Fernet`.
- Provides string `encrypt()` and `decrypt()` helpers.
- Validates `ENCRYPTION_KEY` on startup.
- Current service is appropriate for encrypting small metadata values such as storage references.
- It is not sufficient by itself as a final large-file content encryption design because document bytes should use streaming/chunk-aware authenticated encryption or envelope encryption with per-document data keys.

### Plaintext or unsafe fields to replace before API exposure

High priority before document APIs:

1. Replace `Document.storage_reference` with `storage_reference_encrypted`.
2. Do not expose storage references in any response.
3. Do not store direct local paths, bucket names, object URLs, or signed URLs in plaintext.
4. Avoid accepting document content, extracted text, or OCR text into plaintext columns.
5. Add `beneficiary_id` only after designing ownership checks and lifecycle behavior.
6. Replace legacy display document types with stable internal controlled values.

## 2. Controlled Document Types

Use stable uppercase internal values suitable for APIs, filtering, and future reporting:

```text
WILL
TRUST
LIFE_INSURANCE_POLICY
BENEFICIARY_FORM
ACCOUNT_STATEMENT
RETIREMENT_DOCUMENT
DEED
VEHICLE_TITLE
TAX_DOCUMENT
IDENTIFICATION
POWER_OF_ATTORNEY
HEALTHCARE_DIRECTIVE
EMPLOYER_BENEFIT_DOCUMENT
GOVERNMENT_BENEFIT_DOCUMENT
DIGITAL_ASSET_INSTRUCTIONS
OTHER
```

Recommended semantics:

- Store internal values exactly as above.
- Render user-facing labels in the frontend/API presentation layer later.
- Reject unknown values with `422` in future APIs.
- Keep `OTHER` available but require a safe optional description or subtype only if encrypted or carefully validated.

## 3. Recommended Document Metadata Design

Recommended future schema fields:

| Field | Required | Searchable? | Encryption recommendation | Notes |
|---|---:|---|---|---|
| `id` | Yes | Yes | Plaintext internal | Opaque UUID/ULID. |
| `user_id` | Yes | Yes | Plaintext internal | Required ownership boundary. |
| `asset_id` | No | Yes | Plaintext internal | Must belong to same user if present. |
| `beneficiary_id` | No | Yes | Plaintext internal | Future FK; must belong to same user if present. |
| `document_type` | Yes | Yes | Plaintext controlled | Sensitive but useful for filtering/reporting. |
| `document_name` | Yes | Maybe | Prefer encrypted display plus optional search token | Current plaintext is sensitive. If search is required, consider `document_name_search_hash`. |
| `description` | No | No | Encrypted | Free text may contain legal, financial, or identity details. |
| `original_filename` | Yes for uploads | Maybe | Prefer encrypted or sanitized plaintext basename | Original filenames often contain names/account info. Avoid logging. |
| `mime_type` | Yes | Yes | Plaintext controlled | Needed for validation and safe response headers. |
| `file_size` | Yes | Yes | Plaintext | Operational metadata. |
| `checksum_hash` | Yes | Yes | Plaintext hash | SHA-256 of encrypted or plaintext bytes depending purpose; see integrity notes below. |
| `storage_reference_encrypted` | Yes after upload | No | Encrypted | Replaces unsafe `storage_reference`. Never returned. |
| `encryption_key_reference` | Later | No | Plaintext opaque KMS key ID or encrypted reference | Do not expose externally. Needed for envelope encryption/key rotation. |
| `content_encryption_algorithm` | Yes after upload | Yes | Plaintext internal | Example: `AES-256-GCM`, `FERNET`, `KMS_ENVELOPE_AES_256_GCM`. |
| `expiration_date` | No | Yes | Plaintext date | Useful lifecycle filter; sensitive but operational. |
| `effective_date` | No | Yes | Plaintext date | Useful for legal docs/policies. |
| `verification_status` | Yes | Yes | Plaintext controlled | `UNKNOWN`, `VERIFIED`, `NEEDS_REVIEW`, `EXPIRED`, `REPLACED`. |
| `verified_at` | No | Yes | Plaintext timestamp | Set on verification. |
| `review_due_at` | No | Yes | Plaintext timestamp | Used for reminders. |
| `status` | Yes | Yes | Plaintext controlled | `ACTIVE`, `ARCHIVED`, `REPLACED`, `DELETED_PENDING_PURGE`. |
| `archived_at` | No | Yes | Plaintext timestamp | Exclude archived by default. |
| `version_group_id` | No | Yes | Plaintext internal | Groups replacements. |
| `supersedes_document_id` | No | Yes | Plaintext internal | Version history link. |
| `created_at` / `updated_at` | Yes | Yes | Plaintext timestamp | Operational audit. |
| `created_by` / `modified_by` | Yes | Yes | Plaintext internal | Audit actor IDs. |

### Integrity checksum recommendation

Use two hashes if needed:

- `plaintext_sha256_encrypted`: encrypted checksum of original plaintext bytes, used to verify decrypted content without exposing a fingerprint of a sensitive document.
- `ciphertext_sha256`: plaintext hash of encrypted bytes, used to detect storage corruption without decryption.

For initial implementation, `ciphertext_sha256` is safer to expose internally. Do not expose checksums publicly unless there is a product need.

## 4. File Storage Architecture

### Development storage

Recommended development strategy:

- Store encrypted files on local disk under a private directory outside public/static paths, for example `backend/private_storage/documents/`.
- Use opaque generated filenames based on document IDs and random suffixes, never original filenames.
- Store only encrypted bytes.
- Store local path/object key only in `storage_reference_encrypted`.
- Disable direct browser access to the storage directory.
- Serve downloads only through future authenticated API handlers that verify ownership, decrypt, and stream safely.
- Ensure private storage is excluded from source control and backups unless encrypted backup policy exists.

### Production storage

Recommended production strategy:

- Use private encrypted object storage such as S3, Azure Blob Storage, or GCS.
- Use private buckets/containers only; no public ACLs and no public URLs.
- Store object keys as opaque random values.
- Use short-lived signed URLs only after authorization, or preferably stream through the API when policy requires server-side logging/decryption.
- Use envelope encryption with cloud KMS or managed key service.
- Store KMS key references and encrypted data-key references separately from user-facing metadata.
- Enable bucket access logs, versioning, retention policies, and malware scanning integration.

No storage implementation should be added in this architecture phase.

## 5. File Encryption Design

### Upload/encryption workflow

Future upload flow:

1. Authenticate user with existing auth dependency.
2. Verify `asset_id`, if supplied, belongs to current user.
3. Verify `beneficiary_id`, if supplied, belongs to current user.
4. Validate document type, file type, extension, size, and filename.
5. Generate opaque document ID and opaque storage object key.
6. Generate a per-document data encryption key.
7. Encrypt document content before persistence.
8. Store encrypted bytes in local private storage or private object storage.
9. Store encrypted storage reference in `storage_reference_encrypted`.
10. Store integrity checksum metadata.
11. Persist document metadata and audit fields.
12. Return metadata only, never storage references or decrypted content.

### Authenticated encryption approach

- Use authenticated encryption so tampering is detected before decrypted bytes are trusted.
- Recommended content encryption: AES-256-GCM or XChaCha20-Poly1305 with random nonce per file/chunk.
- For large files, use chunked authenticated encryption with per-chunk nonces and a manifest protected by authentication data.
- Bind additional authenticated data (AAD) to document metadata such as `document_id`, `user_id`, and encryption version.

### Per-document keys

- Generate a unique data encryption key for every document.
- Never reuse nonce/key pairs.
- Store encrypted data keys, not raw data keys.
- Separate content encryption keys from application metadata encryption keys.

### Development fallback

- Development can use locally managed app encryption for both metadata references and file bytes.
- Fernet can be acceptable for small prototype files, but the production design should not depend on loading large files fully into memory.
- Even in development, files must be encrypted at rest and stored outside public directories.

### Production KMS/envelope path

- Request a data key from KMS.
- Encrypt content locally with the plaintext data key.
- Immediately discard plaintext data key from memory after use.
- Store KMS-encrypted data key reference/bytes in metadata.
- Store object in private encrypted bucket/container.
- On download, authorize user, retrieve encrypted data key, decrypt via KMS, stream-decrypt content, and return with safe headers.

### Key rotation considerations

- Track encryption algorithm and key version/reference per document.
- Rotate metadata encryption keys by decrypting/re-encrypting `storage_reference_encrypted`.
- Rotate content keys by either rewrapping encrypted data keys or re-encrypting content, depending on KMS capabilities and threat model.
- Keep old keys available for decrypting existing documents until migration completes.
- Add tests proving old documents remain readable during rotation.

## 6. Access Control Rules

Strict future rules:

- Every document belongs to exactly one `user_id`.
- Every document operation requires authentication.
- If `asset_id` is provided, the asset must belong to the same current user.
- If `beneficiary_id` is provided, the beneficiary must belong to the same current user.
- Cross-user document, asset, or beneficiary references return `404` to avoid enumeration.
- Document lookup should filter by both `Document.id` and `Document.user_id`.
- List/detail responses must never expose storage references, signed URLs, encrypted storage references, data keys, or ciphertext.
- Download/decrypt is allowed only after ownership checks pass.
- Archived documents are excluded from default list responses.
- Sensitive metadata such as filenames, descriptions, storage paths, and checksums should not be logged.
- Audit events should record document ID, user ID, action, timestamp, and non-sensitive status, but not filenames or descriptions unless policy allows.

## 7. File Validation Rules

### Size limits

Conservative initial limit:

- Maximum file size: `20 MB` per document.
- Consider smaller limits for images and text files.
- Reject empty files unless a metadata-only record is explicitly supported later.

### MIME type allowlist

Initial conservative allowlist:

```text
application/pdf
image/jpeg
image/png
text/plain
application/vnd.openxmlformats-officedocument.wordprocessingml.document
application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
```

Consider adding only after security review:

```text
image/tiff
application/msword
application/vnd.ms-excel
```

Avoid initially:

- Executables
- Scripts
- HTML/SVG with active content risk
- Archives such as `.zip`, `.rar`, `.7z`
- Password-protected files unless a scanning workflow can handle them

### Extension allowlist

Initial extensions:

```text
.pdf
.jpg
.jpeg
.png
.txt
.docx
.xlsx
```

### Filename normalization

- Normalize Unicode.
- Strip path separators and control characters.
- Store original filename encrypted or sanitized.
- Use generated opaque storage filenames only.
- Enforce a maximum filename length.
- Never trust client-supplied paths.

### Double-extension attacks

- Reject suspicious filenames such as `will.pdf.exe`.
- Validate both extension and detected content/MIME.
- Do not infer safety from extension alone.

### Content-type mismatch

- Compare client MIME type with server-side sniffed content type.
- Reject mismatches unless explicitly allowed by a safe mapping.
- Store the server-verified MIME type.

### Malware scanning hook

- Add a scanning stage before final active status.
- Initial statuses may include `PENDING_SCAN`, `ACTIVE`, `QUARANTINED`, `REJECTED`.
- Do not allow download until scan passes, unless an admin-only quarantine workflow exists.

### Checksum validation

- Calculate checksum server-side after receiving bytes.
- Verify stored encrypted bytes against checksum before download/decryption.
- Optionally compare client-provided checksum only as an additional integrity check, not as a trust source.

### Duplicate-file handling

- Detect duplicates per user using encrypted or internal checksum strategy.
- Recommended behavior: allow duplicates but warn/flag possible duplicate in metadata.
- Avoid global duplicate detection that could leak whether another user has the same document.

## 8. Lifecycle Design

### Upload

- Creates metadata and encrypted content.
- Validates ownership of linked asset/beneficiary.
- Sets `status` to `PENDING_SCAN` or `ACTIVE` depending on scanning availability.
- Sets `verification_status` to `UNKNOWN` or `NEEDS_REVIEW`.
- Returns metadata only.

### Metadata update

- Allows safe fields such as `document_type`, dates, review metadata, and encrypted description/name updates.
- Does not change file bytes.
- Updates `modified_by` and `updated_at`.
- Revalidates linked asset/beneficiary ownership if links change.

### Verification

- Allows user or future trusted workflow to mark document as verified.
- Sets `verification_status = VERIFIED`, `verified_at`, `review_due_at`, `modified_by`, and `updated_at`.
- Should not imply legal validity; only user/system review status.

### Expiration

- `expiration_date` triggers `EXPIRED` or `NEEDS_REVIEW` state.
- Expired documents remain visible unless archived.
- Replacement should be encouraged instead of deletion.

### Archival

- Sets `status = ARCHIVED` and `archived_at`.
- Excluded from default lists.
- Preserves encrypted content and metadata for historical continuity.

### Replacement/versioning

- Prefer creating a new document row linked by `version_group_id` and `supersedes_document_id`.
- Mark old document as `REPLACED` or archived.
- Preserve previous encrypted content and metadata.

### Linked asset archived

- Do not delete documents.
- Keep documents viewable from archived/historical views.
- Default active document lists may exclude documents linked only to archived assets unless requested.
- New uploads to archived assets should be rejected or require a future explicit historical-entry flag.

### Linked beneficiary archived/deceased

- Do not delete documents.
- Keep documents viewable for historical/legal continuity.
- New uploads linked to archived beneficiaries should be rejected by default.
- New uploads linked to deceased beneficiaries may be allowed only for historical/legal records if explicitly supported; otherwise reject in initial implementation.

### Retention

- Retain archived/replaced documents unless user explicitly requests deletion and policy permits.
- Support export before deletion in future privacy workflows.
- Retention policy should account for legal/estate planning needs.

### Permanent deletion

- Prefer archive/versioning over destructive delete.
- If permanent deletion is ever allowed:
  - Require re-authentication or strong confirmation.
  - Delete encrypted object and metadata or tombstone metadata.
  - Write audit event without sensitive fields.
  - Handle object storage versioning and backups according to retention policy.

## 9. Future API Design Proposal

Do not implement these endpoints in this phase.

### `POST /documents`

Purpose: upload a document and create metadata.

Authentication: required.

Ownership checks:

- Verify current user.
- Verify optional `asset_id` belongs to user.
- Verify optional `beneficiary_id` belongs to user.
- Return `404` for cross-user linked records.

Request schema:

- Multipart file upload plus metadata fields:
  - `asset_id?`
  - `beneficiary_id?`
  - `document_type`
  - `document_name`
  - `description?`
  - `expiration_date?`
  - `effective_date?`

Response schema:

- Safe metadata only: IDs, type, display metadata, size, MIME type, lifecycle status, verification status, timestamps.
- No storage reference, encrypted reference, signed URL, or content.

Encryption behavior:

- Encrypt content before persistence.
- Encrypt storage reference.
- Store integrity checksum.

Audit requirements:

- Record `document.created` with document ID, user ID, linked IDs, status, and non-sensitive metadata only.

Lifecycle behavior:

- Initial status `PENDING_SCAN` if scanning exists, otherwise `ACTIVE` with clear risk acceptance.

### `GET /documents`

Purpose: list documents for current user.

Authentication: required.

Ownership checks:

- Filter by `Document.user_id == current_user.id`.
- Optional asset/beneficiary filters must be owner-scoped.

Request/query schema:

- `asset_id?`
- `beneficiary_id?`
- `document_type?`
- `status?`
- `include_archived=false`

Response schema:

- List of safe metadata summaries.
- No storage references, checksums unless required, signed URLs, or encrypted fields.

Encryption behavior:

- No decryption of file content.
- Decrypt display metadata only if stored encrypted and needed for response.

Audit requirements:

- Optional read audit depending on sensitivity policy.

Lifecycle behavior:

- Exclude archived documents by default.

### `GET /documents/{document_id}`

Purpose: retrieve safe metadata for a single document.

Authentication: required.

Ownership checks:

- Lookup by `document_id` and `current_user.id`.
- Return `404` if not found or cross-user.

Response schema:

- Safe metadata detail.
- No storage reference or content.

Encryption behavior:

- Decrypt only safe display metadata, not file bytes.

Audit requirements:

- Optional metadata-view audit.

Lifecycle behavior:

- Archived document detail may be viewable if directly requested by owner.

### `PUT /documents/{document_id}`

Purpose: update metadata only.

Authentication: required.

Ownership checks:

- Document must belong to current user.
- New linked asset/beneficiary must belong to current user.

Request schema:

- `asset_id?`
- `beneficiary_id?`
- `document_type?`
- `document_name?`
- `description?`
- `expiration_date?`
- `effective_date?`
- `review_due_at?`

Response schema:

- Safe metadata detail.

Encryption behavior:

- Encrypt sensitive metadata fields before persistence.
- Do not modify file bytes.

Audit requirements:

- Record `document.metadata_updated` with non-sensitive changed field names.

Lifecycle behavior:

- Reject updates to archived documents unless a future restore/correction workflow is defined.

### `POST /documents/{document_id}/archive`

Purpose: archive document without deleting content.

Authentication: required.

Ownership checks:

- Document must belong to current user.

Request schema:

- Optional encrypted `archive_reason` in future.

Response schema:

- Safe confirmation metadata: `id`, `status`, `archived_at`.

Encryption behavior:

- No file decryption required.
- Encrypt archive reason if accepted.

Audit requirements:

- Record `document.archived`.

Lifecycle behavior:

- Set `status = ARCHIVED`, `archived_at`, `modified_by`, `updated_at`.

### `POST /documents/{document_id}/verify`

Purpose: mark document metadata/content as reviewed.

Authentication: required.

Ownership checks:

- Document must belong to current user.

Request schema:

- `verification_status`
- `review_due_at?`
- Optional encrypted notes in future.

Response schema:

- Safe metadata with verification fields.

Encryption behavior:

- No content decryption required unless checksum verification is part of verification.

Audit requirements:

- Record `document.verified` or `document.review_status_changed`.

Lifecycle behavior:

- Set `verified_at` when status becomes `VERIFIED`.
- Reject verification for quarantined/rejected documents.

### `GET /documents/{document_id}/download`

Purpose: authorized download/decrypt of document content.

Authentication: required.

Ownership checks:

- Document must belong to current user.
- Return `404` for missing/cross-user.
- Confirm document is not archived/quarantined unless policy allows historical download.

Request schema:

- No body.

Response schema:

- File stream with safe `Content-Type` and `Content-Disposition`.
- No JSON metadata unless using a signed-download preparation endpoint.

Encryption behavior:

- Decrypt `storage_reference_encrypted` server-side.
- Retrieve encrypted bytes.
- Verify checksum.
- Decrypt content after authorization.
- Stream decrypted bytes with safe headers or generate short-lived signed access only if object remains encrypted/client-safe.

Audit requirements:

- Record `document.downloaded` with document ID, user ID, timestamp, IP/user-agent if policy permits.
- Never log filename, storage path, or content.

Lifecycle behavior:

- Reject or require explicit include flag for archived/replaced documents.

## 10. Test Plan

Future implementation tests should cover:

1. Owner uploads metadata/file for own asset.
2. Owner uploads metadata/file for own beneficiary.
3. User-level document can be created without asset or beneficiary.
4. Cross-user asset link is blocked with `404`.
5. Cross-user beneficiary link is blocked with `404`.
6. Cross-user document detail/download returns `404`.
7. `storage_reference_encrypted` is populated and plaintext storage reference is not persisted.
8. List responses do not include storage path, encrypted storage reference, signed URL, ciphertext, or key reference.
9. Invalid document type is rejected.
10. Invalid MIME type is rejected.
11. Oversized file is rejected.
12. Empty file handling follows policy.
13. Suspicious filenames and double extensions are rejected.
14. Content-type/extension mismatch is rejected.
15. Malware scanning hook can quarantine/reject files.
16. Archived documents are excluded from default lists.
17. Download requires ownership and authorization.
18. Checksum validation detects corrupted encrypted bytes.
19. Encrypted content is not stored as plaintext.
20. Replacement/versioning preserves prior document history.
21. Metadata updates do not alter file bytes.
22. Archived linked assets/beneficiaries follow lifecycle policy.
23. Sensitive metadata is not logged in audit events.

## 11. Security Risks

- Current `Document.storage_reference` is plaintext and must not be exposed through APIs.
- Direct file paths, bucket names, object keys, or signed URLs can leak storage topology and should never be returned in list/detail responses.
- User-provided filenames and descriptions may contain sensitive data and should be encrypted or sanitized.
- MIME type and extension validation can be bypassed if not backed by server-side content inspection.
- Malware scanning is not currently implemented; production upload should include a scanning/quarantine workflow.
- Application-level encryption must be carefully separated between metadata encryption and content encryption.
- Large-file encryption must avoid loading unbounded file bytes into memory.
- Global duplicate detection could leak cross-user document existence.
- Parent cascade delete relationships could remove document metadata if users/assets are hard-deleted; product policy should prefer archive/export workflows.
- Signed URLs must be short-lived, authorization-gated, and never public.

## 12. Implementation Priorities

1. Replace plaintext `storage_reference` with `storage_reference_encrypted` before any document API exposure.
2. Add controlled document type constants and schema validation.
3. Add document metadata fields for lifecycle, verification, file metadata, checksum, and optional beneficiary linkage.
4. Define local private encrypted storage abstraction for development.
5. Define production object-storage abstraction without public URLs.
6. Implement per-document content encryption and encrypted storage-reference handling.
7. Add strict owner-scoped lookup helpers for documents, linked assets, and linked beneficiaries.
8. Add upload/list/detail/update/archive/verify/download APIs only after storage and encryption foundations are in place.
9. Add audit logging that excludes sensitive metadata.
10. Add malware scanning/quarantine integration before production document uploads.
11. Add comprehensive tests for ownership, encryption, validation, lifecycle, and response redaction.

## 13. Transitional Provider-Neutral Storage State

The provider-neutral hardening layer uses three database-authoritative states:

- `PENDING`: metadata exists without committed content, or one atomically claimed upload attempt is in progress.
- `STORED`: encrypted content and its database metadata are committed. This is the transitional Discovery-eligible state and does **not** mean malware scanning occurred.
- `FAILED`: the current upload attempt failed and may be atomically replaced by a retry.

`SCANNING`, `CLEAN`, `QUARANTINED`, and `REJECTED` are deliberately deferred
until malware scanning is implemented. At that point, Discovery eligibility
must move from transitional `STORED` to the approved clean state.

Each successful new upload records an opaque UUID attempt ID, ciphertext SHA-256,
ciphertext size, storage backend, encrypted backend-neutral locator, encryption
format, and non-secret `master_key_id`. The identifier selects which configured
master key wrapped the per-document DEK; it is not key material. Existing single
`ENCRYPTION_KEY` behavior remains unchanged, and no rotation is implemented by
this state model.

The legacy plaintext `checksum_sha256` column is retained for additive migration
and rollback compatibility, but new uploads do not populate it and API responses
do not expose it. Ciphertext SHA-256 plus Fernet authentication provide the new
storage-integrity path without creating a global plaintext document fingerprint.

`LocalDocumentStorage` remains development-oriented. Object storage, durable
outbox/reconciliation, coordinated backup/restore and key recovery, deployment
monitoring, and malware scanning remain required before real-data production use.
