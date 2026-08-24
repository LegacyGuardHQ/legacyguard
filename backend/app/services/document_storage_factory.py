from __future__ import annotations

from app.config import Settings, settings
from app.services.document_storage import DocumentStorage, LocalDocumentStorage
from app.services.document_storage_config import get_default_document_storage_root


def build_document_storage(configuration: Settings = settings) -> DocumentStorage:
    if configuration.document_storage_backend == "LOCAL":
        return LocalDocumentStorage(configuration.document_storage_root or get_default_document_storage_root())
    if configuration.document_storage_backend == "OBJECT":
        from app.services.object_document_storage import ObjectDocumentStorage

        return ObjectDocumentStorage.from_settings(configuration)
    raise ValueError("Unsupported document storage backend")
