# LegacyGuard Asset Inventory Architecture

## Purpose

This document defines the design for the first LegacyGuard asset management feature before API endpoints are implemented.

This is a design proposal only. It does not create endpoints, modify models, or change database architecture.

## Goals

- Allow authenticated users to maintain an inventory of personal legacy assets.
- Enforce strict ownership so users can only access their own assets.
- Separate searchable asset metadata from highly sensitive encrypted asset details.
- Prepare future relationships from assets to beneficiaries, documents, and reports.
- Preserve compatibility with the existing SQLAlchemy model structure.

## Existing Model Overview

The current backend already includes:

- `User`
- `Asset`
- `AssetDetail`
- `AssetBeneficiary`
- `Beneficiary`
- `Document`
- `Report`
- `Task`

The first asset feature should build on the existing `Asset` and `AssetDetail` models.

## Entity Relationship Overview

```text
User
 |
 | 1-to-many
 v
Assets
 |
 | 1-to-one
 v
AssetDetails
```

Future relationships:

```text
Assets 1-to-many AssetBeneficiaries many-to-1 Beneficiaries
Assets 1-to-many Documents
Assets used as source data for Reports
```

## 1. Asset Entity Design

Current model: `backend/app/models/asset.py`

### Purpose

`Asset` stores searchable asset metadata and ownership information. It should not store account numbers, policy numbers, credentials, or private notes in plaintext.

### Fields

| Field | Data type | Required | Searchable | Protection | Purpose |
|---|---:|---:|---:|---|---|
| `id` | `String` | Yes | Yes | Internal | Asset primary key. Should be UUID-style. |
| `user_id` | `String` | Yes | Yes | Internal | Owner ID. Required for authorization and filtering. |
| `asset_category` | `String` | Yes | Yes | Sensitive metadata | Category such as bank account, investment, real estate, insurance policy, vehicle, business, digital asset, or other. |
| `asset_name` | `String` | Yes | Yes, with caution | Sensitive metadata | User-facing display name. May reveal asset purpose. |
| `institution` | `String` | No | Yes, with caution | Sensitive metadata | Bank, insurer, brokerage, employer, custodian, or other institution. |
| `description` | `Text` | No | No recommended | Encrypt if used for private details | Free text can contain sensitive data. Avoid using for confidential details unless encrypted replacement exists. |
| `estimated_value` | `Numeric(12, 2)` | No | Optional | Sensitive financial metadata | Used for planning and reporting. Consider privacy tradeoffs before indexing/filtering. |
| `ownership_type` | `String` | No | Yes | Sensitive metadata | Individual, joint, trust-owned, business-owned, beneficiary-designated, etc. |
| `status` | `String` | Yes | Yes | Internal workflow metadata | Active, inactive, closed, transferred, archived. |
| `created_at` | `DateTime(timezone=True)` | Yes | Yes | Internal | Creation timestamp. |
| `updated_at` | `DateTime(timezone=True)` | Yes | Yes | Internal | Update timestamp. |
| `created_by` | `String` | No | Yes | Internal audit metadata | User who created the asset. |
| `modified_by` | `String` | No | Yes | Internal audit metadata | User who last modified the asset. |

### Recommended Asset Categories

Initial categories should be controlled values to reduce inconsistent user input:

- Bank Account
- Investment Account
- Retirement Account
- Insurance Policy
- Real Estate
- Vehicle
- Business Interest
- Digital Asset
- Safe Deposit Box
- Personal Property
- Debt / Liability
- Other

### Ownership Rules

- Every asset must have exactly one owning `user_id`.
- `user_id` must be assigned from the authenticated user, not accepted from client input.
- Users may create, read, update, and delete only their own assets.
- Cross-user asset access should return `404 Resource not found` instead of `403` to avoid revealing resource existence.
- List queries must always filter by `Asset.user_id == current_user.id`.
- Updates and deletes must first load the asset through ownership-aware authorization utilities.

### Asset Search Strategy

Search/filter should initially use only metadata fields:

- `asset_category`
- `status`
- `ownership_type`
- optionally `institution`
- optionally `asset_name`
- optionally value ranges for `estimated_value`

Search must not depend on encrypted account numbers, policy numbers, notes, or credential references.

## 2. AssetDetail Entity Design

Current model: `backend/app/models/asset_detail.py`

### Purpose

`AssetDetail` stores sensitive details for one asset. It should hold encrypted financial identifiers and private notes separate from searchable asset metadata.

### Relationship

- `Asset` has one `AssetDetail` record.
- `AssetDetail.asset_id` is unique and references `assets.id`.
- Deleting an asset should delete its asset detail through cascade behavior.

### Fields

| Field | Data type | Required | Searchable | Protection | Purpose |
|---|---:|---:|---:|---|---|
| `id` | `String` | Yes | Yes | Internal | Asset detail primary key. |
| `asset_id` | `String` | Yes | Yes | Internal | One-to-one link to `Asset`. |
| `account_number_encrypted` | `Text` | No | No | Encrypted | Account number or equivalent financial identifier. |
| `policy_number_encrypted` | `Text` | No | No | Encrypted | Insurance policy number or similar policy identifier. |
| `login_information_reference` | `Text` | No | No recommended | Encrypt before use | Reference to credential vault item or login instructions. Current plaintext field should not store secrets. |
| `contact_information` | `Text` | No | No recommended | Encrypt before use | Contact information can include names, phones, emails, or service representatives. Current plaintext field should be replaced or treated carefully. |
| `notes_encrypted` | `Text` | No | No | Encrypted | Private notes. |
| `created_at` | `DateTime(timezone=True)` | Yes | Yes | Internal | Creation timestamp. |
| `updated_at` | `DateTime(timezone=True)` | Yes | Yes | Internal | Update timestamp. |
| `created_by` | `String` | No | Yes | Internal audit metadata | User who created the details. |
| `modified_by` | `String` | No | Yes | Internal audit metadata | User who last modified the details. |

### Encryption Requirements

These fields must always be encrypted before persistence:

- account numbers
- policy numbers
- private notes

These fields should be encrypted before being exposed through production APIs:

- login information references
- contact information

Plaintext must not be logged, included in audit details, or returned to unauthorized users.

### Searchable Fields

`AssetDetail` should not be used for general search. Searchable values should live in `Asset` metadata. Sensitive fields in `AssetDetail` are encrypted and should not be queried directly.

If exact-match lookup is ever required for sensitive values, use a separate keyed hash/token column instead of plaintext.

## 3. Database Relationships

### User to Assets

```text
User.id -> Asset.user_id
```

- One user owns many assets.
- `Asset.user_id` is required and indexed.
- User deletion cascades to owned assets.

### Asset to AssetDetails

```text
Asset.id -> AssetDetail.asset_id
```

- One asset has one detail record.
- `AssetDetail.asset_id` is unique and indexed.
- Asset deletion cascades to its detail record.

### SQLAlchemy Relationships

Existing relationship direction:

- `User.assets`
- `Asset.user`
- `Asset.details`
- `AssetDetail.asset`

Note: `Asset.details` is currently modeled as a relationship collection even though `AssetDetail.asset_id` is unique. Future cleanup may consider `uselist=False`, but this phase does not modify models.

## 4. Security Requirements

### Authentication

- All future asset endpoints must require an authenticated user.
- Authentication should use the existing JWT/session dependency.

### Ownership Enforcement

Future asset endpoints must use the authorization foundation:

- list: `get_owned_query(db, Asset, current_user)`
- read/update/delete: `get_owned_record(db, Asset, asset_id, current_user)` or equivalent dependency
- create: assign `Asset.user_id = current_user.id` server-side

Client-supplied `user_id`, `created_by`, or `modified_by` values must be ignored or rejected.

### Encryption

- Sensitive detail values must be encrypted before database persistence.
- Decryption must occur only after ownership authorization succeeds.
- API responses should avoid returning encrypted ciphertext directly unless explicitly designed for internal diagnostics.
- API responses should return decrypted sensitive values only when necessary and only to the owner.

### Audit Requirements

Future asset operations should populate:

- `created_by` on create
- `modified_by` on create/update
- `created_at` and `updated_at` via database defaults/on-update behavior

Audit events should be logged for:

- asset created
- asset viewed, if audit requirements demand read tracking
- asset updated
- asset deleted/archived
- asset detail updated

Audit logs must not include plaintext account numbers, policy numbers, notes, or document references.

### Validation Requirements

Future API schemas should validate:

- non-empty asset name
- supported asset category
- non-negative estimated value
- controlled status values
- controlled ownership type values where possible
- maximum lengths for text inputs
- no client-controlled owner fields

## 5. Future Relationships

### Assets to Beneficiaries

Current join model: `AssetBeneficiary`

Relationship:

```text
Asset.id -> AssetBeneficiary.asset_id
Beneficiary.id -> AssetBeneficiary.beneficiary_id
```

Purpose:

- Assign one or more beneficiaries to an asset.
- Store percentage, transfer priority, and transfer method.

Security rule:

- The asset and beneficiary must both belong to the current user before a relationship can be created.

### Assets to Documents

Current model: `Document`

Relationship:

```text
Asset.id -> Document.asset_id
```

Purpose:

- Attach account statements, policies, deeds, legal documents, IDs, or supporting files to an asset.

Security rule:

- A document linked to an asset must belong to the same user as the asset.
- Document storage references should be encrypted before document APIs are exposed.

### Assets to Reports

Current model: `Report`

Relationship today:

```text
User.id -> Report.user_id
```

Future design:

- Reports may aggregate asset data by user.
- Reports should not require direct asset foreign keys unless per-asset reports become a feature.
- Report content should be encrypted before report generation APIs are exposed.

## 6. Future API Design Proposal

No endpoints are implemented in this phase. The proposed future API shape is below.

### `POST /assets`

Purpose: create an asset and optional asset details.

Security:

- Requires authentication.
- Sets `user_id` from current user.
- Encrypts sensitive detail fields before persistence.
- Sets audit fields from current user.

Request concept:

```json
{
  "asset_name": "Checking Account",
  "asset_category": "Bank Account",
  "institution": "Example Bank",
  "estimated_value": 2500.00,
  "ownership_type": "Joint",
  "status": "Active",
  "details": {
    "account_number": "123456789",
    "policy_number": null,
    "notes": "Private owner note"
  }
}
```

Response concept:

```json
{
  "id": "asset-id",
  "asset_name": "Checking Account",
  "asset_category": "Bank Account",
  "institution": "Example Bank",
  "estimated_value": "2500.00",
  "ownership_type": "Joint",
  "status": "Active",
  "created_at": "...",
  "updated_at": "..."
}
```

Sensitive detail values should be omitted by default or returned only through explicit detail views.

### `GET /assets`

Purpose: list current user assets.

Security:

- Requires authentication.
- Always filters by current user.
- Supports metadata filters only.

Recommended filters:

- `asset_category`
- `status`
- `ownership_type`
- `institution`
- value range, if retained as searchable metadata

### `GET /assets/{id}`

Purpose: retrieve one owned asset.

Security:

- Requires authentication.
- Uses ownership-aware lookup.
- Returns `404` if missing or owned by another user.
- Decrypts sensitive details only after ownership is confirmed.

Recommended response behavior:

- Return asset metadata by default.
- Include details only if the endpoint is explicitly designed to return details.
- Never return ciphertext as if it were plaintext.

### `PUT /assets/{id}`

Purpose: update one owned asset.

Security:

- Requires authentication.
- Uses ownership-aware lookup.
- Ignores/rejects client-supplied owner and audit fields.
- Encrypts updated sensitive detail fields before persistence.
- Updates `modified_by`.

### `DELETE /assets/{id}`

Purpose: delete or archive one owned asset.

Security:

- Requires authentication.
- Uses ownership-aware lookup.
- Returns `404` if missing or owned by another user.

Design decision needed:

- Hard delete: remove asset and cascaded details/doc relationships.
- Soft delete/archive: set status to archived and preserve audit trail.

Recommendation: prefer soft delete/archive for estate-planning records unless legal deletion requirements demand hard delete.

## Response Model Recommendations

Separate request/response schemas should be used for metadata and details:

- `AssetCreate`
- `AssetUpdate`
- `AssetResponse`
- `AssetDetailCreate`
- `AssetDetailUpdate`
- `AssetDetailResponse`

Avoid returning:

- `user_id` unless needed internally
- `created_by`
- `modified_by`
- encrypted ciphertext fields

Return decrypted sensitive values only in owner-authorized detail responses.

## Implementation Recommendations

1. Keep `Asset` focused on searchable metadata.
2. Keep `AssetDetail` focused on encrypted sensitive values.
3. Assign ownership server-side.
4. Use ownership utilities for every read/update/delete operation.
5. Encrypt before persistence and decrypt only after authorization.
6. Avoid logging plaintext sensitive values.
7. Add tests for:
   - asset creation assigns current user
   - list only returns current user assets
   - cross-user access returns `404`
   - encrypted fields are not stored plaintext
   - update/delete enforce ownership

## Open Design Decisions

- Whether `Asset.description` should remain plaintext, be removed, or receive an encrypted replacement.
- Whether `Asset.estimated_value` should remain searchable plaintext or be encrypted.
- Whether `Asset.details` relationship should be changed to `uselist=False` in a future model cleanup.
- Whether deletion should be hard delete or archive-by-status.
- Whether asset names and institutions should remain searchable plaintext or move to encrypted display plus tokenized lookup.
