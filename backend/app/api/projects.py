"""Projects, members and requirement revisions (FR-01/02, permissions.md)."""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import UnaryExpression, exists, func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, authenticated, forbidden, not_found, project_roles, require_project_role
from app.api.models import Page, PageInfo, StrictModel, UUIDIn, decode_cursor, encode_cursor, escape_like
from app.auth.models import User
from app.core.db import get_db
from app.core.errors import ApiError
from app.project.models import PROJECT_ROLES, Project, ProjectMember, RequirementRevision

router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticated)])

ProjectRole = Literal["solution_lead", "solution_architect", "qa_evaluator", "business_reviewer"]
SORTABLE: dict[str, UnaryExpression[Any]] = {
    "updated_at": Project.updated_at.asc(),
    "-updated_at": Project.updated_at.desc(),
    "name": Project.name.asc(),
    "-name": Project.name.desc(),
}


class ProjectCreate(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    business_domain: str = Field(min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=1000)


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    business_domain: str
    description: str | None
    owner_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MemberIn(StrictModel):
    user_id: UUIDIn
    roles: list[ProjectRole] = Field(min_length=1, max_length=len(PROJECT_ROLES))


class MemberOut(BaseModel):
    user_id: uuid.UUID
    display_name: str
    roles: list[str]


class RequirementCreate(StrictModel):
    content: str = Field(min_length=1, max_length=20000)


class RequirementOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    revision: int
    content: str
    ai_suggestions: dict[str, object] | None
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    created_at: datetime


def _project_out(p: Project) -> ProjectOut:
    return ProjectOut.model_validate(p, from_attributes=True)


def _requirement_out(r: RequirementRevision) -> RequirementOut:
    return RequirementOut(
        id=r.id,
        project_id=r.project_id,
        revision=r.revision,
        content=r.content,
        ai_suggestions=None,
        approved_by=r.approved_by,
        approved_at=r.approved_at,
        created_at=r.created_at,
    )


@router.get("/projects", response_model=Page[ProjectOut], operation_id="listProjects")
def list_projects(
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    sort: str = Query("-updated_at", max_length=20),
    q: str | None = Query(None, max_length=100),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[ProjectOut]:
    order = SORTABLE.get(sort)
    if order is None:
        raise ApiError("invalid_sort", "並び替えの項目が正しくありません。", 422)
    offset = decode_cursor(cursor)
    member = exists().where(ProjectMember.project_id == Project.id, ProjectMember.user_id == ctx.user.id)
    stmt = select(Project).where(member)
    if q:
        stmt = stmt.where(Project.name.ilike(escape_like(q), escape="\\"))
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(order, Project.id).offset(offset).limit(limit)).scalars().all()
    return Page(
        items=[_project_out(p) for p in rows],
        page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total)),
    )


@router.post("/projects", response_model=ProjectOut, status_code=201, operation_id="createProject")
def create_project(
    body: ProjectCreate,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ProjectOut:
    is_lead_somewhere = db.execute(
        select(exists().where(ProjectMember.user_id == ctx.user.id, ProjectMember.roles.contains(["solution_lead"])))
    ).scalar_one()
    if not (ctx.user.is_admin or is_lead_somewhere):
        raise forbidden()
    project = Project(
        name=body.name, business_domain=body.business_domain, description=body.description, owner_id=ctx.user.id
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=ctx.user.id, roles=["solution_lead"]))
    db.commit()
    return _project_out(project)


@router.get("/projects/{project_id}", response_model=ProjectOut, operation_id="getProject")
def get_project(
    project_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ProjectOut:
    project_roles(db, project_id, ctx.user)
    project = db.get(Project, project_id)
    if project is None:
        raise not_found()
    return _project_out(project)


@router.get("/projects/{project_id}/members", response_model=list[MemberOut], operation_id="getProjectMembers")
def get_members(
    project_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MemberOut]:
    project_roles(db, project_id, ctx.user)
    return _members(db, project_id)


def _members(db: Session, project_id: uuid.UUID) -> list[MemberOut]:
    rows = db.execute(
        select(ProjectMember, User.display_name)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(User.display_name)
    ).all()
    return [MemberOut(user_id=m.user_id, display_name=name, roles=list(m.roles)) for m, name in rows]


@router.put("/projects/{project_id}/members", response_model=list[MemberOut], operation_id="putProjectMembers")
def put_members(
    project_id: uuid.UUID,
    body: list[MemberIn],
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MemberOut]:
    require_project_role(db, project_id, ctx.user, {"solution_lead"})
    if not 1 <= len(body) <= 100:
        raise ApiError("validation_error", "メンバーは 1〜100 人で指定してください。", 422)
    ids = [m.user_id for m in body]
    if len(set(ids)) != len(ids):
        raise ApiError("duplicate_member", "同じ利用者が重複しています。", 422)
    mine = next((m for m in body if m.user_id == ctx.user.id), None)
    if mine is None or "solution_lead" not in mine.roles:
        raise ApiError("cannot_remove_own_lead", "自分の責任者（solution_lead）のロールは外せません。", 422)
    active = set(db.execute(select(User.id).where(User.id.in_(ids), User.is_active)).scalars())
    if active != set(ids):
        raise ApiError("unknown_user", "存在しない、または無効な利用者が含まれています。", 422)
    db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete()
    db.add_all(ProjectMember(project_id=project_id, user_id=m.user_id, roles=sorted(set(m.roles))) for m in body)
    db.commit()
    return _members(db, project_id)


@router.get(
    "/projects/{project_id}/requirements", response_model=list[RequirementOut], operation_id="listRequirementRevisions"
)
def list_requirements(
    project_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[RequirementOut]:
    project_roles(db, project_id, ctx.user)
    rows = db.execute(
        select(RequirementRevision)
        .where(RequirementRevision.project_id == project_id)
        .order_by(RequirementRevision.revision.desc())
        .limit(200)
    ).scalars()
    return [_requirement_out(r) for r in rows]


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementOut,
    status_code=201,
    operation_id="createRequirementRevision",
)
def create_requirement(
    project_id: uuid.UUID,
    body: RequirementCreate,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RequirementOut:
    require_project_role(db, project_id, ctx.user, {"solution_lead", "solution_architect"})
    # Lock the project row so concurrent submissions get consecutive revision numbers.
    db.execute(select(Project.id).where(Project.id == project_id).with_for_update())
    latest = db.execute(
        select(func.max(RequirementRevision.revision)).where(RequirementRevision.project_id == project_id)
    ).scalar_one()
    revision = RequirementRevision(
        project_id=project_id, revision=(latest or 0) + 1, content=body.content, created_by=ctx.user.id
    )
    db.add(revision)
    db.commit()
    return _requirement_out(revision)


@router.post(
    "/requirements/{revision_id}/approve", response_model=RequirementOut, operation_id="approveRequirementRevision"
)
def approve_requirement(
    revision_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RequirementOut:
    revision = db.execute(
        select(RequirementRevision).where(RequirementRevision.id == revision_id).with_for_update()
    ).scalar_one_or_none()
    if revision is None:
        raise not_found()
    require_project_role(db, revision.project_id, ctx.user, {"solution_lead"})
    if revision.created_by == ctx.user.id:
        raise ApiError("self_approval", "自分が作成した要件は承認できません。", 403)
    if revision.approved_by is not None:
        raise ApiError("already_approved", "この要件は承認済みです。", 409)
    revision.approved_by = ctx.user.id
    revision.approved_at = datetime.now(UTC)
    db.commit()
    return _requirement_out(revision)
