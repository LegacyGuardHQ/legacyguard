from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.asset import ASSET_STATUS_ACTIVE, ASSET_STATUS_ARCHIVED, ASSET_VERIFICATION_VERIFIED, Asset
from app.models.asset_detail import AssetDetail
from app.models.user import User
from app.schemas.assets import AssetCreate, AssetDetailResponse, AssetListResponse, AssetResponse, AssetUpdate
from app.security.auth import get_current_user, get_db
from app.services.asset_creation import create_asset_record

router = APIRouter(prefix="/assets", tags=["assets"])


def _detail_response(detail: AssetDetail | None) -> AssetDetailResponse | None:
    if detail is None:
        return None
    return AssetDetailResponse(
        account_number=detail.get_decrypted_value("account_number_encrypted"),
        policy_number=detail.get_decrypted_value("policy_number_encrypted"),
        notes=detail.get_decrypted_value("notes_encrypted"),
        claim_instructions=detail.get_decrypted_value("claim_instructions_encrypted"),
    )


def _asset_response(asset: Asset, include_details: bool = False) -> AssetResponse:
    return AssetResponse(
        id=asset.id,
        asset_category=asset.asset_category,
        asset_name=asset.asset_name,
        institution=asset.institution,
        description=asset.description,
        estimated_value=asset.estimated_value,
        ownership_type=asset.ownership_type,
        status=asset.status,
        is_verified=asset.is_verified,
        verification_status=asset.verification_status,
        verified_at=asset.verified_at,
        archived_at=asset.archived_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
        details=_detail_response(asset.details) if include_details else None,
    )


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssetResponse:
    asset = create_asset_record(db, user_id=current_user.id, payload=payload)
    return _asset_response(asset, include_details=True)


@router.get("", response_model=list[AssetListResponse])
def list_assets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Asset]:
    return db.query(Asset).filter(Asset.user_id == current_user.id, Asset.archived_at.is_(None)).all()


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssetResponse:
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return _asset_response(asset, include_details=True)


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset(asset_id: str, payload: AssetUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssetResponse:
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    now = datetime.now(timezone.utc)
    for field in ("asset_name", "asset_category", "institution", "description", "estimated_value", "ownership_type", "status"):
        value = getattr(payload, field)
        if value is not None:
            setattr(asset, field, value)
    if payload.is_verified is not None:
        asset.is_verified = payload.is_verified
        if payload.is_verified and asset.verified_at is None:
            asset.verified_at = now
    if payload.verification_status is not None:
        asset.verification_status = payload.verification_status
        if payload.verification_status == ASSET_VERIFICATION_VERIFIED and asset.verified_at is None:
            asset.verified_at = now

    asset.modified_by = current_user.id
    asset.updated_at = now

    if payload.details is not None:
        detail = asset.details or AssetDetail(asset_id=asset.id, created_by=current_user.id)
        detail.modified_by = current_user.id
        detail.set_encrypted_fields(
            account_number=payload.details.account_number,
            policy_number=payload.details.policy_number,
            notes=payload.details.notes,
            claim_instructions=payload.details.claim_instructions,
        )
        db.add(detail)

    db.commit()
    db.refresh(asset)
    return _asset_response(asset, include_details=True)


@router.post("/{asset_id}/archive", response_model=AssetResponse)
def archive_asset(asset_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> AssetResponse:
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    now = datetime.now(timezone.utc)
    asset.status = ASSET_STATUS_ARCHIVED
    asset.archived_at = now
    asset.modified_by = current_user.id
    asset.updated_at = now
    db.commit()
    db.refresh(asset)
    return _asset_response(asset, include_details=True)