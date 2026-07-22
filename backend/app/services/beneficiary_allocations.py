from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.asset_beneficiary import (
    BENEFICIARY_ROLE_CONTINGENT,
    BENEFICIARY_ROLE_INFORMATIONAL,
    BENEFICIARY_ROLE_PRIMARY,
    BENEFICIARY_ROLE_SUCCESSOR,
    BENEFICIARY_ROLE_VALUES,
    AssetBeneficiary,
)


class AllocationValidationError(ValueError):
    pass


ALLOCATED_ROLE_VALUES = {
    BENEFICIARY_ROLE_PRIMARY,
    BENEFICIARY_ROLE_CONTINGENT,
    BENEFICIARY_ROLE_SUCCESSOR,
}


@dataclass(frozen=True)
class AllocationValidationResult:
    role: str
    total: Decimal
    is_complete: bool


def validate_beneficiary_role(role: str) -> str:
    if role not in BENEFICIARY_ROLE_VALUES:
        raise AllocationValidationError("Unsupported beneficiary role")
    return role


def validate_individual_percentage(percentage: Decimal | float | int | None) -> Decimal | None:
    if percentage is None:
        return None
    value = Decimal(str(percentage))
    if value < Decimal("0") or value > Decimal("100"):
        raise AllocationValidationError("Percentage must be between 0 and 100")
    return value


def calculate_active_role_total(
    links: list[AssetBeneficiary],
    role: str,
    *,
    proposed_link_id: str | None = None,
    proposed_percentage: Decimal | float | int | None = None,
) -> Decimal:
    validate_beneficiary_role(role)
    if role == BENEFICIARY_ROLE_INFORMATIONAL:
        return Decimal("0")

    total = Decimal("0")
    proposed_value = validate_individual_percentage(proposed_percentage)
    if proposed_link_id is None and proposed_value is not None:
        total += proposed_value
    for link in links:
        if link.is_active is False or link.beneficiary_role != role:
            continue
        if proposed_link_id is not None and link.id == proposed_link_id:
            if proposed_value is not None:
                total += proposed_value
            continue
        if link.percentage is not None:
            total += Decimal(str(link.percentage))
    return total


def validate_active_role_total(
    links: list[AssetBeneficiary],
    role: str,
    *,
    proposed_link_id: str | None = None,
    proposed_percentage: Decimal | float | int | None = None,
) -> AllocationValidationResult:
    total = calculate_active_role_total(
        links,
        role,
        proposed_link_id=proposed_link_id,
        proposed_percentage=proposed_percentage,
    )
    if total > Decimal("100"):
        raise AllocationValidationError(f"{role} allocation total cannot exceed 100")
    return AllocationValidationResult(role=role, total=total, is_complete=total == Decimal("100"))


def validate_asset_allocation_change(
    db: Session,
    asset_id: str,
    role: str,
    percentage: Decimal | float | int | None,
    *,
    link_id: str | None = None,
) -> AllocationValidationResult:
    validate_beneficiary_role(role)
    validate_individual_percentage(percentage)
    if role == BENEFICIARY_ROLE_INFORMATIONAL:
        return AllocationValidationResult(role=role, total=Decimal("0"), is_complete=False)

    links = db.query(AssetBeneficiary).filter(AssetBeneficiary.asset_id == asset_id).all()
    return validate_active_role_total(links, role, proposed_link_id=link_id, proposed_percentage=percentage)