"""Capability Catalog and rule packs (FR-03, AC-02). Write access: solution_architect (any project) or admin."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, Path, Query, Response
from pydantic import BaseModel
from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, authenticated, forbidden, not_found
from app.api.models import Page, PageInfo, decode_cursor, encode_cursor, escape_like
from app.catalog import service
from app.catalog.models import CapabilityVersion, RulePackVersion
from app.catalog.validation import validate_capability
from app.core.db import get_db
from app.core.errors import ApiError
from app.project.models import ProjectMember

router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticated)])

SEMVER = r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$"
ID_PATTERN = r"^[a-z][a-z0-9_.-]{0,63}$"
JsonBody = Body(..., media_type="application/json")


class CapabilityVersionOut(BaseModel):
    id: uuid.UUID
    capability_id: str
    version: str
    kind: str
    name: str
    content_sha256: str
    contract: dict[str, Any]
    registered_by: uuid.UUID
    registered_at: datetime


class RulePackVersionOut(BaseModel):
    id: uuid.UUID
    rule_pack_id: str
    version: str
    content_sha256: str
    rule_pack: dict[str, Any]
    registered_at: datetime


class ValidationIssueOut(BaseModel):
    code: str
    message: str
    location: str


class ValidationReport(BaseModel):
    valid: bool
    errors: list[ValidationIssueOut]
    warnings: list[ValidationIssueOut]


def require_architect(db: Session, ctx: AuthContext) -> None:
    if ctx.user.is_admin:
        return
    is_architect = db.execute(
        select(
            exists().where(ProjectMember.user_id == ctx.user.id, ProjectMember.roles.contains(["solution_architect"]))
        )
    ).scalar_one()
    if not is_architect:
        raise forbidden()


def _require_object(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        raise ApiError("contract_invalid", "契約は JSON のオブジェクトで送ってください。", 422)
    return body


@router.get("/capabilities", response_model=Page[CapabilityVersionOut], operation_id="listCapabilities")
def list_capabilities(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    tag: str | None = Query(None, pattern=r"^[a-z][a-z0-9_-]{0,31}$"),
    kind: Literal["local", "rest", "mcp_tool", "llm"] | None = None,
    q: str | None = Query(None, max_length=100),
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[CapabilityVersionOut]:
    offset = decode_cursor(cursor)
    stmt = select(CapabilityVersion)
    if kind:
        stmt = stmt.where(CapabilityVersion.kind == kind)
    if tag:
        stmt = stmt.where(CapabilityVersion.contract["tags"].contains([tag]))
    if q:
        pattern = escape_like(q)
        stmt = stmt.where(
            or_(
                CapabilityVersion.name.ilike(pattern, escape="\\"),
                CapabilityVersion.capability_id.ilike(pattern, escape="\\"),
            )
        )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(CapabilityVersion.capability_id, CapabilityVersion.registered_at).offset(offset).limit(limit)
    ).scalars()
    items = [CapabilityVersionOut.model_validate(r, from_attributes=True) for r in rows]
    return Page(items=items, page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total)))


@router.post(
    "/capabilities", response_model=CapabilityVersionOut, status_code=201, operation_id="registerCapabilityVersion"
)
def register_capability(
    response: Response,
    body: Any = JsonBody,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> CapabilityVersionOut:
    require_architect(db, ctx)
    row, created = service.register_capability(db, _require_object(body), ctx.user.id)
    response.status_code = 201 if created else 200
    return CapabilityVersionOut.model_validate(row, from_attributes=True)


@router.post("/capabilities/validate", response_model=ValidationReport, operation_id="validateCapabilityContract")
def validate(
    body: Any = JsonBody,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ValidationReport:
    require_architect(db, ctx)
    issues = validate_capability(body)
    errors = [ValidationIssueOut(code=i.code, message=i.message, location=i.location) for i in issues]
    return ValidationReport(valid=not errors, errors=errors, warnings=[])


@router.get(
    "/capabilities/{capability_id}/versions/{version}",
    response_model=CapabilityVersionOut,
    operation_id="getCapabilityVersion",
)
def get_capability_version(
    capability_id: str = Path(max_length=64, pattern=ID_PATTERN),
    version: str = Path(max_length=32, pattern=SEMVER),
    db: Session = Depends(get_db),  # noqa: B008
) -> CapabilityVersionOut:
    row = db.execute(
        select(CapabilityVersion).where(
            CapabilityVersion.capability_id == capability_id, CapabilityVersion.version == version
        )
    ).scalar_one_or_none()
    if row is None:
        raise not_found()
    return CapabilityVersionOut.model_validate(row, from_attributes=True)


@router.get("/rule-packs", response_model=Page[RulePackVersionOut], operation_id="listRulePacks")
def list_rule_packs(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[RulePackVersionOut]:
    offset = decode_cursor(cursor)
    total = db.execute(select(func.count()).select_from(RulePackVersion)).scalar_one()
    rows = db.execute(
        select(RulePackVersion)
        .order_by(RulePackVersion.rule_pack_id, RulePackVersion.registered_at)
        .offset(offset)
        .limit(limit)
    ).scalars()
    items = [RulePackVersionOut.model_validate(r, from_attributes=True) for r in rows]
    return Page(items=items, page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total)))


@router.post("/rule-packs", response_model=RulePackVersionOut, status_code=201, operation_id="registerRulePackVersion")
def register_rule_pack(
    response: Response,
    body: Any = JsonBody,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RulePackVersionOut:
    require_architect(db, ctx)
    row, created = service.register_rule_pack(db, _require_object(body), ctx.user.id)
    response.status_code = 201 if created else 200
    return RulePackVersionOut.model_validate(row, from_attributes=True)


@router.get(
    "/rule-packs/{rule_pack_id}/versions/{version}",
    response_model=RulePackVersionOut,
    operation_id="getRulePackVersion",
)
def get_rule_pack_version(
    rule_pack_id: str = Path(max_length=64, pattern=ID_PATTERN),
    version: str = Path(max_length=32, pattern=SEMVER),
    db: Session = Depends(get_db),  # noqa: B008
) -> RulePackVersionOut:
    row = db.execute(
        select(RulePackVersion).where(RulePackVersion.rule_pack_id == rule_pack_id, RulePackVersion.version == version)
    ).scalar_one_or_none()
    if row is None:
        raise not_found()
    return RulePackVersionOut.model_validate(row, from_attributes=True)
