from __future__ import annotations

import hashlib
import mimetypes
import re
import unicodedata
from pathlib import PurePath

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".txt", ".docx", ".xlsx"}
ALLOWED_MIME_TYPES = {
    "application/pdf": {".pdf"},
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "text/plain": {".txt"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
}
DANGEROUS_EXTENSIONS = {".exe", ".bat", ".cmd", ".com", ".js", ".vbs", ".ps1", ".sh", ".html", ".svg", ".zip", ".rar", ".7z"}


class DocumentValidationError(ValueError):
    pass


class MalwareScanner:
    def scan(self, content: bytes) -> None:
        raise NotImplementedError("Malware scanning hook is not implemented")


def validate_document_size(size: int) -> int:
    if size <= 0:
        raise DocumentValidationError("Document file must not be empty")
    if size > MAX_DOCUMENT_BYTES:
        raise DocumentValidationError("Document exceeds maximum size")
    return size


def normalize_display_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFKC", filename or "").strip()
    if not normalized:
        raise DocumentValidationError("Filename is required")
    if any(separator in normalized for separator in ("/", "\\")) or PurePath(normalized).name != normalized:
        raise DocumentValidationError("Filename must not contain path components")
    normalized = re.sub(r"[\x00-\x1f\x7f]", "", normalized).strip()
    if not normalized or normalized in {".", ".."}:
        raise DocumentValidationError("Invalid filename")
    if len(normalized) > 255:
        raise DocumentValidationError("Filename is too long")
    return normalized


def _extensions(filename: str) -> list[str]:
    suffixes = [suffix.lower() for suffix in PurePath(filename).suffixes]
    if not suffixes:
        raise DocumentValidationError("Document extension is required")
    return suffixes


def validate_extension_and_mime(filename: str, mime_type: str) -> tuple[str, str]:
    display_name = normalize_display_filename(filename)
    suffixes = _extensions(display_name)
    final_extension = suffixes[-1]
    if any(suffix in DANGEROUS_EXTENSIONS for suffix in suffixes):
        raise DocumentValidationError("Filename contains a dangerous extension")
    if len(suffixes) > 1 and final_extension not in {".gz"}:
        raise DocumentValidationError("Double extensions are not allowed")
    if final_extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError("Unsupported document extension")
    if mime_type not in ALLOWED_MIME_TYPES:
        raise DocumentValidationError("Unsupported document MIME type")
    if final_extension not in ALLOWED_MIME_TYPES[mime_type]:
        guessed, _ = mimetypes.guess_type(display_name)
        if guessed != mime_type:
            raise DocumentValidationError("Document extension does not match MIME type")
    return display_name, final_extension


def calculate_checksum_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def validate_magic_bytes(content: bytes, mime_type: str) -> None:
    if mime_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise DocumentValidationError("Document content does not match MIME type")
    if mime_type == "image/png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise DocumentValidationError("Document content does not match MIME type")
    if mime_type == "image/jpeg" and not content.startswith(b"\xff\xd8\xff"):
        raise DocumentValidationError("Document content does not match MIME type")
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" and not content.startswith(b"PK"):
        raise DocumentValidationError("Document content does not match MIME type")
    if mime_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" and not content.startswith(b"PK"):
        raise DocumentValidationError("Document content does not match MIME type")
