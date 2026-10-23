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
