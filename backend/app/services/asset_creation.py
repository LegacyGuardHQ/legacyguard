import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.asset import (
    ASSET_STATUS_ACTIVE,
    ASSET_VERIFICATION_NEEDS_REVIEW,
    Asset,
)
from app.models.asset_detail import AssetDetail
from app.schemas.assets import AssetCreate


def create_asset_record(
    db: Session,
    *,
    user_id: str,
    payload: AssetCreate,
    require_manual_verification: bool = False,
    commit: bool = True,
) -> Asset:
    """Create an asset using the application's normal encryption and ownership rules.

    Discovery conversions use ``require_manual_verification`` so a confirmed finding
    never becomes a verified ownership claim merely because the user created an
    inventory record from it.
    """
    now = datetime.now(timezone.utc)
    is_verified = False if require_manual_verification else payload.is_verified
    verification_status = (
        ASSET_VERIFICATION_NEEDS_REVIEW
        if require_manual_verification
        else payload.verification_status
    )

    asset = Asset(
        id=str(uuid.uuid4()),
        user_id=user_id,
        asset_category=payload.asset_category,
        asset_name=payload.asset_name,
        institution=payload.institution,
        description=payload.description,
        estimated_value=payload.estimated_value,
        ownership_type=payload.ownership_type,
        status=payload.status or ASSET_STATUS_ACTIVE,
        is_verified=is_verified,
        verification_status=verification_status,
        verified_at=now if is_verified else None,
        created_at=now,
        updated_at=now,
        created_by=user_id,
        modified_by=user_id,
    )
    db.add(asset)

    if payload.details is not None:
        detail = AssetDetail(asset_id=asset.id, created_by=user_id, modified_by=user_id)
        detail.set_encrypted_fields(
            account_number=payload.details.account_number,
            policy_number=payload.details.policy_number,
            notes=payload.details.notes,
            claim_instructions=payload.details.claim_instructions,
        )
        db.add(detail)

    if commit:
        db.commit()
        db.refresh(asset)
    else:
        db.flush()
    return asset
