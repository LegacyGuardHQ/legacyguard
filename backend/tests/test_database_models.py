import os
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.database.connection import Base, engine
from app.models.asset import ASSET_STATUS_ARCHIVED, ASSET_VERIFICATION_VERIFIED, Asset
from app.models.asset_beneficiary import (
    BENEFICIARY_ROLE_CONTINGENT,
    BENEFICIARY_ROLE_INFORMATIONAL,
    BENEFICIARY_ROLE_PRIMARY,
    TRANSFER_METHOD_BENEFICIARY_DESIGNATION,
    TRANSFER_METHOD_JOINT_OWNERSHIP,
    TRANSFER_METHOD_OTHER,
    TRANSFER_METHOD_PROBATE,
    TRANSFER_METHOD_TRUST,
    TRANSFER_METHOD_WILL,
    TRANSFER_METHOD_VALUES,
    AssetBeneficiary,
)
from app.models.asset_detail import AssetDetail
from app.models.beneficiary import BENEFICIARY_STATUS_DECEASED, BENEFICIARY_VERIFICATION_VERIFIED, Beneficiary
from app.models.contact import Contact
from app.models.document import Document
from app.models.report import Report
from app.models.task import Task
from app.models.user import User
from app.services.beneficiary_allocations import AllocationValidationError, validate_active_role_total, validate_beneficiary_role
from app.services.document_content_encryption import document_content_encryption_service
from app.services.document_storage import DocumentStorageError, LocalDocumentStorage
from app.services.document_validation import DocumentValidationError, validate_document_size, validate_extension_and_mime
from app.services.encryption import encryption_service


@pytest.fixture(autouse=True)
def reset_db() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def _create_user(db: Session, email: str) -> User:
    user = User(id=f"user-{email}", email=email, password_hash="hash", role="USER")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_user_can_create_assets() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "owner@example.com")
        asset = Asset(
            id="asset-1",
            user_id=user.id,
            asset_category="Bank Account",
            asset_name="Checking Account",
            institution="Example Bank",
            description="Primary spending account",
            estimated_value=2500.0,
            ownership_type="Joint",
            status="Active",
            created_by=user.id,
            modified_by=user.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)

        persisted = db.query(Asset).filter(Asset.user_id == user.id).first()
        assert persisted is not None
        assert persisted.asset_name == "Checking Account"
    finally:
        db.close()


def test_user_can_only_access_owned_assets() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        owner_a = _create_user(db, "a@example.com")
        owner_b = _create_user(db, "b@example.com")

        db.add_all(
            [
                Asset(
                    id="asset-a",
                    user_id=owner_a.id,
                    asset_category="Investment",
                    asset_name="Retirement",
                    institution="Broker",
                    estimated_value=10000.0,
                    ownership_type="Individual",
                    status="Active",
                    created_by=owner_a.id,
                    modified_by=owner_a.id,
                ),
                Asset(
                    id="asset-b",
                    user_id=owner_b.id,
                    asset_category="Bank Account",
                    asset_name="Savings",
                    institution="Bank",
                    estimated_value=5000.0,
                    ownership_type="Individual",
                    status="Active",
                    created_by=owner_b.id,
                    modified_by=owner_b.id,
                ),
            ]
        )
        db.commit()

        assets = db.query(Asset).filter(Asset.user_id == owner_a.id).all()
        assert len(assets) == 1
        assert assets[0].asset_name == "Retirement"
    finally:
        db.close()


def test_beneficiary_relationships_work() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "beneficiary@example.com")
        asset = Asset(
            id="asset-2",
            user_id=user.id,
            asset_category="Insurance Policy",
            asset_name="Life Insurance",
            institution="Example Insurer",
            estimated_value=50000.0,
            ownership_type="Individual",
            status="Active",
            created_by=user.id,
            modified_by=user.id,
        )
        beneficiary = Beneficiary(id="benef-1", user_id=user.id, name="Spouse", relationship_type="Spouse")
        db.add_all([asset, beneficiary])
        db.commit()

        link = AssetBeneficiary(
            asset_id=asset.id,
            beneficiary_id=beneficiary.id,
            percentage=50.0,
            beneficiary_role="PRIMARY",
            priority_order=1,
            transfer_priority=1,
            transfer_method=TRANSFER_METHOD_BENEFICIARY_DESIGNATION,
            created_by=user.id,
            modified_by=user.id,
        )
        db.add(link)
        db.commit()

        relation = db.query(AssetBeneficiary).filter(AssetBeneficiary.asset_id == asset.id).one()
        assert relation.beneficiary_id == beneficiary.id
        assert relation.beneficiary_role == "PRIMARY"
        assert relation.priority_order == 1
        assert relation.transfer_method == TRANSFER_METHOD_BENEFICIARY_DESIGNATION
    finally:
        db.close()


def test_beneficiary_encrypted_fields_and_lifecycle_support() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "beneficiary-secure@example.com")
        beneficiary = Beneficiary(
            id="benef-secure",
            user_id=user.id,
            name="Secure Beneficiary",
            relationship_type="Spouse",
            status=BENEFICIARY_STATUS_DECEASED,
            verification_status=BENEFICIARY_VERIFICATION_VERIFIED,
            verified_at=datetime.now(timezone.utc),
            review_due_at=datetime.now(timezone.utc),
            is_deceased=True,
            deceased_at=datetime.now(timezone.utc),
            archived_at=None,
            created_by=user.id,
            modified_by=user.id,
        )
        beneficiary.set_encrypted_fields(contact_information="secure@example.com", notes="Sensitive beneficiary note")
        db.add(beneficiary)
        db.commit()
        db.refresh(beneficiary)

        assert beneficiary.contact_information_encrypted != "secure@example.com"
        assert beneficiary.notes_encrypted != "Sensitive beneficiary note"
        assert beneficiary.get_decrypted_value("contact_information_encrypted") == "secure@example.com"
        assert beneficiary.get_decrypted_value("notes_encrypted") == "Sensitive beneficiary note"
        assert beneficiary.status == BENEFICIARY_STATUS_DECEASED
        assert beneficiary.verification_status == BENEFICIARY_VERIFICATION_VERIFIED
        assert beneficiary.is_deceased is True
        assert beneficiary.deceased_at is not None
    finally:
        db.close()


def test_asset_beneficiary_constraints_prevent_duplicates_and_invalid_percentages() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "beneficiary-constraints@example.com")
        asset = Asset(id="asset-constraints", user_id=user.id, asset_category="Bank Account", asset_name="Checking", status="Active")
        beneficiary = Beneficiary(id="benef-constraints", user_id=user.id, name="Beneficiary", relationship_type="Spouse")
        db.add_all([asset, beneficiary])
        db.commit()

        db.add(AssetBeneficiary(asset_id=asset.id, beneficiary_id=beneficiary.id, percentage=50.0, beneficiary_role="PRIMARY"))
        db.commit()

        db.add(AssetBeneficiary(asset_id=asset.id, beneficiary_id=beneficiary.id, percentage=25.0, beneficiary_role="CONTINGENT"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        other = Beneficiary(id="benef-invalid-percent", user_id=user.id, name="Other", relationship_type="Child")
        db.add(other)
        db.commit()
        db.add(AssetBeneficiary(asset_id=asset.id, beneficiary_id=other.id, percentage=101.0, beneficiary_role="PRIMARY"))
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.close()


def test_documents_link_correctly() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "docs@example.com")
        asset = Asset(
            id="asset-3",
            user_id=user.id,
            asset_category="Bank Account",
            asset_name="Investment Account",
            institution="Example Bank",
            estimated_value=12000.0,
            ownership_type="Individual",
            status="Active",
            created_by=user.id,
            modified_by=user.id,
        )
        db.add(asset)
        db.commit()

        beneficiary = Beneficiary(id="benef-doc-1", user_id=user.id, name="Document Beneficiary", relationship_type="Spouse")
        db.add(beneficiary)
        db.commit()

        document = Document(
            id="doc-1",
            user_id=user.id,
            asset_id=asset.id,
            beneficiary_id=beneficiary.id,
            document_type="ACCOUNT_STATEMENT",
            document_name="January Statement",
            original_filename="statement.pdf",
            mime_type="application/pdf",
            file_size=128,
            checksum_sha256="abc123",
            encrypted=True,
            created_by=user.id,
            modified_by=user.id,
        )
        document.set_storage_reference("local://private/path/doc-1")
        document.set_description("Sensitive document description")
        document.set_encryption_key_reference("development-key-reference")
        db.add(document)
        db.commit()

        saved = db.query(Document).filter(Document.asset_id == asset.id).one()
        assert saved.document_name == "January Statement"
        assert saved.asset_id == asset.id
        assert saved.beneficiary_id == beneficiary.id
        assert saved.storage_reference is None
        assert saved.storage_reference_encrypted != "local://private/path/doc-1"
        assert saved.get_storage_reference() == "local://private/path/doc-1"
        assert saved.description_encrypted != "Sensitive document description"
        assert saved.get_description() == "Sensitive document description"
        assert saved.encryption_key_reference_encrypted != "development-key-reference"
        assert saved.get_encryption_key_reference() == "development-key-reference"
        assert saved.status == "ACTIVE"
        assert saved.verification_status == "UNKNOWN"
        assert saved.version_number == 1
    finally:
        db.close()


def test_document_archive_and_version_fields_work() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "document-version@example.com")
        replacement = Document(id="doc-replacement", user_id=user.id, document_type="WILL", document_name="Will v2", version_number=2)
        original = Document(
            id="doc-original",
            user_id=user.id,
            document_type="WILL",
            document_name="Will v1",
            status="REPLACED",
            verification_status="REPLACED",
            archived_at=datetime.now(timezone.utc),
            replaced_by_document_id=replacement.id,
            version_number=1,
        )
        db.add_all([replacement, original])
        db.commit()
        saved = db.query(Document).filter(Document.id == original.id).one()
        assert saved.status == "REPLACED"
        assert saved.archived_at is not None
        assert saved.replaced_by_document_id == replacement.id
        assert saved.replaced_by_document.id == replacement.id
    finally:
        db.close()


def test_document_content_encryption_round_trip_and_not_plaintext() -> None:
    document_id = "550e8400-e29b-41d4-a716-446655440000"
    plaintext = b"sensitive estate planning document bytes"

    encrypted = document_content_encryption_service.encrypt(document_id, plaintext)

    assert encrypted.encrypted_bytes != plaintext
    assert plaintext not in encrypted.encrypted_bytes
    assert encrypted.encrypted_key_reference
    assert document_content_encryption_service.decrypt(document_id, encrypted.encrypted_bytes, encrypted.encrypted_key_reference) == plaintext


def test_local_document_storage_uses_opaque_paths_and_rejects_traversal(tmp_path) -> None:
    storage = LocalDocumentStorage(tmp_path / "document-storage")
    document_id = "550e8400-e29b-41d4-a716-446655440001"
    encrypted_bytes = b"encrypted bytes only"

    reference = storage.save_encrypted(document_id, encrypted_bytes)

    assert "550e8400" not in reference
    assert reference.endswith(".lgdoc")
    assert storage.exists(document_id) is True
    assert storage.read_encrypted(document_id) == encrypted_bytes
    with pytest.raises(DocumentStorageError):
        storage.save_encrypted("../evil", encrypted_bytes)


def test_document_validation_rejects_oversized_and_invalid_files() -> None:
    assert validate_document_size(1024) == 1024
    with pytest.raises(DocumentValidationError):
        validate_document_size(20 * 1024 * 1024 + 1)
    with pytest.raises(DocumentValidationError):
        validate_extension_and_mime("statement.pdf.exe", "application/pdf")
    with pytest.raises(DocumentValidationError):
        validate_extension_and_mime("statement.pdf", "image/png")
    assert validate_extension_and_mime("statement.pdf", "application/pdf") == ("statement.pdf", ".pdf")


def test_encryption_fields_function() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "encrypt@example.com")
        asset = Asset(
            id="asset-4",
            user_id=user.id,
            asset_category="Insurance Policy",
            asset_name="Life Insurance",
            institution="Insurer",
            estimated_value=60000.0,
            ownership_type="Individual",
            status="Active",
            created_by=user.id,
            modified_by=user.id,
        )
        db.add(asset)
        db.commit()

        detail = AssetDetail(asset_id=asset.id)
        detail.set_encrypted_fields(
            account_number="1234",
            policy_number="POL-1",
            notes="Keep secure",
            claim_instructions="Call insurer with policy number",
        )
        db.add(detail)
        db.commit()
        db.refresh(detail)

        assert detail.get_decrypted_value("account_number_encrypted") == "1234"
        assert detail.get_decrypted_value("policy_number_encrypted") == "POL-1"
        assert detail.get_decrypted_value("notes_encrypted") == "Keep secure"
        assert detail.get_decrypted_value("claim_instructions_encrypted") == "Call insurer with policy number"
        assert detail.claim_instructions_encrypted != "Call insurer with policy number"
    finally:
        db.close()


def test_asset_has_one_detail_relationship_and_preparation_fields() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "prepared@example.com")
        asset = Asset(
            id="asset-prepared",
            user_id=user.id,
            asset_category="Insurance Policy",
            asset_name="Prepared Policy",
            institution="Insurer",
            estimated_value=100000.0,
            ownership_type="Individual",
            status="Active",
            is_verified=True,
            verification_status=ASSET_VERIFICATION_VERIFIED,
            verified_at=datetime.now(timezone.utc),
            archived_at=None,
            created_by=user.id,
            modified_by=user.id,
        )
        detail = AssetDetail(asset_id=asset.id)
        detail.set_encrypted_fields(claim_instructions="Submit claim form to insurer")
        db.add(asset)
        db.add(detail)
        db.commit()

        saved = db.query(Asset).filter(Asset.id == asset.id).one()
        assert saved.details is not None
        assert saved.details.asset_id == asset.id
        assert saved.details.get_decrypted_value("claim_instructions_encrypted") == "Submit claim form to insurer"
        assert saved.is_verified is True
        assert saved.verification_status == ASSET_VERIFICATION_VERIFIED
        assert saved.verified_at is not None
        assert saved.archived_at is None
    finally:
        db.close()


def test_asset_soft_archive_uses_status_and_archived_at() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "archive@example.com")
        asset = Asset(
            id="asset-archive",
            user_id=user.id,
            asset_category="Bank Account",
            asset_name="Archived Checking",
            status="Active",
        )
        db.add(asset)
        db.commit()

        asset.status = ASSET_STATUS_ARCHIVED
        asset.archived_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(asset)

        assert asset.status == ASSET_STATUS_ARCHIVED
        assert asset.archived_at is not None
    finally:
        db.close()


def test_asset_beneficiary_controlled_roles_and_transfer_methods() -> None:
    assert validate_beneficiary_role(BENEFICIARY_ROLE_PRIMARY) == BENEFICIARY_ROLE_PRIMARY
    assert validate_beneficiary_role(BENEFICIARY_ROLE_CONTINGENT) == BENEFICIARY_ROLE_CONTINGENT
    assert validate_beneficiary_role(BENEFICIARY_ROLE_INFORMATIONAL) == BENEFICIARY_ROLE_INFORMATIONAL
    with pytest.raises(AllocationValidationError):
        validate_beneficiary_role("UNSUPPORTED")

    assert TRANSFER_METHOD_VALUES == {
        TRANSFER_METHOD_BENEFICIARY_DESIGNATION,
        TRANSFER_METHOD_WILL,
        TRANSFER_METHOD_TRUST,
        TRANSFER_METHOD_JOINT_OWNERSHIP,
        TRANSFER_METHOD_PROBATE,
        TRANSFER_METHOD_OTHER,
    }


def test_asset_beneficiary_priority_and_deactivation_fields() -> None:
    from app.database.connection import SessionLocal

    db = SessionLocal()
    try:
        user = _create_user(db, "link-lifecycle@example.com")
        asset = Asset(id="asset-link-life", user_id=user.id, asset_category="Bank Account", asset_name="Checking", status="Active")
        beneficiary = Beneficiary(id="benef-link-life", user_id=user.id, name="Beneficiary", relationship_type="Spouse")
        db.add_all([asset, beneficiary])
        db.commit()

        link = AssetBeneficiary(
            asset_id=asset.id,
            beneficiary_id=beneficiary.id,
            percentage=25,
            beneficiary_role=BENEFICIARY_ROLE_PRIMARY,
            priority_order=2,
            is_active=False,
            deactivated_at=datetime.now(timezone.utc),
        )
        link.set_deactivation_reason("Sensitive deactivation reason")
        db.add(link)
        db.commit()
        db.refresh(link)

        assert link.priority_order == 2
        assert link.is_active is False
        assert link.deactivated_at is not None
        assert link.deactivation_reason_encrypted != "Sensitive deactivation reason"
        assert link.get_deactivation_reason() == "Sensitive deactivation reason"
    finally:
        db.close()


def test_primary_allocation_totals_cannot_exceed_100() -> None:
    links = [
        AssetBeneficiary(id="link-1", asset_id="asset", beneficiary_id="benef-1", percentage=60, beneficiary_role=BENEFICIARY_ROLE_PRIMARY),
        AssetBeneficiary(id="link-2", asset_id="asset", beneficiary_id="benef-2", percentage=41, beneficiary_role=BENEFICIARY_ROLE_PRIMARY),
    ]

    with pytest.raises(AllocationValidationError):
        validate_active_role_total(links, BENEFICIARY_ROLE_PRIMARY)


def test_contingent_allocation_totals_are_validated_separately() -> None:
    links = [
        AssetBeneficiary(id="link-1", asset_id="asset", beneficiary_id="benef-1", percentage=100, beneficiary_role=BENEFICIARY_ROLE_PRIMARY),
        AssetBeneficiary(id="link-2", asset_id="asset", beneficiary_id="benef-2", percentage=100, beneficiary_role=BENEFICIARY_ROLE_CONTINGENT),
    ]

    primary = validate_active_role_total(links, BENEFICIARY_ROLE_PRIMARY)
    contingent = validate_active_role_total(links, BENEFICIARY_ROLE_CONTINGENT)

    assert primary.total == 100
    assert primary.is_complete is True
    assert contingent.total == 100
    assert contingent.is_complete is True


def test_informational_and_inactive_links_do_not_count_toward_totals() -> None:
    links = [
        AssetBeneficiary(id="link-1", asset_id="asset", beneficiary_id="benef-1", percentage=100, beneficiary_role=BENEFICIARY_ROLE_PRIMARY),
        AssetBeneficiary(id="link-2", asset_id="asset", beneficiary_id="benef-2", percentage=100, beneficiary_role=BENEFICIARY_ROLE_INFORMATIONAL),
        AssetBeneficiary(id="link-3", asset_id="asset", beneficiary_id="benef-3", percentage=100, beneficiary_role=BENEFICIARY_ROLE_PRIMARY, is_active=False),
    ]

    primary = validate_active_role_total(links, BENEFICIARY_ROLE_PRIMARY)
    informational = validate_active_role_total(links, BENEFICIARY_ROLE_INFORMATIONAL)

    assert primary.total == 100
    assert informational.total == 0
