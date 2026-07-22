from __future__ import annotations

import re
from dataclasses import dataclass

# Keep excerpts short enough for human explainability while avoiding storage of full document passages.
MAX_EXCERPT_LENGTH = 250

# Matched terms should be short indicator phrases, not copied document fragments or identifiers.
MAX_TERM_LENGTH = 80

REDACTION_TOKEN = "[REDACTED]"
WARNING_REDACTION_APPLIED = "Sensitive pattern redaction applied"
WARNING_EXCERPT_TRUNCATED = "Evidence excerpt truncated"
WARNING_TERM_TRUNCATED = "Matched term truncated"

# These patterns target common high-risk identifiers that may appear in financial documents.
# The goal is data minimization before any future persistence of discovery findings.
SENSITIVE_PATTERNS = (
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),  # US Social Security number format.
    re.compile(r"\b[A-Z0-9][A-Z0-9-]*\d[A-Z0-9-]*\d[A-Z0-9-]*\d[A-Z0-9-]*\d[A-Z0-9-]*\b", re.IGNORECASE),  # Policy-like identifiers.
    re.compile(r"\b\d{8,}\b"),  # Long account/reference numbers.
    re.compile(r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),  # Email addresses.
    re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b"),  # US phone numbers.
)


@dataclass(frozen=True)
class DiscoveryPrivacyResult:
    sanitized_terms: list[str]
    sanitized_excerpt: str | None
    redaction_applied: bool
    warnings: list[str]


class DiscoveryPrivacyService:
    def sanitize_evidence(
        self,
        *,
        matched_terms: list[str] | tuple[str, ...] | None,
        evidence_excerpt: str | None,
    ) -> DiscoveryPrivacyResult:
        warnings: list[str] = []
        redaction_applied = False

        sanitized_terms: list[str] = []
        for term in matched_terms or []:
            sanitized_term, term_redacted = self._sanitize_text(term, max_length=MAX_TERM_LENGTH)
            if term_redacted:
                redaction_applied = True
                self._add_warning(warnings, WARNING_REDACTION_APPLIED)
            if len(term) > MAX_TERM_LENGTH:
                self._add_warning(warnings, WARNING_TERM_TRUNCATED)
            if sanitized_term:
                sanitized_terms.append(sanitized_term)

        sanitized_excerpt = None
        if evidence_excerpt:
            sanitized_excerpt, excerpt_redacted = self._sanitize_text(evidence_excerpt, max_length=MAX_EXCERPT_LENGTH)
            if excerpt_redacted:
                redaction_applied = True
                self._add_warning(warnings, WARNING_REDACTION_APPLIED)
            if len(evidence_excerpt) > MAX_EXCERPT_LENGTH:
                self._add_warning(warnings, WARNING_EXCERPT_TRUNCATED)

        return DiscoveryPrivacyResult(
            sanitized_terms=sanitized_terms,
            sanitized_excerpt=sanitized_excerpt,
            redaction_applied=redaction_applied,
            warnings=warnings,
        )

    def _sanitize_text(self, value: str, *, max_length: int) -> tuple[str, bool]:
        sanitized = value.strip()
        redaction_applied = False

        for pattern in SENSITIVE_PATTERNS:
            sanitized, substitutions = pattern.subn(REDACTION_TOKEN, sanitized)
            redaction_applied = redaction_applied or substitutions > 0

        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length].rstrip()

        return sanitized, redaction_applied

    def _add_warning(self, warnings: list[str], warning: str) -> None:
        if warning not in warnings:
            warnings.append(warning)