"""Documents: upload, list and download (upload-and-files.md, docs/design/detail/documents.md)."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException
from starlette.formparsers import MultiPartException

from app.api.deps import AuthContext, authenticated, get_settings_dep, not_found, project_roles, require_project_role
from app.api.models import Page, PageInfo, decode_cursor, encode_cursor
from app.core.config import Settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.documents import storage
from app.documents.models import Document

router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticated)])

UPLOAD_ROLES = {"solution_lead", "solution_architect", "qa_evaluator"}


class DocumentOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    display_name: str
    media_type: Literal["application/pdf", "image/png", "image/jpeg"]
    size_bytes: int
    page_count: int
    sha256: str
    data_origin: Literal["synthetic"]
    created_at: datetime


@dataclass
class Upload:
    name: str | None
    declared_type: str | None
    data: bytes


def _invalid() -> ApiError:
    return ApiError("validation_error", "入力内容に誤りがあります。", 422)


async def read_upload(request: Request) -> Upload:
    """multipart/form-data with exactly `file` and `data_origin=synthetic` (additionalProperties: false)."""
    try:
        form = await request.form(max_files=1, max_fields=1)
    except (HTTPException, MultiPartException) as exc:  # malformed body or too many parts
        raise _invalid() from exc
    try:
        file, origin = form.get("file"), form.get("data_origin")
        if set(form.keys()) != {"file", "data_origin"} or not isinstance(file, UploadFile) or origin != "synthetic":
            raise _invalid()
        data = await file.read(storage.MAX_DOCUMENT_BYTES + 1)
        return Upload(name=file.filename, declared_type=file.content_type, data=data)
    finally:
        await form.close()


def _out(document: Document) -> DocumentOut:
    return DocumentOut.model_validate(document, from_attributes=True)


@router.get("/projects/{project_id}/documents", response_model=Page[DocumentOut], operation_id="listDocuments")
def list_documents(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[DocumentOut]:
    project_roles(db, project_id, ctx.user)
    offset = decode_cursor(cursor)
    total = db.execute(select(func.count()).where(Document.project_id == project_id)).scalar_one()
    rows = db.execute(
        select(Document)
        .where(Document.project_id == project_id)
        .order_by(Document.created_at.desc(), Document.id)
        .offset(offset)
        .limit(limit)
    ).scalars()
    return Page(
        items=[_out(d) for d in rows], page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total))
    )


@router.post(
    "/projects/{project_id}/documents", response_model=DocumentOut, status_code=201, operation_id="uploadDocument"
)
def upload_document(
    project_id: uuid.UUID,
    upload: Upload = Depends(read_upload),  # noqa: B008
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> DocumentOut:
    require_project_role(db, project_id, ctx.user, UPLOAD_ROLES)
    if len(upload.data) > storage.MAX_DOCUMENT_BYTES:
        raise ApiError("document_too_large", "ファイルの大きさが上限（10 MB）を超えています。", 413)
    if not upload.data:
        raise ApiError("document_empty", "ファイルが空です。", 422)
    name = storage.display_name(upload.name)
    media_type = storage.media_type_of(name, upload.declared_type, upload.data[:16])
    page_count = storage.inspect(upload.data, media_type)

    document = Document(
        project_id=project_id,
        display_name=name,
        media_type=media_type,
        size_bytes=len(upload.data),
        page_count=page_count,
        sha256=storage.sha256_hex(upload.data),
        data_origin="synthetic",
        storage_name=storage.new_storage_name(),
        uploaded_by=ctx.user.id,
    )
    storage.write(settings.storage_dir, document.storage_name, upload.data)
    try:
        db.add(document)
        db.commit()
    except Exception:
        db.rollback()
        storage.remove(settings.storage_dir, document.storage_name)
        raise
    return _out(document)


def content_disposition(name: str) -> str:
    """attachment with an ASCII fallback and the RFC 5987 UTF-8 name (no user text reaches the header raw)."""
    fallback = "".join(ch if 0x20 <= ord(ch) < 0x7F and ch not in '"\\' else "_" for ch in name)
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(name, safe='')}"


@router.get("/documents/{document_id}/content", operation_id="downloadDocument")
def download_document(
    document_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    settings: Settings = Depends(get_settings_dep),  # noqa: B008
) -> Response:
    document = db.get(Document, document_id)
    if document is None:
        raise not_found()
    project_roles(db, document.project_id, ctx.user)
    data = storage.read(settings.storage_dir, document.storage_name, document.sha256)
    # nosniff and Cache-Control: no-store are added to every /api/ response by SecurityMiddleware.
    return Response(
        content=data,
        media_type=document.media_type,
        headers={"Content-Disposition": content_disposition(document.display_name)},
    )
