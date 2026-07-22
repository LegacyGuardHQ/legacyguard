# LegacyGuard Beneficiary Management Architecture

## Purpose

This document designs the beneficiary system for LegacyGuard before beneficiary APIs are implemented.

This is a design document only. It does not modify models, schemas, migrations, or API endpoints.

## Goals

- Allow users to maintain a private list of beneficiaries.
- Allow assets to be associated with one or more beneficiaries.
- Support beneficiary percentages, primary/contingent designations, and transfer priority/order.
- Protect beneficiary personal information with encryption where appropriate.
- Enforce strict ownership across beneficiaries, assets, and asset-beneficiary links.
- Prepare for estate-planning concerns such as deceased beneficiaries, stale information, and periodic review.

## Current Model Review

Current models reviewed:

- `backend/app/models/beneficiary.py`
- `backend/app/models/asset_beneficiary.py`
- `backend/app/schemas/legacy.py`

Current `Beneficiary` fields:

- `id`
- `user_id`
- `name`
- `relationship_type`
- `contact_information`
- `notes`
- `created_at`
- `updated_at`
- `created_by`
- `modified_by`

Current `AssetBeneficiary` fields:

- `id`
- `asset_id`
- `beneficiary_id`
- `percentage`
- `transfer_priority`
- `transfer_method`
- `created_at`
- `updated_at`
- `created_by`
- `modified_by`

## 1. Beneficiary Entity Design

### Purpose

`Beneficiary` represents a person, trust, charity, organization, or other recipient who may receive or be associated with one or more assets.

Beneficiaries are user-owned records. A beneficiary created by one user must never be visible to or linkable by another user.

### Current Field Classification

| Field | Data type | Sensitivity | Recommended storage | Reason |
|---|---:|---|---|---|
| `id` | `String` | Internal | Plaintext searchable | Primary key for relationships. |
| `user_id` | `String` | Internal | Plaintext searchable | Ownership boundary. Required for authorization. |
| `name` | `String` | Sensitive | Plaintext searchable initially; optional future encrypted display plus tokenized lookup | Beneficiary name is personal data but useful for user search/listing. |
| `relationship_type` | `String` | Sensitive | Plaintext searchable | Useful for filtering and estate context, but reveals family/personal relationships. |
| `contact_information` | `Text` | Highly sensitive | Encrypted recommended | May include email, phone, address, or private contact details. Current plaintext field should not be exposed in production APIs without encryption. |
| `notes` | `Text` | Highly sensitive | Encrypted recommended | Free text may contain private family, legal, or estate-planning context. |
| `created_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `updated_at` | `DateTime` | Internal | Plaintext searchable | Operational timestamp. |
| `created_by` | `String` | Internal | Plaintext searchable | Audit metadata. |
| `modified_by` | `String` | Internal | Plaintext searchable | Audit metadata. |

### Recommended Future Fields

Before implementing production beneficiary APIs, consider adding:

| Field | Purpose | Protection |
|---|---|---|
| `contact_information_encrypted` | Encrypted contact details. | Encrypted |
| `notes_encrypted` | Encrypted beneficiary notes. | Encrypted |
| `verification_status` | Tracks whether beneficiary information is current. | Plaintext searchable |
| `verified_at` | Timestamp for last verification. | Plaintext searchable |
| `review_due_at` | Date the beneficiary should be reviewed again. | Plaintext searchable |
| `is_deceased` | Indicates beneficiary is deceased. | Sensitive metadata |
| `deceased_at` | Optional date of death. | Sensitive metadata |
| `status` | Active, inactive, archived, deceased, needs review. | Plaintext searchable |
| `archived_at` | Soft archive timestamp. | Plaintext searchable |

### Ownership Rules

- Every beneficiary must have exactly one `user_id` owner.
- `user_id` must be assigned server-side from the authenticated user.
- Clients must not provide or override `user_id`, `created_by`, or `modified_by`.
- Users may create, read, update, archive, and link only their own beneficiaries.
- Cross-user access should return `404 Resource not found` to avoid leaking existence.
- Beneficiary list queries must always filter by `Beneficiary.user_id == current_user.id`.

## 2. Asset ↔ Beneficiary Relationship Design

Current join model: `backend/app/models/asset_beneficiary.py`

Relationship:

```text
Asset.id       -> AssetBeneficiary.asset_id
Beneficiary.id -> AssetBeneficiary.beneficiary_id
```

Conceptually:

```text
User
 ├── Assets
 │    └── AssetBeneficiary links
 └── Beneficiaries
      └── AssetBeneficiary links
```

### Multiple Beneficiaries per Asset

An asset may have multiple beneficiaries through multiple `AssetBeneficiary` records.

Rules:

- The same asset can link to multiple beneficiaries.
- A beneficiary can be linked to multiple assets.
- Asset and beneficiary must both belong to the current user.
- Duplicate links between the same asset and beneficiary should be prevented with a future uniqueness constraint or application validation.

Recommended future uniqueness rule:

```text
unique(asset_id, beneficiary_id)
```

### Beneficiary Percentages

Current field:

```python
percentage = Column(Numeric(5, 2), nullable=True)
```

Recommended rules:

- Percentage must be between `0` and `100`.
- For percentage-based transfer methods, total primary beneficiary percentages for an asset should not exceed `100`.
- Contingent beneficiary percentages may be validated separately from primary beneficiaries.
- `NULL` percentage can be allowed for non-percentage transfer methods or informational links.

### Primary vs Contingent Beneficiaries

Current model does not have an explicit primary/contingent field.

Current possible use:

- `transfer_priority` can indicate ordering, but it is currently a string and not ideal for primary/contingent semantics.

Recommended future field:

```text
beneficiary_role
```

Allowed values:

- `PRIMARY`
- `CONTINGENT`
- `SUCCESSOR`
- `INFORMATIONAL`

Storage:

- Plaintext searchable, because it is operational estate metadata.

### Priority / Order

Current field:

```python
transfer_priority = Column(String, nullable=True)
```

Recommended future refinement:

- Convert or supplement with integer priority/order, for example `priority_order`.
- Lower numbers should represent higher priority.
- Use together with `beneficiary_role` to order contingent or successor beneficiaries.

Example:

```text
PRIMARY priority 1: spouse 100%
CONTINGENT priority 1: child A 50%
CONTINGENT priority 1: child B 50%
SUCCESSOR priority 2: trust 100%
```

### Relationship Type

`Beneficiary.relationship_type` describes the beneficiary’s relationship to the user, such as:

- spouse
- child
- parent
- sibling
- trust
- charity
- business partner
- estate
- other

This should stay on the beneficiary record, not the asset-beneficiary link, because it describes the beneficiary globally relative to the user.

## 3. Security Requirements

### Authentication

All future beneficiary endpoints must require authentication using the existing auth dependency.

### Ownership Enforcement

Beneficiary APIs must enforce ownership at every boundary:

- list: filter by current user
- read/update/archive: load by ID and current user
- link to asset: verify both asset and beneficiary are owned by the current user

Cross-user access must return `404`.

### Encrypted Contact Information

Beneficiary contact information should be encrypted before storage.

Current field:

```text
contact_information
```

Recommended future field:

```text
contact_information_encrypted
```

Plaintext contact information should not be logged, audited, or returned to unauthorized users.

### Encrypted Sensitive Notes

Current field:

```text
notes
```

Recommended future field:

```text
notes_encrypted
```

Notes are free text and should be treated as highly sensitive.

### Audit Requirements

Future beneficiary operations should populate:

- `created_by`
- `modified_by`
- `created_at`
- `updated_at`

Recommended audit events:

- beneficiary created
- beneficiary updated
- beneficiary archived/deactivated
- beneficiary linked to asset
- beneficiary unlinked from asset
- beneficiary allocation changed

Audit logs must not include plaintext contact information or notes.

## 4. Future API Design

No endpoints are implemented in this phase.

### `POST /beneficiaries`

Purpose:

- Create a beneficiary owned by the authenticated user.

Security:

- Assign `user_id` from current user.
- Encrypt contact information and notes before persistence.
- Set audit fields from current user.

Request concept:

```json
{
  "name": "Jane Doe",
  "relationship_type": "Spouse",
  "contact_information": "jane@example.com, 555-0100",
  "notes": "Private family context"
}
```

Response concept:

```json
{
  "id": "beneficiary-id",
  "name": "Jane Doe",
  "relationship_type": "Spouse",
  "verification_status": "UNKNOWN",
  "created_at": "...",
  "updated_at": "..."
}
```

Sensitive fields should be omitted by default or returned only in owner-authorized detail responses.

### `GET /beneficiaries`

Purpose:

- List current user beneficiaries.

Security:

- Filter by current user.
- Exclude archived beneficiaries by default if archive support exists.
- Do not expose encrypted contact information or notes in list responses.

Recommended filters:

- relationship type
- status
- verification status
- review due date

### `GET /beneficiaries/{id}`

Purpose:

- Retrieve one beneficiary owned by the current user.

Security:

- Filter by beneficiary ID and current user ID.
- Return `404` for missing or cross-user records.
- Decrypt contact information and notes only after ownership verification.

### `PUT /beneficiaries/{id}`

Purpose:

- Update beneficiary metadata and encrypted fields.

Security:

- Enforce ownership.
- Re-encrypt updated contact information and notes.
- Update `modified_by` and `updated_at`.

### `POST /assets/{id}/beneficiaries`

Purpose:

- Link an existing beneficiary to an existing asset.

Security:

- Authenticate user.
- Verify asset belongs to user.
- Verify beneficiary belongs to user.
- Create `AssetBeneficiary` link only after both ownership checks pass.

Request concept:

```json
{
  "beneficiary_id": "beneficiary-id",
  "percentage": 50.00,
  "beneficiary_role": "PRIMARY",
  "priority_order": 1,
  "transfer_method": "Beneficiary Designation"
}
```

## 5. Estate-Planning Concerns

### Deceased Beneficiary Handling

Beneficiary records should support deceased/inactive states before production use.

Recommended future fields:

- `is_deceased`
- `deceased_at`
- `status`

Rules:

- Deceased beneficiaries should not be silently removed from historical asset plans.
- Asset allocations should flag deceased beneficiaries for review.
- Reports should identify assets with deceased or inactive beneficiaries.

### Outdated Information

Beneficiary contact information can become stale.

Recommended future fields:

- `verification_status`
- `verified_at`
- `review_due_at`

Recommended statuses:

- `UNKNOWN`
- `VERIFIED`
- `NEEDS_REVIEW`
- `OUTDATED`
- `DECEASED`
- `ARCHIVED`

### Verification Status

Beneficiary verification should be independent of asset verification.

Examples:

- Beneficiary contact info verified.
- Beneficiary still intended as recipient.
- Relationship or legal eligibility reviewed.

### Review Dates

Recommended review policy:

- prompt annual review of beneficiaries
- prompt review after major life events
- prompt review if beneficiary marked deceased, outdated, or unreachable

Life events:

- marriage
- divorce
- birth/adoption
- death
- relocation
- policy/account change
- estate plan update

## Implementation Recommendations

1. Add encrypted beneficiary contact and notes fields before beneficiary APIs.
2. Add beneficiary verification/review fields before production use.
3. Add primary/contingent role support to `AssetBeneficiary`.
4. Add integer priority/order support to `AssetBeneficiary`.
5. Add validation so allocation percentages do not exceed 100% per asset and beneficiary role group.
6. Enforce ownership for both sides of asset-beneficiary links.
7. Never include plaintext contact information or notes in audit logs.
8. Add tests for cross-user beneficiary access and cross-user asset-beneficiary linking.

## Open Design Decisions

- Whether beneficiary names remain plaintext searchable or move to encrypted display plus tokenized lookup.
- Whether `relationship_type` should be a controlled enum.
- Whether `transfer_priority` should be replaced by integer `priority_order`.
- Whether `beneficiary_role` should be added before the first linking API.
- Whether percentage validation should be strict at write time or warning-based for draft plans.
- Whether beneficiary archive/deceased states should prevent new asset links or only warn the user.
