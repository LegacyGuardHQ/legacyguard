from __future__ import annotations

from dataclasses import dataclass

from app.services.discovery_rules import DISCOVERY_RULES, DiscoveryRule


@dataclass(frozen=True)
class EvidenceCandidate:
    category: str
    matched_terms: list[str]
    confidence_score: int


class DiscoveryEngine:
    def __init__(self, rules: tuple[DiscoveryRule, ...] = DISCOVERY_RULES) -> None:
        self.rules = rules

    def analyze_text(self, document_text: str | None) -> list[EvidenceCandidate]:
        if not document_text:
            return []

        normalized_text = document_text.casefold()
        candidates: list[EvidenceCandidate] = []

        for rule in self.rules:
            matched_terms = [keyword for keyword in rule.keywords if keyword.casefold() in normalized_text]
            if matched_terms:
                candidates.append(
                    EvidenceCandidate(
                        category=rule.category,
                        matched_terms=matched_terms,
                        confidence_score=rule.confidence_score,
                    )
                )

        return candidates