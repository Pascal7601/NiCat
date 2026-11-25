"""File preservation within a private, non-served filesystem root."""
import hashlib
import os
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError

MAX_BYTES_DEFAULT = 8 * 1024 * 1024


def private_root() -> Path:
    root = Path(getattr(settings, "NICAT_DOCUMENT_PRIVATE_ROOT", Path(settings.BASE_DIR).parent / "private_document_uploads")).resolve()
    # Avoid accidentally serving private uploads through Django's configured public roots.
    for attr in ("STATIC_ROOT", "MEDIA_ROOT"):
        configured = getattr(settings, attr, None)
        if configured:
            public = Path(configured).resolve()
            if root == public or public in root.parents:
                raise RuntimeError(f"NICAT_DOCUMENT_PRIVATE_ROOT must not be inside {attr}")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return root


def private_path(key: str) -> Path:
    if not key or "/" in key or "\\" in key or ".." in key:
        raise ValueError("Invalid internal document key")
    return private_root() / key


def save_original(upload, key: str, file_type: str) -> tuple[int, str]:
    """Byte-for-byte storage. Never use a user-controlled filename as a path."""
    limit = min(MAX_BYTES_DEFAULT, max(1, int(getattr(settings, "NICAT_DOCUMENT_MAX_BYTES", MAX_BYTES_DEFAULT))))
    path = private_path(key)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as out:
            first = True
            for chunk in upload.chunks(chunk_size=65536):
                if not isinstance(chunk, bytes):
                    raise ValidationError("Upload is not binary")
                size += len(chunk)
                if size > limit:
                    raise ValidationError(f"Document exceeds {limit} bytes")
                if first:
                    if file_type == "pdf" and not chunk.startswith(b"%PDF-"):
                        raise ValidationError("File content does not match a PDF")
                    first = False
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise ValidationError("Empty files cannot be uploaded")
        if file_type == "txt":
            try:
                # Text uploads must be valid UTF-8 and contain no NUL bytes.
                content = path.read_bytes()
                if b"\x00" in content:
                    raise UnicodeError("NUL byte")
                content.decode("utf-8-sig")
            except UnicodeError:
                raise ValidationError("TXT files must be UTF-8 plain text")
        return size, digest.hexdigest()
    except Exception:
        path.unlink(missing_ok=True)
        raise
