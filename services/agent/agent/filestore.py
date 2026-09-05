"""
Enterprise File Store — Staging layer for document management.

Files are stored on disk before being processed/indexed into ChromaDB.
This follows enterprise patterns (like Google Drive) where documents exist
in a file store first and are optionally indexed for AI retrieval.

Lifecycle:
  upload → staged on disk → (user/agent triggers) → processed → indexed in ChromaDB
"""

import os
import uuid
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("agent-service.filestore")

# Storage root — configurable via env, defaults to /data/filestore inside container
FILESTORE_ROOT = os.getenv("FILESTORE_ROOT", "/data/filestore")
FILESTORE_STAGING_ROOT = os.getenv("FILESTORE_STAGING_ROOT", "/data/filestore-staging")
FILESTORE_QUARANTINE_ROOT = os.getenv("FILESTORE_QUARANTINE_ROOT", "/data/filestore-quarantine")


def _ensure_root():
    """Create the filestore root directory if it doesn't exist."""
    Path(FILESTORE_ROOT).mkdir(parents=True, exist_ok=True)


def _ensure_stage_root():
    Path(FILESTORE_STAGING_ROOT).mkdir(parents=True, exist_ok=True)


def _ensure_quarantine_root():
    Path(FILESTORE_QUARANTINE_ROOT).mkdir(parents=True, exist_ok=True)


def _doc_dir(doc_id: str) -> Path:
    """Each document gets its own directory for clean isolation."""
    return Path(FILESTORE_ROOT) / doc_id


def _staging_dir(upload_id: str) -> Path:
    return Path(FILESTORE_STAGING_ROOT) / upload_id


def _quarantine_dir(upload_id: str) -> Path:
    return Path(FILESTORE_QUARANTINE_ROOT) / upload_id


def sanitize_filename(filename: str) -> str:
    sanitized = Path((filename or "").replace("\x00", "")).name.strip()
    if not sanitized or sanitized in {".", ".."}:
        raise ValueError("invalid filename")
    return sanitized


def create_upload_staging_path(upload_id: str, filename: str) -> Path:
    _ensure_stage_root()
    safe_filename = sanitize_filename(filename)
    stage_dir = _staging_dir(upload_id)
    stage_dir.mkdir(parents=True, exist_ok=True)
    return stage_dir / safe_filename


def _cleanup_parent_if_empty(path: Path) -> None:
    try:
        if path.exists() and path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    except OSError:
        pass


def promote_staged_file(upload_id: str, staged_path: str | Path, doc_id: str, filename: str) -> dict:
    _ensure_root()
    safe_filename = sanitize_filename(filename)
    src = Path(staged_path)
    if not src.exists():
        raise FileNotFoundError(f"staged file not found: {src}")
    doc_dir = _doc_dir(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)
    dest = doc_dir / safe_filename
    shutil.move(str(src), str(dest))
    _cleanup_parent_if_empty(_staging_dir(upload_id))
    size = dest.stat().st_size
    logger.info("Promoted staged file: upload_id=%s doc_id=%s path=%s size=%d", upload_id, doc_id, dest, size)
    return {"storage_path": str(dest), "size_bytes": size}


def quarantine_staged_file(upload_id: str, staged_path: str | Path, filename: str) -> dict:
    _ensure_quarantine_root()
    safe_filename = sanitize_filename(filename)
    src = Path(staged_path)
    quarantine_dir = _quarantine_dir(upload_id)
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    dest = quarantine_dir / safe_filename
    if src.exists():
                shutil.move(str(src), str(dest))
    _cleanup_parent_if_empty(_staging_dir(upload_id))
    size = dest.stat().st_size if dest.exists() else 0
    logger.warning("Quarantined staged file: upload_id=%s path=%s size=%d", upload_id, dest, size)
    return {"quarantine_path": str(dest), "size_bytes": size}


def save_file(doc_id: str, filename: str, content: bytes | str) -> dict:
    """
    Save a file to the staging area.

    Returns:
        dict with storage_path, size_bytes
    """
    _ensure_root()
    doc_dir = _doc_dir(doc_id)
    doc_dir.mkdir(parents=True, exist_ok=True)

    file_path = doc_dir / sanitize_filename(filename)
    if isinstance(content, str):
        file_path.write_text(content, encoding="utf-8")
        size = len(content.encode("utf-8"))
    else:
        file_path.write_bytes(content)
        size = len(content)

    storage_path = str(file_path)
    logger.info("File stored: doc_id=%s path=%s size=%d", doc_id, storage_path, size)
    return {"storage_path": storage_path, "size_bytes": size}


def read_file(doc_id: str, filename: str) -> str | None:
    """Read a text file from the store. Returns None if not found."""
    file_path = _doc_dir(doc_id) / sanitize_filename(filename)
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8")


def read_file_bytes(doc_id: str, filename: str) -> bytes | None:
    """Read raw bytes from the store. Returns None if not found."""
    file_path = _doc_dir(doc_id) / sanitize_filename(filename)
    if not file_path.exists():
        return None
    return file_path.read_bytes()


def file_exists(doc_id: str, filename: str) -> bool:
    """Check if a file exists in the store."""
    return (_doc_dir(doc_id) / sanitize_filename(filename)).exists()


def delete_file(doc_id: str) -> bool:
    """Delete a document's entire storage directory."""
    doc_dir = _doc_dir(doc_id)
    if doc_dir.exists():
        shutil.rmtree(doc_dir)
        logger.info("File deleted: doc_id=%s", doc_id)
        return True
    return False


def get_storage_stats() -> dict:
    """Get overall storage statistics."""
    _ensure_root()
    root = Path(FILESTORE_ROOT)
    total_files = 0
    total_size = 0
    for f in root.rglob("*"):
        if f.is_file():
            total_files += 1
            total_size += f.stat().st_size
    return {
        "root": FILESTORE_ROOT,
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }
