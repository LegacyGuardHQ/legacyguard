# LegacyGuard Encryption Field Map

## Purpose

This document classifies current and planned LegacyGuard data fields by sensitivity and recommended storage method before asset, beneficiary, or document APIs are created.

This is a review and recommendation document only. It does not modify models, schemas, migrations, or APIs.

## Classification Legend

### Sensitivity Levels

- **Public**: Safe to expose broadly, such as non-user-specific service metadata.
- **Internal**: Operational data needed by the application but not meant for public exposure.
- **Sensitive**: Personal or contextual information that may reveal user behavior, relationships, or private planning details.
- **Highly sensitive**: Financial account data, policy numbers, private notes, document references, recovery material, or data that could enable fraud or identity theft.

### Storage Methods

- **Plaintext searchable**: Stored in plaintext to support lookup, filtering, sorting, ownership checks, or indexes.
- **Encrypted**: Stored using application-level authenticated encryption, preferably in explicit `_encrypted` columns.
- **Hashed/tokenized**: Stored as a keyed hash or lookup token for equality search without storing the original plaintext.

## User Model

Current model: `backend/app/models/user.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key required for ownership, joins, and authorization. |
| `email` | `String` | Sensitive | Plaintext searchable now; recommended future hashed/tokenized lookup plus encrypted display value | Required today for login and uniqueness. Email is personal data and should be protected more strongly if privacy requirements increase. |
| `password_hash` | `String` | Highly sensitive | Hashed/tokenized | Passwords must never be encrypted reversibly. Current bcrypt hashing is appropriate. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp useful for sorting and audit history. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp useful for synchronization and audit history. |
| `last_login` | `DateTime` | Sensitive | Plaintext searchable | Useful for security monitoring but reveals account activity. Restrict access. |
| `is_active` | `Boolean` | Internal | Plaintext searchable | Required for account status checks. |
| `role` | `String` | Internal | Plaintext searchable | Required for authorization and future RBAC. |
| Future `legal_name` | `String` | Sensitive | Encrypted | Direct personal identifier. |
| Future `phone_number` | `String` | Sensitive | Encrypted; optional hashed/tokenized normalized phone for lookup | Personal contact information. |
| Future `address` | `Text` | Highly sensitive | Encrypted | Direct location and identity information. |
| Future `date_of_birth` | `Date` | Highly sensitive | Encrypted | Identity-theft risk. |
| Future `government_id` / `tax_id` | `String` | Highly sensitive | Encrypted; never plaintext searchable | Identity-theft and fraud risk. |

## Asset Model

Current model: `backend/app/models/asset.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key. |
| `user_id` | `String` | Internal | Plaintext searchable | Required for ownership authorization and filtering. |
| `asset_category` | `String` | Sensitive | Plaintext searchable | Needed for filtering, but categories can reveal financial profile. Keep values controlled. |
| `asset_name` | `String` | Sensitive | Plaintext searchable or encrypted depending on product search needs | User-facing label may reveal institution/account context. Consider encrypted display name plus searchable category if stronger privacy is required. |
| `institution` | `String` | Sensitive | Plaintext searchable or encrypted depending on search needs | Financial institution can reveal user holdings. Keep searchable only if required. |
| `description` | `Text` | Highly sensitive | Encrypted recommended | Free text may contain account numbers, private notes, or personally identifying details. |
| `estimated_value` | `Numeric` | Sensitive | Plaintext searchable or encrypted depending on analytics needs | Financial value is sensitive. Plaintext supports sorting/reporting but increases privacy risk. |
| `ownership_type` | `String` | Sensitive | Plaintext searchable | Useful classification field; may reveal estate structure. |
| `status` | `String` | Internal | Plaintext searchable | Operational state needed for filtering. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit/ownership metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit/ownership metadata. |

## Asset Detail Model

Current model: `backend/app/models/asset_detail.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key. |
| `asset_id` | `String` | Internal | Plaintext searchable | Required relationship key. |
| `account_number_encrypted` | `Text` | Highly sensitive | Encrypted | Account numbers can enable fraud and must never be stored plaintext. Existing encrypted column is appropriate. |
| `policy_number_encrypted` | `Text` | Highly sensitive | Encrypted | Insurance policy numbers are sensitive financial/legal identifiers. Existing encrypted column is appropriate. |
| `login_information_reference` | `Text` | Highly sensitive | Encrypted recommended | Credential vault references or login hints may expose access paths. Current field is plaintext and should be migrated to encrypted storage before use. |
| `contact_information` | `Text` | Sensitive | Encrypted recommended | Contact data may include names, phone numbers, emails, or private service contacts. Current field is plaintext and should be encrypted before sensitive use. |
| `notes_encrypted` | `Text` | Highly sensitive | Encrypted | Private notes may contain secrets or estate-planning details. Existing encrypted column is appropriate. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit metadata. |

## Beneficiary Model

Current model: `backend/app/models/beneficiary.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key. |
| `user_id` | `String` | Internal | Plaintext searchable | Required for ownership checks. |
| `name` | `String` | Sensitive | Plaintext searchable or encrypted depending on search requirements | Beneficiary names are personal data. Searchability may be useful, but encrypted display plus tokenized lookup is more private. |
| `relationship_type` | `String` | Sensitive | Plaintext searchable | Useful classification field but reveals personal relationships. |
| `contact_information` | `Text` | Highly sensitive | Encrypted recommended | May contain phone, email, address, and other personal details. Current field is plaintext and should be encrypted before API exposure. |
| `notes` | `Text` | Highly sensitive | Encrypted recommended | Free text may include personal, legal, or family context. Current field is plaintext and should be encrypted before API exposure. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit metadata. |

## Document Model

Current model: `backend/app/models/document.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key. |
| `user_id` | `String` | Internal | Plaintext searchable | Required for ownership checks. |
| `asset_id` | `String` | Internal | Plaintext searchable | Relationship key; can reveal document-asset linkage. |
| `document_type` | `String` | Sensitive | Plaintext searchable | Needed for filtering, but can reveal legal/financial context. Keep controlled. |
| `document_name` | `String` | Sensitive | Plaintext searchable or encrypted depending on search needs | Names may reveal content. Consider encrypted display name plus tokenized lookup. |
| `storage_reference` | `Text` | Highly sensitive | Encrypted recommended | Storage paths, object keys, URLs, or provider references must not be exposed. Current field is plaintext and should be encrypted before document APIs. |
| `encrypted` | `Boolean` | Internal | Plaintext searchable | Operational flag indicating content encryption state. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| Future `content` / uploaded bytes | Binary/Object | Highly sensitive | Encrypted | Document contents may contain legal, financial, identity, or estate-planning data. Use per-document encryption keys and envelope encryption. |
| Future `extracted_text` | `Text` | Highly sensitive | Encrypted | Extracted text can expose full document contents. |

## Report Model

Current model: `backend/app/models/report.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key. |
| `user_id` | `String` | Internal | Plaintext searchable | Required for ownership checks. |
| `report_type` | `String` | Sensitive | Plaintext searchable | Needed for filtering; may reveal report purpose. |
| `content` | `Text` | Highly sensitive | Encrypted recommended | Reports may summarize assets, beneficiaries, documents, and private instructions. Current field is plaintext and should be encrypted before use. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit metadata. |

## Task Model

Current model: `backend/app/models/task.py`

| Field | Data type | Sensitivity level | Storage method | Reason for classification |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Internal primary key. |
| `user_id` | `String` | Internal | Plaintext searchable | Required for ownership checks. |
| `task_name` | `String` | Sensitive | Plaintext searchable or encrypted depending on search needs | Task names may reveal estate-planning activity. |
| `description` | `Text` | Highly sensitive | Encrypted recommended | Free text may contain private instructions or sensitive planning context. Current field is plaintext and should be encrypted if exposed. |
| `priority` | `String` | Internal | Plaintext searchable | Operational classification for sorting/filtering. |
| `status` | `String` | Internal | Plaintext searchable | Operational state for workflow filtering. |
| `due_date` | `DateTime` | Sensitive | Plaintext searchable | Scheduling data can reveal planning timeline. Useful for reminders and sorting. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit metadata. |

## Required Recommendations

### 1. Account Numbers

Account numbers are **highly sensitive** and should always use encrypted storage. The existing `AssetDetail.account_number_encrypted` field supports this correctly.

Recommended implementation priority: **high**.

### 2. Insurance Policy Numbers

Insurance policy numbers are **highly sensitive** and should always use encrypted storage. The existing `AssetDetail.policy_number_encrypted` field supports this correctly.

Recommended implementation priority: **high**.

### 3. Contact Information

Contact information should be encrypted when it includes personal phone numbers, emails, addresses, professional contacts, or asset-related contacts.

Fields needing encrypted replacements or migrations:

- `AssetDetail.contact_information`
- `Beneficiary.contact_information`

Recommended future names:

- `contact_information_encrypted`

Recommended implementation priority: **high before beneficiary/contact APIs**.

### 4. Personal Notes

Personal notes are **highly sensitive** because users may enter private instructions, family information, account context, credentials, or legal planning details.

Existing encrypted support:

- `AssetDetail.notes_encrypted`

Fields needing encrypted replacement:

- `Beneficiary.notes`
- free-text `Asset.description` if used for private detail

Recommended implementation priority: **high**.

### 5. Document References

Document storage references are **highly sensitive** because they may reveal storage provider paths, object IDs, bucket names, or access URLs.

Field needing encrypted replacement:

- `Document.storage_reference`

Recommended future name:

- `storage_reference_encrypted`

Recommended implementation priority: **high before document APIs**.

### 6. Reports

Report content is **highly sensitive** because it may aggregate the most private information in the system.

Field needing encrypted replacement:

- `Report.content`

Recommended future name:

- `content_encrypted`

Recommended implementation priority: **medium-high before report generation**.

### 7. Task Descriptions

Task descriptions should be treated as **highly sensitive** when they contain private instructions, legal planning notes, or asset context.

Field needing encrypted replacement:

- `Task.description`

Recommended future name:

- `description_encrypted`

Recommended implementation priority: **medium before task APIs**.

### 8. Email Addresses

Email addresses are **sensitive** personal data. The current plaintext `User.email` supports authentication lookup and uniqueness.

Recommended future privacy-enhanced pattern:

- `email_hash`: keyed hash/token for login lookup and uniqueness.
- `email_encrypted`: encrypted display/recovery email.
- Keep `email` plaintext only if operational simplicity is prioritized over stronger privacy.

Recommended implementation priority: **medium**, because changing login lookup affects authentication and migrations.

## Existing Model Support Assessment

### Supports Encryption Correctly Today

- `AssetDetail.account_number_encrypted`
- `AssetDetail.policy_number_encrypted`
- `AssetDetail.notes_encrypted`

These fields already follow the explicit encrypted-column naming pattern.

### Needs Encrypted Replacement Before Sensitive API Exposure

- `Asset.description`
- `AssetDetail.login_information_reference`
- `AssetDetail.contact_information`
- `Beneficiary.contact_information`
- `Beneficiary.notes`
- `Document.storage_reference`
- `Report.content`
- `Task.description`

### Can Remain Searchable With Caution

- `user_id`
- relationship IDs and primary keys
- category/type/status fields
- timestamps
- audit user IDs
- booleans such as `encrypted`, `is_active`, `mfa_enabled`

### Searchable But Privacy-Sensitive

These may remain plaintext only if product requirements need search/filtering:

- `User.email`
- `Asset.asset_name`
- `Asset.institution`
- `Asset.estimated_value`
- `Beneficiary.name`
- `Document.document_name`
- `Task.task_name`

For stronger privacy, use encrypted display fields plus keyed hashes/tokens for exact-match lookup.

## Implementation Priorities

1. **Before asset APIs**
   - Ensure asset account numbers, policy numbers, and notes only use encrypted fields.
   - Avoid accepting sensitive data into plaintext `Asset.description` unless encrypted replacement exists.

2. **Before beneficiary APIs**
   - Add encrypted beneficiary contact information and notes fields.
   - Decide whether beneficiary names remain searchable or move to encrypted display plus tokenized lookup.

3. **Before document APIs**
   - Replace plaintext `storage_reference` with encrypted storage reference.
   - Define document content encryption and per-document key strategy.

4. **Before reports/tasks APIs**
   - Encrypt report content.
   - Encrypt task descriptions if free text is user-controlled.

5. **Before production hardening**
   - Decide whether email remains plaintext or moves to keyed hash plus encrypted display value.
   - Add tests proving sensitive plaintext is not persisted.
   - Add logging review to prevent plaintext exposure.
