from __future__ import annotations

import os
import hashlib
import hmac
import tempfile
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath


class DocumentStorageError(ValueError):
    pass


class DocumentIntegrityError(DocumentStorageError):
    pass


@dataclass(frozen=True)
class StorageReadiness:
    configuration_valid: bool
    reachable: bool
    write_ready: bool | None

    @property
    def ready(self) -> bool:
        return self.configuration_valid and self.reachable and self.write_ready is not False


class DocumentStorage(ABC):
    @abstractmethod
    def save_encrypted(self, document_id: str, encrypted_bytes: bytes) -> str:
        raise NotImplementedError

    @abstractmethod
    def read_encrypted(
        self,
        locator: str,
        *,
        expected_sha256: str | None = None,
        expected_size: int | None = None,
    ) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def exists(self, locator: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def archive(self, locator: str) -> str:
        """Apply backend archival semantics.

        Backends may retain an immutable object in place when archival is represented
        by authoritative database state. A physical move is not required by contract.
        """
        raise NotImplementedError

    @abstractmethod
    def delete_permanently(self, locator: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def check_readiness(self) -> StorageReadiness:
        """Perform a non-destructive backend readiness check."""
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

    def _path_from_locator(self, locator: str, *, allowed_roots: tuple[Path, ...] | None = None) -> Path:
        windows_locator = PureWindowsPath(locator)
        if not locator or PurePosixPath(locator).is_absolute() or windows_locator.is_absolute() or windows_locator.drive:
            raise DocumentStorageError("Invalid document storage locator")
        try:
            locator_path = Path(locator)
            if ".." in locator_path.parts or ".." in windows_locator.parts:
                raise DocumentStorageError("Invalid document storage locator")
            path = (self.root / locator_path).resolve()
            permitted_roots = allowed_roots or (self.active_root, self.archive_root)
            within_permitted_root = any(
                os.path.commonpath([str(root.resolve()), str(path)]) == str(root.resolve())
                for root in permitted_roots
            )
        except (OSError, ValueError) as exc:
            raise DocumentStorageError("Invalid document storage locator") from exc
        if not within_permitted_root:
            raise DocumentStorageError("Invalid document storage locator")
        return path

    def save_encrypted(self, document_id: str, encrypted_bytes: bytes) -> str:
        if not encrypted_bytes:
            raise DocumentStorageError("Encrypted document bytes are required")
        path = self._path_for(document_id)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=path.parent,
                prefix=".upload-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(encrypted_bytes)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, path)
            temporary_path = None
        except OSError as exc:
            raise DocumentStorageError("Encrypted document could not be stored") from exc
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return str(path.relative_to(self.root))

    def read_encrypted(
        self,
        locator: str,
        *,
        expected_sha256: str | None = None,
        expected_size: int | None = None,
    ) -> bytes:
        path = self._path_from_locator(locator)
        if not path.is_file():
            raise DocumentStorageError("Encrypted document not found")
        encrypted_bytes = path.read_bytes()
        if expected_size is not None and len(encrypted_bytes) != expected_size:
            raise DocumentIntegrityError("Encrypted document size mismatch")
        if expected_sha256 is not None:
            normalized_expected = expected_sha256.strip().lower()
            actual = hashlib.sha256(encrypted_bytes).hexdigest()
            if len(normalized_expected) != 64 or not hmac.compare_digest(actual, normalized_expected):
                raise DocumentIntegrityError("Encrypted document checksum mismatch")
        return encrypted_bytes

    def exists(self, locator: str) -> bool:
        return self._path_from_locator(locator).is_file()

    def archive(self, locator: str) -> str:
        source = self._path_from_locator(locator, allowed_roots=(self.active_root,))
        if not source.is_file():
            raise DocumentStorageError("Encrypted document not found")
        target = self._path_from_locator(
            str(Path("archive") / source.name),
            allowed_roots=(self.archive_root,),
        )
        source.replace(target)
        return str(target.relative_to(self.root))

    def delete_permanently(self, locator: str) -> None:
        path = self._path_from_locator(locator)
        if path.is_file():
            path.unlink()

    def check_readiness(self) -> StorageReadiness:
        configuration_valid = self.active_root.parent == self.root and self.archive_root.parent == self.root
        reachable = self.active_root.is_dir() and self.archive_root.is_dir()
        write_ready = os.access(self.active_root, os.W_OK) and os.access(self.archive_root, os.W_OK) if reachable else False
        return StorageReadiness(configuration_valid, reachable, write_ready)
