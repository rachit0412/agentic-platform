import logging
import os
import socket
import struct
from pathlib import Path

import magic

logger = logging.getLogger("agent-service.upload-security")

CLAMAV_HOST = os.getenv("CLAMAV_HOST", "clamav")
CLAMAV_PORT = int(os.getenv("CLAMAV_PORT", "3310"))
CLAMAV_TIMEOUT_SECONDS = float(os.getenv("CLAMAV_TIMEOUT_SECONDS", "30"))
MAX_UPLOAD_SIZE_BYTES = int(os.getenv("DOCUMENT_UPLOAD_MAX_BYTES", str(5 * 1024 * 1024)))
UPLOAD_READ_CHUNK_BYTES = int(os.getenv("DOCUMENT_UPLOAD_READ_CHUNK_BYTES", str(1024 * 1024)))
MAGIC_SAMPLE_BYTES = int(os.getenv("DOCUMENT_UPLOAD_MAGIC_SAMPLE_BYTES", "8192"))

ALLOWED_UPLOAD_TYPES = {
    ".txt": {"text/plain"},
    ".md": {"text/plain", "text/markdown"},
    ".json": {"application/json", "text/plain"},
    ".csv": {"text/csv", "text/plain", "application/csv", "application/vnd.ms-excel"},
    ".pdf": {"application/pdf"},
    ".log": {"text/plain"},
    ".yaml": {"text/plain", "application/x-yaml", "text/yaml"},
    ".yml": {"text/plain", "application/x-yaml", "text/yaml"},
    ".xml": {"application/xml", "text/xml", "text/plain"},
    ".html": {"text/html", "application/xhtml+xml", "text/plain"},
}
TEXT_LIKE_EXTENSIONS = {".txt", ".md", ".json", ".csv", ".log", ".yaml", ".yml", ".xml", ".html"}


class UploadSecurityError(Exception):
    def __init__(self, status_code: int, detail: str, *, malware_name: str | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.malware_name = malware_name


def sanitize_upload_filename(filename: str) -> str:
    sanitized = Path((filename or "").replace("\x00", "")).name.strip()
    if not sanitized or sanitized in {".", ".."}:
        raise UploadSecurityError(400, "A valid filename is required")
    return sanitized


def inspect_magic_bytes(filename: str, sample: bytes) -> dict:
    safe_name = sanitize_upload_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_TYPES:
        raise UploadSecurityError(
            415,
            "Unsupported file type. Allowed extensions: .txt, .md, .json, .csv, .pdf, .log, .yaml, .yml, .xml, .html",
        )
    if not sample:
        raise UploadSecurityError(400, "Uploaded file is empty")

    detected_mime = magic.from_buffer(sample, mime=True) or "application/octet-stream"
    allowed_mimes = ALLOWED_UPLOAD_TYPES[ext]
    if detected_mime not in allowed_mimes:
        if ext in TEXT_LIKE_EXTENSIONS and detected_mime.startswith("text/"):
            pass
        else:
            raise UploadSecurityError(
                415,
                f"File header does not match extension. Detected {detected_mime} for {ext or 'unknown'} file.",
            )

    return {"filename": safe_name, "extension": ext, "mime": detected_mime}


def scan_file_with_clamav(file_path: str | Path, *, chunk_size: int | None = None) -> dict:
    file_path = Path(file_path)
    read_size = chunk_size or UPLOAD_READ_CHUNK_BYTES
    try:
        with socket.create_connection((CLAMAV_HOST, CLAMAV_PORT), timeout=CLAMAV_TIMEOUT_SECONDS) as sock:
            sock.sendall(b"zINSTREAM\0")
            with file_path.open("rb") as handle:
                while True:
                    chunk = handle.read(read_size)
                    if not chunk:
                        break
                    sock.sendall(struct.pack(">I", len(chunk)))
                    sock.sendall(chunk)
            sock.sendall(struct.pack(">I", 0))

            reply = bytearray()
            while True:
                data = sock.recv(4096)
                if not data:
                    break
                reply.extend(data)
    except OSError as exc:
        raise UploadSecurityError(503, f"Upload malware scanner unavailable: {exc}") from exc

    decoded = reply.replace(b"\0", b"\n").decode("utf-8", "replace").strip()
    verdict = next((line.strip() for line in decoded.splitlines() if line.strip()), "")
    logger.info("ClamAV verdict for %s: %s", file_path.name, verdict or decoded)

    if verdict.endswith("OK"):
        return {"status": "clean", "verdict": verdict}
    if verdict.endswith("FOUND"):
        malware_name = verdict.split(": ", 1)[-1].rsplit(" FOUND", 1)[0].strip()
        raise UploadSecurityError(422, f"Malware detected: {malware_name}", malware_name=malware_name)
    if "ERROR" in verdict or "size limit exceeded" in verdict.lower():
        raise UploadSecurityError(502, f"Malware scan failed: {verdict}")

    raise UploadSecurityError(502, f"Unexpected malware scan response: {verdict or decoded}")