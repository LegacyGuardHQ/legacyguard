from app.services.discovery_categories import INSURANCE_INDICATOR, RETIREMENT_INDICATOR
from app.services.discovery_engine import DiscoveryEngine


def test_retirement_keyword_detection() -> None:
    engine = DiscoveryEngine()

    candidates = engine.analyze_text("The statement references a 401(k) rollover and retirement distribution.")

    retirement_candidate = next(candidate for candidate in candidates if candidate.category == RETIREMENT_INDICATOR)
    assert retirement_candidate.confidence_score == 85
    assert "401(k)" in retirement_candidate.matched_terms
    assert "rollover" in retirement_candidate.matched_terms
    assert "retirement" in retirement_candidate.matched_terms


def test_insurance_keyword_detection() -> None:
    engine = DiscoveryEngine()

    candidates = engine.analyze_text("This life insurance policy includes premium and coverage details.")

    insurance_candidate = next(candidate for candidate in candidates if candidate.category == INSURANCE_INDICATOR)
    assert insurance_candidate.confidence_score == 80
    assert "life insurance" in insurance_candidate.matched_terms
    assert "policy" in insurance_candidate.matched_terms
    assert "premium" in insurance_candidate.matched_terms


def test_no_false_positive_on_normal_text() -> None:
    engine = DiscoveryEngine()

    candidates = engine.analyze_text("This family recipe describes how to bake bread and prepare soup.")

    assert candidates == []


def test_confidence_scoring_behavior() -> None:
    engine = DiscoveryEngine()

    candidates = engine.analyze_text("IRA beneficiary information is included for review.")

    retirement_candidate = next(candidate for candidate in candidates if candidate.category == RETIREMENT_INDICATOR)
    insurance_candidate = next(candidate for candidate in candidates if candidate.category == INSURANCE_INDICATOR)

    assert retirement_candidate.confidence_score == 85
    assert insurance_candidate.confidence_score == 80