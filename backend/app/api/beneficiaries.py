import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.beneficiary import (
    BENEFICIARY_STATUS_ACTIVE,
    BENEFICIARY_STATUS_ARCHIVED,
    BENEFICIARY_STATUS_DECEASED,
    BENEFICIARY_VERIFICATION_NEEDS_REVIEW,
    BENEFICIARY_VERIFICATION_VERIFIED,
    Beneficiary,
)
from app.models.user import User
from app.schemas.beneficiaries import BeneficiaryCreate, BeneficiaryListResponse, BeneficiaryResponse, BeneficiaryUpdate
from app.security.auth import get_current_user, get_db

router = APIRouter(prefix="/beneficiaries", tags=["beneficiaries"])


def _get_owned_beneficiary(db: Session, beneficiary_id: str, user_id: str) -> Beneficiary:
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id, Beneficiary.user_id == user_id).first()
    if beneficiary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")
    return beneficiary


def _beneficiary_response(beneficiary: Beneficiary, include_sensitive: bool = False) -> BeneficiaryResponse:
    return BeneficiaryResponse(
        id=beneficiary.id,
        name=beneficiary.name,
        relationship_type=beneficiary.relationship_type,
        status=beneficiary.status,
        verification_status=beneficiary.verification_status,
        verified_at=beneficiary.verified_at,
        review_due_at=beneficiary.review_due_at,
        is_deceased=beneficiary.is_deceased,
        deceased_at=beneficiary.deceased_at,
        archived_at=beneficiary.archived_at,
        created_at=beneficiary.created_at,
        updated_at=beneficiary.updated_at,
        contact_information=beneficiary.get_decrypted_value("contact_information_encrypted") if include_sensitive else None,
        notes=beneficiary.get_decrypted_value("notes_encrypted") if include_sensitive else None,
    )


@router.post("", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
def create_beneficiary(
    payload: BeneficiaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    now = datetime.now(timezone.utc)
    beneficiary = Beneficiary(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        name=payload.name,
        relationship_type=payload.relationship_type,
        status=BENEFICIARY_STATUS_ACTIVE,
        verification_status=payload.verification_status,
        verified_at=now if payload.verification_status == BENEFICIARY_VERIFICATION_VERIFIED else None,
        review_due_at=payload.review_due_at,
        is_deceased=payload.is_deceased,
        deceased_at=now if payload.is_deceased else None,
        archived_at=None,
        created_at=now,
        updated_at=now,
        created_by=current_user.id,
        modified_by=current_user.id,
    )
    beneficiary.set_encrypted_fields(contact_information=payload.contact_information, notes=payload.notes)
    db.add(beneficiary)
    db.commit()
    db.refresh(beneficiary)
    return _beneficiary_response(beneficiary, include_sensitive=True)


@router.get("", response_model=list[BeneficiaryListResponse])
def list_beneficiaries(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Beneficiary]:
    return db.query(Beneficiary).filter(Beneficiary.user_id == current_user.id, Beneficiary.archived_at.is_(None)).all()


@router.get("/{beneficiary_id}", response_model=BeneficiaryResponse)
def get_beneficiary(
    beneficiary_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    beneficiary = _get_owned_beneficiary(db, beneficiary_id, current_user.id)
    return _beneficiary_response(beneficiary, include_sensitive=True)


@router.put("/{beneficiary_id}", response_model=BeneficiaryResponse)
def update_beneficiary(
    beneficiary_id: str,
    payload: BeneficiaryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    beneficiary = _get_owned_beneficiary(db, beneficiary_id, current_user.id)
    if beneficiary.status == BENEFICIARY_STATUS_ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived beneficiaries cannot be updated")

    now = datetime.now(timezone.utc)
    update_data = payload.model_dump(exclude_unset=True)
    for field in ("name", "relationship_type", "verification_status", "review_due_at", "is_deceased"):
        if field in update_data:
            setattr(beneficiary, field, update_data[field])

    if "contact_information" in update_data:
        beneficiary.set_encrypted_fields(contact_information=update_data["contact_information"])
    if "notes" in update_data:
        beneficiary.set_encrypted_fields(notes=update_data["notes"])

    if "verification_status" in update_data:
        beneficiary.verified_at = now if update_data["verification_status"] == BENEFICIARY_VERIFICATION_VERIFIED else None
    if "is_deceased" in update_data:
        beneficiary.deceased_at = now if update_data["is_deceased"] else None
        if update_data["is_deceased"]:
            beneficiary.status = BENEFICIARY_STATUS_DECEASED
        elif beneficiary.status == BENEFICIARY_STATUS_DECEASED:
            beneficiary.status = BENEFICIARY_STATUS_ACTIVE

    beneficiary.modified_by = current_user.id
    beneficiary.updated_at = now
    db.commit()
    db.refresh(beneficiary)
    return _beneficiary_response(beneficiary, include_sensitive=True)


@router.post("/{beneficiary_id}/archive", response_model=BeneficiaryResponse)
def archive_beneficiary(
    beneficiary_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    beneficiary = _get_owned_beneficiary(db, beneficiary_id, current_user.id)
    if beneficiary.status == BENEFICIARY_STATUS_DECEASED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Deceased beneficiaries cannot be archived")

    now = datetime.now(timezone.utc)
    beneficiary.status = BENEFICIARY_STATUS_ARCHIVED
    beneficiary.archived_at = now
    beneficiary.modified_by = current_user.id
    beneficiary.updated_at = now
    db.commit()
    db.refresh(beneficiary)
    return _beneficiary_response(beneficiary, include_sensitive=True)


@router.post("/{beneficiary_id}/mark-deceased", response_model=BeneficiaryResponse)
def mark_beneficiary_deceased(
    beneficiary_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BeneficiaryResponse:
    beneficiary = _get_owned_beneficiary(db, beneficiary_id, current_user.id)
    if beneficiary.status == BENEFICIARY_STATUS_ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived beneficiaries cannot be marked deceased")

    now = datetime.now(timezone.utc)
    beneficiary.is_deceased = True
    beneficiary.status = BENEFICIARY_STATUS_DECEASED
    beneficiary.deceased_at = now
    beneficiary.verification_status = BENEFICIARY_VERIFICATION_NEEDS_REVIEW
    beneficiary.modified_by = current_user.id
    beneficiary.updated_at = now
    db.commit()
    db.refresh(beneficiary)
    return _beneficiary_response(beneficiary, include_sensitive=True)