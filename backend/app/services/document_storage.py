from __future__ import annotations

import os
import hashlib
import uuid
from pathlib import Path


class DocumentStorageError(ValueError):
    pass


class DocumentStorage:
    def save_encrypted(self, document_id: str, encrypted_bytes: bytes) -> str:
        raise NotImplementedError

    def read_encrypted(self, document_id: str) -> bytes:
        raise NotImplementedError

    def exists(self, document_id: str) -> bool:
        raise NotImplementedError

    def archive(self, document_id: str) -> None:
        raise NotImplementedError

    def delete_permanently(self, document_id: str) -> None:
        raise NotImplementedError


class LocalDocumentStorage(DocumentStorage):
    def __init__(self, root: str | Path = "private_storage/documents") -> None:
        self.root = Path(root).resolve()
        self.active_root = self.root / "active"
        self.archive_root = self.root / "archive"
        self.active_root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)

    def _safe_filename(self, document_id: str) -> str:
        try:
            parsed = uuid.UUID(document_id)
        except ValueError as exc:
            raise DocumentStorageError("Document id must be an opaque UUID") from exc
        opaque_name = hashlib.sha256(f"legacyguard-document:{parsed.hex}".encode("utf-8")).hexdigest()
        return f"{opaque_name}.lgdoc"

    def _path_for(self, document_id: str, *, archived: bool = False) -> Path:
        root = self.archive_root if archived else self.active_root
        path = (root / self._safe_filename(document_id)).resolve()
        if os.path.commonpath([str(root.resolve()), str(path)]) != str(root.resolve()):
            raise DocumentStorageError("Invalid document storage path")
        return path

    def save_encrypted(self, document_id: str, encrypted_bytes: bytes) -> str:
        if not encrypted_bytes:
            raise DocumentStorageError("Encrypted document bytes are required")
        path = self._path_for(document_id)
        path.write_bytes(encrypted_bytes)
        return str(path.relative_to(self.root))

    def read_encrypted(self, document_id: str) -> bytes:
        path = self._path_for(document_id)
        if not path.exists():
            archived_path = self._path_for(document_id, archived=True)
            if archived_path.exists():
                return archived_path.read_bytes()
            raise DocumentStorageError("Encrypted document not found")
        return path.read_bytes()

    def exists(self, document_id: str) -> bool:
        return self._path_for(document_id).exists() or self._path_for(document_id, archived=True).exists()

    def archive(self, document_id: str) -> None:
        source = self._path_for(document_id)
        if not source.exists():
            raise DocumentStorageError("Encrypted document not found")
        target = self._path_for(document_id, archived=True)
        source.replace(target)

    def delete_permanently(self, document_id: str) -> None:
        for archived in (False, True):
            path = self._path_for(document_id, archived=archived)
            if path.exists():
                path.unlink()
