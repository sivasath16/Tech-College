import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

log = logging.getLogger("placement")

LOGO_TYPES = {
    "image/png": (".png", b"\x89PNG\r\n\x1a\n"),
    "image/jpeg": (".jpg", b"\xff\xd8\xff"),
    "image/webp": (".webp", b"RIFF"),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def otp_expiry() -> datetime:
    return utcnow() + timedelta(minutes=settings.otp_expire_minutes)


async def save_logo(file: UploadFile) -> str:
    """Validate type, size and magic bytes of a company logo and store it. Returns relative path."""
    if file.content_type not in LOGO_TYPES:
        raise HTTPException(422, "Logo must be a PNG, JPEG or WebP image")
    data = await file.read(settings.max_logo_bytes + 1)
    if len(data) > settings.max_logo_bytes:
        raise HTTPException(413, "Logo must be 2 MB or smaller")
    ext, magic = LOGO_TYPES[file.content_type]
    if not data.startswith(magic):
        raise HTTPException(422, "File content does not match image type")
    folder = Path(settings.upload_dir) / "logos"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (folder / name).write_bytes(data)
    return f"logos/{name}"


DOC_MAGIC = {
    ".pdf": b"%PDF-",
    ".docx": b"PK\x03\x04",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
}
DOC_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
RESUME_EXTS = {".pdf", ".docx"}
CERTIFICATE_EXTS = {".pdf", ".png", ".jpg"}


async def save_document(file: UploadFile, folder_name: str, allowed: set[str]) -> str:
    """Validate type, size and magic bytes of a private student document. Returns relative path."""
    ext = DOC_CONTENT_TYPES.get(file.content_type or "")
    if ext is None or ext not in allowed:
        names = ", ".join(sorted(e.lstrip(".").upper() for e in allowed))
        raise HTTPException(422, f"File must be one of: {names}")
    data = await file.read(settings.max_document_bytes + 1)
    if not data:
        raise HTTPException(422, "File is empty")
    if len(data) > settings.max_document_bytes:
        raise HTTPException(413, f"File must be {settings.max_document_bytes // (1024 * 1024)} MB or smaller")
    if not data.startswith(DOC_MAGIC[ext]):
        raise HTTPException(422, "File content does not match its type")
    folder = Path(settings.upload_dir) / folder_name
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    (folder / name).write_bytes(data)
    return f"{folder_name}/{name}"


def delete_file(relative_path: str | None) -> None:
    if relative_path:
        (Path(settings.upload_dir) / relative_path).unlink(missing_ok=True)
