import base64
import uuid
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Strict

from app.core.errors import ApiError

MAX_OFFSET = 1_000_000


class StrictModel(BaseModel):
    """Request bodies: unknown fields are rejected (mass assignment), no coercion."""

    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


# JSON carries UUIDs as strings; allow that conversion only for UUID fields (strict mode stays on elsewhere).
UUIDIn = Annotated[uuid.UUID, Strict(False)]


class PageInfo(BaseModel):
    total: int
    next_cursor: str | None


class Page[T](BaseModel):
    items: list[T]
    page: PageInfo


def decode_cursor(cursor: str | None) -> int:
    if cursor is None:
        return 0
    try:
        offset = int(base64.urlsafe_b64decode(cursor.encode()).decode().removeprefix("o:"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise ApiError("invalid_cursor", "ページの指定が正しくありません。", 422) from exc
    if not 0 <= offset <= MAX_OFFSET:
        raise ApiError("invalid_cursor", "ページの指定が正しくありません。", 422)
    return offset


def encode_cursor(offset: int, limit: int, total: int) -> str | None:
    nxt = offset + limit
    return base64.urlsafe_b64encode(f"o:{nxt}".encode()).decode() if nxt < total else None


def escape_like(value: str) -> str:
    return "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
