import os

import pytest
from pydantic import ValidationError

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.models.asset import (
    ASSET_STATUS_ACTIVE,
    ASSET_STATUS_ARCHIVED,
    ASSET_VERIFICATION_NEEDS_REVIEW,
    ASSET_VERIFICATION_UNKNOWN,
    ASSET_VERIFICATION_VERIFIED,
)
from app.schemas.legacy import AssetCreate, BeneficiaryCreate, DocumentCreate


def test_asset_create_trims_whitespace_and_defaults() -> None:
    asset = AssetCreate(asset_name="  Checking  ", asset_category="  Bank Account  ")
    assert asset.asset_name == "Checking"
    assert asset.asset_category == "Bank Account"
    assert asset.verification_status == ASSET_VERIFICATION_UNKNOWN
    assert asset.is_verified is False


def test_asset_create_rejects_whitespace_only_name() -> None:
    with pytest.raises(ValidationError, match="Asset name is required"):
        AssetCreate(asset_name="   ", asset_category="Bank Account")


def test_asset_create_rejects_whitespace_only_category() -> None:
    with pytest.raises(ValidationError, match="Asset category is required"):
        AssetCreate(asset_name="Checking", asset_category="   ")


def test_asset_create_accepts_allowed_verification_statuses() -> None:
    for status in (ASSET_VERIFICATION_VERIFIED, ASSET_VERIFICATION_NEEDS_REVIEW):
        asset = AssetCreate(asset_name="Checking", asset_category="Bank", verification_status=status)
        assert asset.verification_status == status


def test_asset_create_accepts_allowed_status_values() -> None:
    for status in (ASSET_STATUS_ACTIVE, ASSET_STATUS_ARCHIVED):
        asset = AssetCreate(asset_name="Checking", asset_category="Bank", status=status)
        assert asset.status == status


def test_asset_create_rejects_unknown_verification_status() -> None:
    with pytest.raises(ValidationError, match="Input should be 'UNKNOWN', 'VERIFIED', 'NEEDS_REVIEW' or 'CLOSED'"):
        AssetCreate(asset_name="Checking", asset_category="Bank", verification_status="bogus")


def test_beneficiary_create_trims_whitespace() -> None:
    beneficiary = BeneficiaryCreate(name="  Jane  ", relationship_type="  Spouse  ")
    assert beneficiary.name == "Jane"
    assert beneficiary.relationship_type == "Spouse"


def test_beneficiary_create_rejects_whitespace_only_name() -> None:
    with pytest.raises(ValidationError, match="Beneficiary name is required"):
        BeneficiaryCreate(name="   ", relationship_type="Spouse")


def test_beneficiary_create_rejects_whitespace_only_relationship() -> None:
    with pytest.raises(ValidationError, match="Relationship is required"):
        BeneficiaryCreate(name="Jane", relationship_type="   ")


def test_document_create_accepts_allowed_type() -> None:
    document = DocumentCreate(document_type="Will", document_name="my-will.pdf")
    assert document.document_type == "Will"


def test_document_create_rejects_unsupported_type() -> None:
    with pytest.raises(ValidationError, match="Unsupported document type"):
        DocumentCreate(document_type="Random", document_name="file.pdf")
