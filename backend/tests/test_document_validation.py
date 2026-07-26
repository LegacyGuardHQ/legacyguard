import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "dev-secret-key-123456")
os.environ.setdefault("ENCRYPTION_KEY", "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE=")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret-123456")
os.environ.setdefault("ENVIRONMENT", "testing")

from app.services.document_validation import (
    DocumentValidationError,
    MalwareScanner,
    calculate_checksum_sha256,
    normalize_display_filename,
    validate_document_size,
    validate_extension_and_mime,
    validate_magic_bytes,
)


def test_malware_scanner_hook_is_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        MalwareScanner().scan(b"content")


def test_validate_document_size_accepts_valid_and_rejects_bounds() -> None:
    assert validate_document_size(1024) == 1024

    with pytest.raises(DocumentValidationError, match="empty"):
        validate_document_size(0)

    with pytest.raises(DocumentValidationError, match="maximum size"):
        validate_document_size(20 * 1024 * 1024 + 1)


def test_normalize_display_filename_strips_and_validates() -> None:
    assert normalize_display_filename("  report.pdf  ") == "report.pdf"


def test_normalize_display_filename_requires_non_empty() -> None:
    with pytest.raises(DocumentValidationError, match="required"):
        normalize_display_filename("   ")


def test_normalize_display_filename_rejects_path_components() -> None:
    with pytest.raises(DocumentValidationError, match="path components"):
        normalize_display_filename("../secret.pdf")

    with pytest.raises(DocumentValidationError, match="path components"):
        normalize_display_filename("dir\\secret.pdf")


def test_normalize_display_filename_rejects_dot_names() -> None:
    with pytest.raises(DocumentValidationError, match="Invalid filename"):
        normalize_display_filename("..")


def test_normalize_display_filename_rejects_overly_long_names() -> None:
    with pytest.raises(DocumentValidationError, match="too long"):
        normalize_display_filename("a" * 256 + ".pdf")


def test_validate_extension_and_mime_accepts_matching_pair() -> None:
    display_name, extension = validate_extension_and_mime("report.pdf", "application/pdf")
    assert display_name == "report.pdf"
    assert extension == ".pdf"


def test_validate_extension_and_mime_rejects_missing_extension() -> None:
    with pytest.raises(DocumentValidationError, match="extension is required"):
        validate_extension_and_mime("report", "application/pdf")


def test_validate_extension_and_mime_rejects_dangerous_extension() -> None:
    with pytest.raises(DocumentValidationError, match="dangerous"):
        validate_extension_and_mime("malware.exe", "application/pdf")


def test_validate_extension_and_mime_rejects_double_extension() -> None:
    with pytest.raises(DocumentValidationError, match="Double extensions"):
        validate_extension_and_mime("report.pdf.txt", "text/plain")


def test_validate_extension_and_mime_rejects_unsupported_extension() -> None:
    with pytest.raises(DocumentValidationError, match="Unsupported document extension"):
        validate_extension_and_mime("archive.gz", "application/pdf")


def test_validate_extension_and_mime_rejects_unsupported_mime() -> None:
    with pytest.raises(DocumentValidationError, match="Unsupported document MIME type"):
        validate_extension_and_mime("report.pdf", "application/x-evil")


def test_validate_extension_and_mime_rejects_mismatched_extension_and_mime() -> None:
    with pytest.raises(DocumentValidationError, match="does not match MIME type"):
        validate_extension_and_mime("report.png", "application/pdf")


def test_calculate_checksum_sha256_is_stable() -> None:
    checksum = calculate_checksum_sha256(b"content")
    assert checksum == calculate_checksum_sha256(b"content")
    assert len(checksum) == 64


def test_validate_magic_bytes_accepts_valid_signatures() -> None:
    validate_magic_bytes(b"%PDF-1.7", "application/pdf")
    validate_magic_bytes(b"\x89PNG\r\n\x1a\n", "image/png")
    validate_magic_bytes(b"\xff\xd8\xff\xe0", "image/jpeg")
    validate_magic_bytes(
        b"PK\x03\x04",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    validate_magic_bytes(
        b"PK\x03\x04",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@pytest.mark.parametrize(
    "content, mime_type",
    [
        (b"not-a-pdf", "application/pdf"),
        (b"not-a-png", "image/png"),
        (b"not-a-jpeg", "image/jpeg"),
        (b"not-a-zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (b"not-a-zip", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ],
)
def test_validate_magic_bytes_rejects_mismatched_content(content: bytes, mime_type: str) -> None:
    with pytest.raises(DocumentValidationError, match="does not match MIME type"):
        validate_magic_bytes(content, mime_type)
