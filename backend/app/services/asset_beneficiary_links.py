from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.asset import ASSET_STATUS_ARCHIVED, Asset
from app.models.beneficiary import BENEFICIARY_STATUS_ARCHIVED, Beneficiary
from app.models.user import User


def get_owned_asset_for_linking(db: Session, asset_id: str, current_user: User) -> Asset:
    asset = db.query(Asset).filter(Asset.id == asset_id, Asset.user_id == current_user.id).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


def get_owned_beneficiary_for_linking(db: Session, beneficiary_id: str, current_user: User) -> Beneficiary:
    beneficiary = db.query(Beneficiary).filter(Beneficiary.id == beneficiary_id, Beneficiary.user_id == current_user.id).first()
    if beneficiary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beneficiary not found")
    return beneficiary


def get_owned_asset_and_beneficiary_for_linking(
    db: Session,
    asset_id: str,
    beneficiary_id: str,
    current_user: User,
) -> tuple[Asset, Beneficiary]:
    asset = get_owned_asset_for_linking(db, asset_id, current_user)
    beneficiary = get_owned_beneficiary_for_linking(db, beneficiary_id, current_user)
    return asset, beneficiary


def validate_link_lifecycle_for_mutation(asset: Asset, beneficiary: Beneficiary) -> None:
    if asset.archived_at is not None or asset.status == ASSET_STATUS_ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived assets cannot have beneficiary links updated")
    if beneficiary.archived_at is not None or beneficiary.status == BENEFICIARY_STATUS_ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived beneficiaries cannot have links updated")
    if beneficiary.is_deceased:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deceased beneficiaries cannot be made active recipients through link updates",
        )