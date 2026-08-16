"""Shared utilities for document storage configuration."""

from app.config import settings


def get_default_document_storage_root() -> str:
    """Centralized helper for resolving the document storage root.

    This avoids duplicating `settings.document_storage_root or "private_storage/documents"`
    in multiple places; other modules (e.g. api/documents, discovery_orchestrator) should
    import and use this helper to ensure consistency.
    """
    return settings.document_storage_root or "private_storage/documents"
