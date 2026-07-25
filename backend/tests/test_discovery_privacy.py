from app.services.discovery_privacy import (
    MAX_EXCERPT_LENGTH,
    REDACTION_TOKEN,
    WARNING_EXCERPT_TRUNCATED,
    WARNING_REDACTION_APPLIED,
    DiscoveryPrivacyService,
)


def test_normal_evidence_text_remains_readable() -> None:
    service = DiscoveryPrivacyService()

    result = service.sanitize_evidence(
        matched_terms=["retirement", "rollover"],
        evidence_excerpt="This document contains retirement-related indicator language.",
    )

    assert result.sanitized_terms == ["retirement", "rollover"]
    assert result.sanitized_excerpt == "This document contains retirement-related indicator language."
    assert result.redaction_applied is False
    assert result.warnings == []


def test_ssn_like_patterns_are_redacted() -> None:
    service = DiscoveryPrivacyService()

    result = service.sanitize_evidence(
        matched_terms=["123-45-6789"],
        evidence_excerpt="SSN 123-45-6789 appears near benefit language.",
    )

    assert result.sanitized_terms == [REDACTION_TOKEN]
    assert "123-45-6789" not in result.sanitized_excerpt
    assert REDACTION_TOKEN in result.sanitized_excerpt
    assert result.redaction_applied is True
    assert WARNING_REDACTION_APPLIED in result.warnings


def test_long_account_numbers_are_redacted() -> None:
    service = DiscoveryPrivacyService()

    result = service.sanitize_evidence(
        matched_terms=["account 987654321012"],
        evidence_excerpt="Account number 987654321012 is listed on the statement.",
    )

    assert "987654321012" not in result.sanitized_terms[0]
    assert "987654321012" not in result.sanitized_excerpt
    assert REDACTION_TOKEN in result.sanitized_excerpt
    assert result.redaction_applied is True


def test_long_excerpts_are_truncated() -> None:
    service = DiscoveryPrivacyService()
    long_excerpt = "retirement " * 100

    result = service.sanitize_evidence(matched_terms=["retirement"], evidence_excerpt=long_excerpt)

    assert result.sanitized_excerpt is not None
    assert len(result.sanitized_excerpt) <= MAX_EXCERPT_LENGTH
    assert WARNING_EXCERPT_TRUNCATED in result.warnings


def test_email_addresses_are_protected() -> None:
    service = DiscoveryPrivacyService()

    result = service.sanitize_evidence(
        matched_terms=["owner@example.com"],
        evidence_excerpt="Contact owner@example.com about coverage details.",
    )

    assert result.sanitized_terms == [REDACTION_TOKEN]
    assert "owner@example.com" not in result.sanitized_excerpt
    assert REDACTION_TOKEN in result.sanitized_excerpt
    assert result.redaction_applied is True


def test_empty_input_is_handled_safely() -> None:
    service = DiscoveryPrivacyService()

    result = service.sanitize_evidence(matched_terms=None, evidence_excerpt=None)

    assert result.sanitized_terms == []
    assert result.sanitized_excerpt is None
    assert result.redaction_applied is False
    assert result.warnings == []

def test_audit_metadata_discards_sensitive_or_unknown_keys() -> None:
    from app.services.audit import _sanitize_metadata

    result = _sanitize_metadata({
        "resource_type": "discovery_scan",
        "resource_id": "scan-1",
        "document_text": "secret content",
        "evidence_excerpt": "secret evidence",
        "nested": {"secret": True},
    })

    assert result == {
        "resource_type": "discovery_scan",
        "resource_id": "scan-1",
    }
    assert "secret" not in str(result)
