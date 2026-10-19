"""Upload checks, storage and retrieval of documents (upload-and-files.md, docs/design/detail/documents.md).

Files are stored under a server-generated name in a directory that is never served. The user's file name is
kept only as a display string. Reads go document id -> DB row -> storage name -> resolved path under the root.
"""

import hashlib
import os
import re
import unicodedata
import uuid
from pathlib import Path

from app.adapters.local import LocalHandler
from app.core.errors import ApiError
from app.documents.inspect import inspect_document

MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
INSPECT_TIMEOUT_S = 20.0

# extension -> media type; the declared Content-Type and the magic bytes must agree with it.
EXTENSIONS = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAGIC = {"application/pdf": b"%PDF-", "image/png": b"\x89PNG\r\n\x1a\n", "image/jpeg": b"\xff\xd8\xff"}

_INSPECT_ERRORS = {
    "encrypted": ("document_encrypted", "暗号化された PDF は利用できません。"),
    "active_content": ("document_active_content", "JavaScript・添付ファイルを含む PDF は利用できません。"),
    "too_many_pages": ("too_many_pages", "ページ数が上限（30 ページ）を超えています。"),
    "too_many_pixels": ("image_too_large", "画像の画素数が上限を超えています。"),
}
_STORAGE_NAME = re.compile(r"^[0-9a-f]{32}$")


def unsupported() -> ApiError:
    return ApiError("unsupported_media_type", "PDF・PNG・JPEG のファイルだけを登録できます。", 415)


def display_name(raw: str | None) -> str:
    """NFC, last path component only, control/format characters removed, at most 255 characters."""
    name = unicodedata.normalize("NFC", raw or "")
    name = re.split(r"[/\\]", name)[-1]
    name = "".join(ch for ch in name if unicodedata.category(ch) not in ("Cc", "Cf")).strip()
    if not name or name in (".", ".."):
        raise ApiError("invalid_file_name", "ファイル名が正しくありません。", 422)
    if len(name) > 255:  # keep the extension, which decides the media type
        suffix = Path(name).suffix[:16]
        name = name[: 255 - len(suffix)] + suffix
    return name


def media_type_of(name: str, declared: str | None, head: bytes) -> str:
    """Extension, declared Content-Type and magic bytes must name the same allowed type (415 otherwise)."""
    media_type = EXTENSIONS.get(Path(name).suffix.lower())
    declared_type = (declared or "").split(";")[0].strip().lower()
    if media_type is None or declared_type != media_type or not head.startswith(MAGIC[media_type]):
        raise unsupported()
    return media_type


def inspect(data: bytes, media_type: str) -> int:
    """Page count from the child-process check. Anything but a clean result is rejected (fail closed)."""
    result = LocalHandler(inspect_document).invoke({"data": data, "media_type": media_type}, {}, INSPECT_TIMEOUT_S)
    output = result.output or {}
    if result.status == "ok" and output.get("status") == "ok":
        return int(output["page_count"])
    code, message = _INSPECT_ERRORS.get(
        str(output.get("status")), ("document_unreadable", "ファイルを読み取れません。")
    )
    raise ApiError(code, message, 422)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def new_storage_name() -> str:
    return uuid.uuid4().hex


def _path(root: Path, storage_name: str) -> Path:
    if not _STORAGE_NAME.fullmatch(storage_name):
        raise ValueError("invalid storage name")
    base = root.resolve()
    path = (base / storage_name).resolve()
    if not path.is_relative_to(base):
        raise ValueError("path escapes the storage root")
    return path


def write(root: Path, storage_name: str, data: bytes) -> None:
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    # O_EXCL: never overwrite; 0o600: readable by the application user only.
    fd = os.open(_path(root, storage_name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


def remove(root: Path, storage_name: str) -> None:
    _path(root, storage_name).unlink(missing_ok=True)


def read(root: Path, storage_name: str, expected_sha256: str) -> bytes:
    data = _path(root, storage_name).read_bytes()
    if sha256_hex(data) != expected_sha256:
        raise ValueError("stored document does not match its recorded hash")
    return data
