from app.models.discovery import EvidenceFinding


def test_evidence_finding_matched_terms_are_encrypted() -> None:
    finding = EvidenceFinding(id="finding-1")

    finding.set_matched_terms("401(k), rollover")

    assert finding.matched_terms_encrypted is not None
    assert finding.matched_terms_encrypted != "401(k), rollover"
    assert "401(k)" not in finding.matched_terms_encrypted


def test_evidence_finding_matched_terms_decrypt_to_original_value() -> None:
    finding = EvidenceFinding(id="finding-2")

    finding.set_matched_terms("retirement, pension")

    assert finding.get_matched_terms() == "retirement, pension"


def test_evidence_finding_excerpt_decrypts_to_original_value() -> None:
    finding = EvidenceFinding(id="finding-3")

    finding.set_evidence_excerpt("This document contains retirement-related indicators.")

    assert finding.evidence_excerpt_encrypted is not None
    assert finding.evidence_excerpt_encrypted != "This document contains retirement-related indicators."
    assert finding.get_evidence_excerpt() == "This document contains retirement-related indicators."


def test_evidence_finding_none_values_are_safe() -> None:
    finding = EvidenceFinding(id="finding-4")

    finding.set_matched_terms(None)
    finding.set_evidence_excerpt(None)

    assert finding.matched_terms_encrypted is None
    assert finding.evidence_excerpt_encrypted is None
    assert finding.get_matched_terms() is None
    assert finding.get_evidence_excerpt() is None


def test_evidence_finding_does_not_store_plaintext() -> None:
    finding = EvidenceFinding(id="finding-5")

    matched_terms = "policy, beneficiary"
    excerpt = "Policy beneficiary indicator appears in this document."

    finding.set_matched_terms(matched_terms)
    finding.set_evidence_excerpt(excerpt)

    assert finding.matched_terms_encrypted != matched_terms
    assert finding.evidence_excerpt_encrypted != excerpt
    assert matched_terms not in finding.matched_terms_encrypted
    assert excerpt not in finding.evidence_excerpt_encrypted