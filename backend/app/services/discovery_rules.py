from __future__ import annotations

from dataclasses import dataclass

from app.services.discovery_categories import (
    BANKING_INDICATOR,
    BENEFICIARY_INDICATOR,
    EMPLOYMENT_BENEFIT_INDICATOR,
    GOVERNMENT_BENEFIT_INDICATOR,
    INSURANCE_INDICATOR,
    INVESTMENT_INDICATOR,
    OTHER_FINANCIAL_INDICATOR,
    PROPERTY_INDICATOR,
    RETIREMENT_INDICATOR,
)


@dataclass(frozen=True)
class DiscoveryRule:
    category: str
    keywords: tuple[str, ...]
    confidence_score: int


DISCOVERY_RULES = (
    DiscoveryRule(
        category=RETIREMENT_INDICATOR,
        keywords=("401k", "401(k)", "retirement", "pension", "IRA", "rollover", "beneficiary", "distribution"),
        confidence_score=85,
    ),
    DiscoveryRule(
        category=INSURANCE_INDICATOR,
        keywords=("policy", "coverage", "premium", "beneficiary", "claim", "life insurance"),
        confidence_score=80,
    ),
    DiscoveryRule(
        category=INVESTMENT_INDICATOR,
        keywords=("brokerage", "dividend", "portfolio", "securities", "stocks", "bonds", "mutual fund"),
        confidence_score=80,
    ),
    DiscoveryRule(
        category=EMPLOYMENT_BENEFIT_INDICATOR,
        keywords=("employee benefits", "employer match", "vesting", "stock options", "benefits enrollment"),
        confidence_score=75,
    ),
    DiscoveryRule(
        category=BANKING_INDICATOR,
        keywords=("bank statement", "checking", "savings", "account number", "routing number", "certificate of deposit"),
        confidence_score=80,
    ),
    DiscoveryRule(
        category=PROPERTY_INDICATOR,
        keywords=("deed", "mortgage", "property tax", "parcel", "real estate", "title"),
        confidence_score=80,
    ),
    DiscoveryRule(
        category=BENEFICIARY_INDICATOR,
        keywords=("beneficiary", "payable on death", "transfer on death", "contingent beneficiary"),
        confidence_score=75,
    ),
    DiscoveryRule(
        category=GOVERNMENT_BENEFIT_INDICATOR,
        keywords=("social security", "medicare", "veterans benefits", "va benefits", "government benefit"),
        confidence_score=75,
    ),
    DiscoveryRule(
        category=OTHER_FINANCIAL_INDICATOR,
        keywords=("financial", "statement", "account", "asset", "liability"),
        confidence_score=60,
    ),
)