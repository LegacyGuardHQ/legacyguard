from __future__ import annotations

from dataclasses import dataclass

EXTRACTION_METHOD_PLAIN_TEXT = "PLAIN_TEXT"
EXTRACTION_METHOD_IN_MEMORY_TEXT = "IN_MEMORY_TEXT"
EXTRACTION_METHOD_UNSUPPORTED = "UNSUPPORTED"

WARNING_EMPTY_DOCUMENT = "Document content is empty"
WARNING_UNSUPPORTED_FORMAT = "Document format extraction not implemented"

SUPPORTED_TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


@dataclass(frozen=True)
class NormalizedDocumentText:
    text: str
    character_count: int
    extraction_method: str
    warnings: list[str]


class DocumentExtractionService:
    def extract_from_text(self, document_text: str | None) -> NormalizedDocumentText:
        normalized = self._normalize_text(document_text or "")
        warnings = [WARNING_EMPTY_DOCUMENT] if not normalized else []
        return NormalizedDocumentText(
            text=normalized,
            character_count=len(normalized),
            extraction_method=EXTRACTION_METHOD_IN_MEMORY_TEXT,
            warnings=warnings,
        )

    def extract_from_bytes(self, content: bytes | None, *, mime_type: str | None = None) -> NormalizedDocumentText:
        if not content:
            return NormalizedDocumentText(
                text="",
                character_count=0,
                extraction_method=EXTRACTION_METHOD_PLAIN_TEXT,
                warnings=[WARNING_EMPTY_DOCUMENT],
            )

        if not self._is_supported_text_format(mime_type):
            return NormalizedDocumentText(
                text="",
                character_count=0,
                extraction_method=EXTRACTION_METHOD_UNSUPPORTED,
                warnings=[self._unsupported_format_warning(mime_type)],
            )

        normalized = self._normalize_text(content.decode("utf-8", errors="replace"))
        warnings = [WARNING_EMPTY_DOCUMENT] if not normalized else []
        return NormalizedDocumentText(
            text=normalized,
            character_count=len(normalized),
            extraction_method=EXTRACTION_METHOD_PLAIN_TEXT,
            warnings=warnings,
        )

    def _is_supported_text_format(self, mime_type: str | None) -> bool:
        return mime_type is None or mime_type in SUPPORTED_TEXT_MIME_TYPES

    def _normalize_text(self, document_text: str) -> str:
        return "\n".join(line.strip() for line in document_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")).strip()

    def _unsupported_format_warning(self, mime_type: str | None) -> str:
        if mime_type == "application/pdf":
            return "PDF extraction not implemented"
        if mime_type in {"application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"}:
            return "Word document extraction not implemented"
        if mime_type and mime_type.startswith("image/"):
            return "OCR extraction not implemented"
        return WARNING_UNSUPPORTED_FORMAT