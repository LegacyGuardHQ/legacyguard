# Asset–Beneficiary Linking Architecture

## Scope

This document designs the secure workflow for linking beneficiaries to assets. It is architecture only: no endpoints, model changes, migrations, or frontend changes are implemented in this phase.

## 1. Current Join-Model Review

### `AssetBeneficiary` join model

Current file: `backend/app/models/asset_beneficiary.py`

The existing join model represents a many-to-many relationship between assets and beneficiaries:

- `id`: primary key, generated UUID string.
- `asset_id`: required foreign key to `assets.id`, indexed, `ondelete="CASCADE"`.
- `beneficiary_id`: required foreign key to `beneficiaries.id`, indexed, `ondelete="CASCADE"`.
- `percentage`: nullable `Numeric(5, 2)` allocation percentage.
- `beneficiary_role`: required string, default `PRIMARY`.
- `priority_order`: canonical nullable integer ordering field.
- `transfer_priority`: legacy nullable string retained for migration compatibility; deprecated for new behavior.
- `transfer_method`: nullable string.
- `created_at`, `updated_at`: timestamp fields.
- `created_by`, `modified_by`: audit actor fields.

Existing database constraints:

- Unique link constraint: one row per `(asset_id, beneficiary_id)`.
- Percentage range check: `percentage IS NULL OR (percentage >= 0 AND percentage <= 100)`.

Relinking behavior implemented in Phase 2: because the unique constraint allows only one row per `(asset_id, beneficiary_id)`, recreating a link for a previously deactivated pair reactivates and updates the existing inactive row instead of inserting a duplicate historical row.

Current limitations:

- No direct `user_id` column exists on the join row.
- Ownership must be enforced through both parent records: `Asset.user_id` and `Beneficiary.user_id`.
- `beneficiary_role` has no model-level controlled-value check yet.
- There is no allocation-total constraint at the database level.
- `priority_order` and `transfer_priority` overlap conceptually and should be clarified before endpoint implementation.
- Existing `ondelete="CASCADE"` can remove links if an asset or beneficiary is hard-deleted. API design should avoid hard deletes for lifecycle changes.

### `Asset` model relationship

Current file: `backend/app/models/asset.py`

- `Asset.user_id` defines ownership.
- Asset lifecycle fields include `status` and `archived_at`.
- `Asset.beneficiaries` relates to `AssetBeneficiary` with `cascade="all, delete-orphan"`.
- Archived assets should not be eligible for new beneficiary links by default.

### `Beneficiary` model relationship

Current file: `backend/app/models/beneficiary.py`

- `Beneficiary.user_id` defines ownership.
- Beneficiary lifecycle fields include `status`, `verification_status`, `review_due_at`, `is_deceased`, `deceased_at`, and `archived_at`.
- `Beneficiary.assets` relates to `AssetBeneficiary` with `cascade="all, delete-orphan"`.
- Sensitive beneficiary fields are encrypted separately and should not be exposed in list/link responses.

## 2. Linking Rules

The model should support:

- Multiple beneficiaries per asset.
- One beneficiary linked to multiple assets.
- Role-based beneficiary classes:
  - `PRIMARY`: first-line beneficiary allocation.
  - `CONTINGENT`: fallback beneficiary allocation if primary beneficiaries cannot receive the transfer.
  - `SUCCESSOR`: later-order successor beneficiary, typically ordered by `priority_order`.
  - `INFORMATIONAL`: contact or reference-only person with no allocation entitlement.
- Allocation percentage per link.
- Priority/order per link.
- Transfer method per link, such as:
  - `Beneficiary Designation`
  - `Will`
  - `Trust`
  - `TOD/POD`
  - `Joint Ownership`
  - `Manual Instruction`

Recommended controlled role values for future implementation:

```text
PRIMARY
CONTINGENT
SUCCESSOR
INFORMATIONAL
```

Recommended semantics:

- `PRIMARY` and `CONTINGENT` links may use percentages.
- `SUCCESSOR` links may use either percentages or priority ordering depending on asset type.
- `INFORMATIONAL` links should generally have `percentage = null` or `0` and should not contribute to allocation totals.
- `priority_order` should be treated as a numeric ordering concept even if currently stored as a string.
- `transfer_priority` should be deprecated or clearly mapped to `priority_order` in a future migration to avoid ambiguous ordering behavior.

## 3. Ownership Security

Future linking operations must enforce ownership through both parent records.

Strict rules:

1. The asset must belong to `current_user.id`.
2. The beneficiary must belong to `current_user.id`.
3. A link may only be created or changed when both parent records belong to the same authenticated user.
4. Cross-user asset references must return `404 Asset not found` or a generic not-found response.
5. Cross-user beneficiary references must return `404 Beneficiary not found` or a generic not-found response.
6. Responses must never reveal whether another user's asset, beneficiary, or link exists.
7. Link queries should join or separately verify asset ownership before returning link rows.
8. Link update/delete operations must verify ownership using the owning asset and beneficiary, not only the join-row ID.

Recommended lookup pattern:

```python
asset = db.query(Asset).filter(
    Asset.id == asset_id,
    Asset.user_id == current_user.id,
).first()
if asset is None:
    raise HTTPException(status_code=404, detail="Asset not found")

beneficiary = db.query(Beneficiary).filter(
    Beneficiary.id == beneficiary_id,
    Beneficiary.user_id == current_user.id,
).first()
if beneficiary is None:
    raise HTTPException(status_code=404, detail="Beneficiary not found")
```

## 4. Allocation Validation

### Individual percentage validation

- `percentage` may be `null` only for roles that do not require allocation, especially `INFORMATIONAL`.
- If provided, `percentage` must be between `0` and `100`, inclusive.
- Reject negative values.
- Reject values over `100`.
- Normalize precision to two decimal places.

### Role-group total validation

Allocation totals should be calculated per asset and per role group.

Recommended groups:

- Primary allocation group: `beneficiary_role = PRIMARY`.
- Contingent allocation group: `beneficiary_role = CONTINGENT`.
- Successor allocation group: validate separately if percentages are used.
- Informational group: excluded from percentage total validation.

Validation rules:

- Primary total must not exceed `100`.
- Contingent total must not exceed `100`.
- Successor total must not exceed `100` when successor percentages are used.
- Primary and contingent totals are independent. A valid plan may have `PRIMARY = 100` and `CONTINGENT = 100` because contingents only apply if primary transfer fails.
- Totals should be allowed to remain below `100` during planning to support incomplete drafts.
- A future verification workflow can warn when totals are below `100`, but create/update should not require exact `100` unless the product introduces a finalization step.

### Null percentage behavior

- `PRIMARY` and `CONTINGENT`: `null` means allocation is unknown/incomplete and should mark the asset or link as needing review.
- `SUCCESSOR`: `null` is acceptable if the successor is priority-based rather than percentage-based.
- `INFORMATIONAL`: `null` is preferred.

### Update/recalculation behavior

On create/update/unlink/deactivate:

1. Load all active links for the same asset and relevant role group.
2. Replace the target link's percentage with the proposed value in memory.
3. Sum non-null percentages in that group.
4. Reject the request if total exceeds `100`.
5. If totals are below `100`, allow the change but mark the link or asset verification state as `NEEDS_REVIEW` in a future lifecycle phase.

## 5. Lifecycle Rules

Do not automatically delete historical links.

### Beneficiary archived

- Existing links should remain for historical visibility.
- Archived beneficiaries should not be eligible for new links.
- Existing active links to archived beneficiaries should be treated as outdated or requiring review.
- Future list responses may include an `is_outdated` or `requires_review` flag.

### Beneficiary deceased

- Existing links should remain for historical continuity.
- New links to deceased beneficiaries should generally be blocked unless explicitly allowed for historical entry.
- Existing primary links to deceased beneficiaries should require review.
- Contingent/successor logic should not automatically rebalance allocations in this phase.

Phase 2 policy: deceased-beneficiary links remain viewable when already active/historical, but create/update operations reject changes that would make a deceased beneficiary an active recipient. Deactivation remains allowed so users can remove an active recipient while preserving historical data.

### Asset archived

- Archived assets should not accept new links or link updates by default.
- Existing links remain for historical records.
- Unlink/deactivate may be allowed only if needed for correction, with audit logging.

### Link becomes outdated

A link should be considered outdated or requiring review when:

- Linked beneficiary is archived.
- Linked beneficiary is deceased.
- Linked beneficiary verification status becomes `NEEDS_REVIEW` or `OUTDATED`.
- Asset verification status becomes `NEEDS_REVIEW` or `CLOSED`.
- Allocation totals are incomplete or exceed validation rules during attempted change.
- Transfer method is missing for asset categories that require one.

### Percentage or role changes

- Recalculate totals for the old and new role groups.
- Update `modified_by` and `updated_at`.
- Mark affected asset/link verification as needing review in a future implementation.
- Preserve prior state through audit logging rather than deleting history.

### Linked beneficiary requires review

- Link remains visible.
- Link responses should surface beneficiary lifecycle summary fields but should not expose sensitive beneficiary contact information by default.
- Planning UI/API can warn users that a linked beneficiary requires review.

## 6. Future API Design Proposal

All endpoints require authentication and must enforce ownership using `current_user.id`.

### `POST /assets/{asset_id}/beneficiaries`

Creates a link between an owned asset and an owned beneficiary.

Request schema proposal:

```json
{
  "beneficiary_id": "string",
  "beneficiary_role": "PRIMARY | CONTINGENT | SUCCESSOR | INFORMATIONAL",
  "percentage": 50.0,
  "priority_order": 1,
  "transfer_method": "Beneficiary Designation"
}
```

Response schema proposal:

```json
{
  "id": "string",
  "asset_id": "string",
  "beneficiary_id": "string",
  "beneficiary_name": "string",
  "beneficiary_role": "PRIMARY",
  "percentage": 50.0,
  "priority_order": 1,
  "transfer_method": "Beneficiary Designation",
  "requires_review": false,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

Authentication: required.

Ownership enforcement:

- Verify asset by `asset_id` and `current_user.id`.
- Verify beneficiary by `beneficiary_id` and `current_user.id`.
- Return 404 for cross-user or missing records.

Allocation validation:

- Validate individual percentage range.
- Validate role-group total does not exceed `100`.
- Reject duplicate active link for same asset and beneficiary.

Lifecycle behavior:

- Reject linking archived assets.
- Reject linking archived beneficiaries.
- Reject or require explicit override for deceased beneficiaries.

Audit expectations:

- Populate `created_by` and `modified_by`.
- Future audit event: `asset_beneficiary.link_created`.

### `GET /assets/{asset_id}/beneficiaries`

Lists beneficiary links for an owned asset.

Request schema: no body.

Optional query parameters:

- `include_inactive=false`
- `role=PRIMARY`

Response schema: list of link response objects.

Authentication: required.

Ownership enforcement:

- Verify asset by `asset_id` and `current_user.id` before returning links.

Allocation validation:

- No mutation; may include computed group totals and warnings.

Lifecycle behavior:

- Default should return active/current links.
- Historical/inactive links can be included with `include_inactive=true` if supported later.

Audit expectations:

- No audit event required for normal read unless security policy later requires sensitive access logging.

### `PUT /assets/{asset_id}/beneficiaries/{beneficiary_id}`

Updates an existing link.

Request schema proposal:

```json
{
  "beneficiary_role": "PRIMARY | CONTINGENT | SUCCESSOR | INFORMATIONAL",
  "percentage": 25.0,
  "priority_order": 2,
  "transfer_method": "Trust"
}
```

Response schema: link response object.

Authentication: required.

Ownership enforcement:

- Verify asset ownership.
- Verify beneficiary ownership.
- Verify link exists for that owned asset and owned beneficiary.
- Return 404 for missing or cross-user records.

Allocation validation:

- Recalculate old and new role-group totals.
- Reject totals over `100`.

Lifecycle behavior:

- Reject updates for archived assets.
- Reject updates to inactive/deactivated links unless using a dedicated restoration endpoint in the future.

Audit expectations:

- Update `modified_by` and `updated_at`.
- Future audit event: `asset_beneficiary.link_updated` with old/new non-sensitive metadata.

Phase 2 implementation note: update rejects inactive links with `404`, rejects archived assets/beneficiaries with `400`, rejects deceased beneficiaries with `400`, excludes the target link's old percentage during allocation recalculation, and returns only safe beneficiary summary metadata.

### `POST /assets/{asset_id}/beneficiaries/{beneficiary_id}/deactivate`

Soft-deactivates an existing active link without deleting the join row.

Authentication: required.

Ownership enforcement:

- Verify asset ownership.
- Verify beneficiary ownership.
- Verify link exists for that asset-beneficiary pair.
- Return `404` for missing, inactive, or cross-user records.

Behavior:

- Sets `is_active = false` and `deactivated_at`.
- Preserves role, percentage, transfer method, and historical metadata.
- Updates `modified_by` and `updated_at`.
- Accepts optional `deactivation_reason`; if present, it is encrypted into `deactivation_reason_encrypted` and is never returned by API responses.
- Default GET responses and allocation totals exclude inactive links.

### `DELETE /assets/{asset_id}/beneficiaries/{beneficiary_id}`

Preferred behavior: deactivate/unlink rather than hard delete.

Request schema proposal:

```json
{
  "reason": "User removed beneficiary from planning allocation"
}
```

Response schema proposal:

```json
{
  "id": "string",
  "asset_id": "string",
  "beneficiary_id": "string",
  "status": "Inactive",
  "deactivated_at": "datetime"
}
```

Authentication: required.

Ownership enforcement:

- Verify asset ownership.
- Verify beneficiary ownership.
- Verify link ownership through both parent records.
- Return 404 for missing or cross-user records.

Allocation validation:

- Recalculate role-group totals after deactivation.
- Below-100 totals are allowed but should mark planning as needing review.

Lifecycle behavior:

- Do not hard-delete by default.
- Preserve historical allocation and transfer metadata.
- A future model change may need fields such as `status`, `deactivated_at`, and `deactivation_reason`.

Audit expectations:

- Update `modified_by` and `updated_at`.
- Future audit event: `asset_beneficiary.link_deactivated`.

## 7. Test Plan

Future implementation tests should cover:

1. Owner links their own asset and beneficiary.
2. Cross-user asset reference is blocked with 404.
3. Cross-user beneficiary reference is blocked with 404.
4. Link is only created when asset and beneficiary both belong to current user.
5. Duplicate link for the same asset and beneficiary is rejected.
6. Percentage below `0` is rejected.
7. Percentage above `100` is rejected.
8. Primary percentage totals over `100` are rejected.
9. Contingent percentage totals over `100` are rejected independently of primary totals.
10. Primary and contingent totals are validated separately.
11. Incomplete totals below `100` are allowed during planning.
12. Null percentage behavior is accepted/rejected according to role.
13. Archived beneficiary cannot be newly linked.
14. Deceased beneficiary behavior follows the chosen policy: reject by default or require explicit override.
15. Archived asset cannot receive new links.
16. Owner can update link metadata and allocation.
17. Non-owner cannot update link.
18. Unlink/deactivate preserves historical record.
19. Deactivated links are excluded from default active link lists.
20. Historical link retrieval, if implemented, includes deactivated links without exposing sensitive beneficiary fields.

## 8. Security Risks

- Join rows do not contain `user_id`; every endpoint must verify ownership through both parent records.
- Cross-user IDs could be used for enumeration if error messages differ. Use consistent 404 behavior.
- Link responses could accidentally expose decrypted beneficiary contact information. Default link responses should include only non-sensitive beneficiary summaries.
- Percentage validation implemented only in application code could be bypassed by direct database writes. Database constraints may need strengthening later.
- Current duplicate constraint prevents multiple role links between the same asset and beneficiary. If business rules later require the same beneficiary in multiple roles for the same asset, the unique constraint must be redesigned.
- Hard deletes on parent records can cascade link deletion. API lifecycle behavior should continue using archive/deactivate patterns instead of hard delete.

## 9. Implementation Priorities

1. Use the controlled role constants now defined on the join model: `PRIMARY`, `CONTINGENT`, `SUCCESSOR`, and `INFORMATIONAL`.
2. Use the controlled transfer method constants now defined on the join model: `BENEFICIARY_DESIGNATION`, `WILL`, `TRUST`, `JOINT_OWNERSHIP`, `PROBATE`, and `OTHER`.
3. Use `priority_order` as the canonical integer ordering field. `transfer_priority` is deprecated and retained only for non-destructive compatibility with legacy rows.
4. Build future unlink behavior on `is_active`, `deactivated_at`, and `deactivation_reason_encrypted` instead of hard deletes.
5. Reuse the allocation-total validation service before persisting future link create/update operations.
6. Reuse owner-scoped lookup helpers for asset and beneficiary loading in future routes.
7. Add create/list/update/deactivate endpoints with strict ownership checks.
8. Add audit logging events for create/update/deactivate operations.
9. Add full API tests for ownership, allocation, lifecycle, and historical preservation.