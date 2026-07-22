import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.asset_beneficiary import AssetBeneficiary
from app.models.user import User
from app.schemas.asset_beneficiaries import (
    AssetBeneficiaryCreate,
    AssetBeneficiaryDeactivateRequest,
    AssetBeneficiaryDeactivateResponse,
    AssetBeneficiaryResponse,
    AssetBeneficiaryUpdate,
    LinkedBeneficiaryMetadata,
)
from app.security.auth import get_current_user, get_db
from app.services.asset_beneficiary_links import (
    get_owned_asset_and_beneficiary_for_linking,
    get_owned_asset_for_linking,
    validate_link_lifecycle_for_mutation,
)
from app.services.beneficiary_allocations import AllocationValidationError, validate_asset_allocation_change

router = APIRouter(prefix="/assets", tags=["asset-beneficiaries"])


def _link_response(link: AssetBeneficiary) -> AssetBeneficiaryResponse:
    beneficiary = link.beneficiary
    return AssetBeneficiaryResponse(
        id=link.id,
        asset_id=link.asset_id,
        beneficiary=LinkedBeneficiaryMetadata(
            id=beneficiary.id,
            name=beneficiary.name,
            relationship_type=beneficiary.relationship_type,
            status=beneficiary.status,
            verification_status=beneficiary.verification_status,
            is_deceased=beneficiary.is_deceased,
        ),
        beneficiary_role=link.beneficiary_role,
        percentage=link.percentage,
        priority_order=link.priority_order,
        transfer_method=link.transfer_method,
        created_at=link.created_at,
        updated_at=link.updated_at,
    )


def _get_owned_link_for_pair(db: Session, asset_id: str, beneficiary_id: str) -> AssetBeneficiary:
    link = (
        db.query(AssetBeneficiary)
        .options(joinedload(AssetBeneficiary.beneficiary))
        .filter(AssetBeneficiary.asset_id == asset_id, AssetBeneficiary.beneficiary_id == beneficiary_id)
        .first()
    )
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset-beneficiary link not found")
    return link


@router.post("/{asset_id}/beneficiaries", response_model=AssetBeneficiaryResponse, status_code=status.HTTP_201_CREATED)
def create_asset_beneficiary_link(
    asset_id: str,
    payload: AssetBeneficiaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetBeneficiaryResponse:
    asset, beneficiary = get_owned_asset_and_beneficiary_for_linking(db, asset_id, payload.beneficiary_id, current_user)
    validate_link_lifecycle_for_mutation(asset, beneficiary)

    existing = (
        db.query(AssetBeneficiary)
        .filter(
            AssetBeneficiary.asset_id == asset_id,
            AssetBeneficiary.beneficiary_id == payload.beneficiary_id,
        )
        .first()
    )

    if existing is not None and existing.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Active asset-beneficiary link already exists")

    try:
        validate_asset_allocation_change(db, asset_id, payload.beneficiary_role, payload.percentage)
    except AllocationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    if existing is not None:
        link = existing
        link.beneficiary_role = payload.beneficiary_role
        link.percentage = payload.percentage
        link.priority_order = payload.priority_order
        link.transfer_method = payload.transfer_method
        link.is_active = True
        link.deactivated_at = None
        link.deactivation_reason_encrypted = None
        link.updated_at = now
        link.modified_by = current_user.id
    else:
        link = AssetBeneficiary(
            id=str(uuid.uuid4()),
            asset_id=asset_id,
            beneficiary_id=payload.beneficiary_id,
            beneficiary_role=payload.beneficiary_role,
            percentage=payload.percentage,
            priority_order=payload.priority_order,
            transfer_method=payload.transfer_method,
            is_active=True,
            created_at=now,
            updated_at=now,
            created_by=current_user.id,
            modified_by=current_user.id,
        )
        db.add(link)
    db.commit()
    db.refresh(link)
    link = (
        db.query(AssetBeneficiary)
        .options(joinedload(AssetBeneficiary.beneficiary))
        .filter(AssetBeneficiary.id == link.id)
        .one()
    )
    return _link_response(link)


@router.get("/{asset_id}/beneficiaries", response_model=list[AssetBeneficiaryResponse])
def list_asset_beneficiary_links(
    asset_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssetBeneficiaryResponse]:
    get_owned_asset_for_linking(db, asset_id, current_user)
    links = (
        db.query(AssetBeneficiary)
        .options(joinedload(AssetBeneficiary.beneficiary))
        .filter(AssetBeneficiary.asset_id == asset_id, AssetBeneficiary.is_active.is_(True))
        .order_by(AssetBeneficiary.priority_order.asc().nullslast(), AssetBeneficiary.created_at.asc())
        .all()
    )
    return [_link_response(link) for link in links]


@router.put("/{asset_id}/beneficiaries/{beneficiary_id}", response_model=AssetBeneficiaryResponse)
def update_asset_beneficiary_link(
    asset_id: str,
    beneficiary_id: str,
    payload: AssetBeneficiaryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetBeneficiaryResponse:
    asset, beneficiary = get_owned_asset_and_beneficiary_for_linking(db, asset_id, beneficiary_id, current_user)
    validate_link_lifecycle_for_mutation(asset, beneficiary)
    link = _get_owned_link_for_pair(db, asset_id, beneficiary_id)
    if not link.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset-beneficiary link not found")

    try:
        validate_asset_allocation_change(db, asset_id, payload.beneficiary_role, payload.percentage, link_id=link.id)
    except AllocationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    link.beneficiary_role = payload.beneficiary_role
    link.percentage = payload.percentage
    link.priority_order = payload.priority_order
    link.transfer_method = payload.transfer_method
    link.modified_by = current_user.id
    link.updated_at = now
    db.commit()
    db.refresh(link)
    link = (
        db.query(AssetBeneficiary)
        .options(joinedload(AssetBeneficiary.beneficiary))
        .filter(AssetBeneficiary.id == link.id)
        .one()
    )
    return _link_response(link)


@router.post("/{asset_id}/beneficiaries/{beneficiary_id}/deactivate", response_model=AssetBeneficiaryDeactivateResponse)
def deactivate_asset_beneficiary_link(
    asset_id: str,
    beneficiary_id: str,
    payload: AssetBeneficiaryDeactivateRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssetBeneficiaryDeactivateResponse:
    get_owned_asset_and_beneficiary_for_linking(db, asset_id, beneficiary_id, current_user)
    link = _get_owned_link_for_pair(db, asset_id, beneficiary_id)
    if not link.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset-beneficiary link not found")

    now = datetime.now(timezone.utc)
    link.is_active = False
    link.deactivated_at = now
    link.modified_by = current_user.id
    link.updated_at = now
    if payload is not None and payload.deactivation_reason:
        link.set_deactivation_reason(payload.deactivation_reason)
    db.commit()
    db.refresh(link)
    return AssetBeneficiaryDeactivateResponse(
        id=link.id,
        asset_id=link.asset_id,
        beneficiary_id=link.beneficiary_id,
        is_active=link.is_active,
        deactivated_at=link.deactivated_at,
    )