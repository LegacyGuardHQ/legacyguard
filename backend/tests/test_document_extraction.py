from app.services.document_extraction import (
    EXTRACTION_METHOD_IN_MEMORY_TEXT,
    EXTRACTION_METHOD_PLAIN_TEXT,
    EXTRACTION_METHOD_UNSUPPORTED,
    WARNING_EMPTY_DOCUMENT,
    DocumentExtractionService,
)


def test_plain_text_extraction_works() -> None:
    service = DocumentExtractionService()

    result = service.extract_from_bytes(b"  retirement document\r\n rollover details  ", mime_type="text/plain")

    assert result.text == "retirement document\nrollover details"
    assert result.extraction_method == EXTRACTION_METHOD_PLAIN_TEXT
    assert result.warnings == []


def test_in_memory_text_extraction_works() -> None:
    service = DocumentExtractionService()

    result = service.extract_from_text("  policy coverage details  ")

    assert result.text == "policy coverage details"
    assert result.extraction_method == EXTRACTION_METHOD_IN_MEMORY_TEXT


def test_empty_document_handling() -> None:
    service = DocumentExtractionService()

    result = service.extract_from_bytes(b"", mime_type="text/plain")

    assert result.text == ""
    assert result.character_count == 0
    assert WARNING_EMPTY_DOCUMENT in result.warnings


def test_unsupported_format_handling() -> None:
    service = DocumentExtractionService()

    result = service.extract_from_bytes(b"%PDF-1.7 binary content", mime_type="application/pdf")

    assert result.text == ""
    assert result.character_count == 0
    assert result.extraction_method == EXTRACTION_METHOD_UNSUPPORTED
    assert result.warnings == ["PDF extraction not implemented"]


def test_character_count_accuracy() -> None:
    service = DocumentExtractionService()

    result = service.extract_from_text("abc\n123")

    assert result.character_count == 7


def test_no_document_persistence_occurs(tmp_path) -> None:
    service = DocumentExtractionService()

    before = set(tmp_path.iterdir())
    result = service.extract_from_text("temporary extracted content")
    after = set(tmp_path.iterdir())

    assert result.text == "temporary extracted content"
    assert before == after