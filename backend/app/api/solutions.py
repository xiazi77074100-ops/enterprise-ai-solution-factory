"""Solutions: workflow drafts, Composer validation and approval (run_execution.md §1・§2, permissions.md)."""

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.catalog import ValidationIssueOut, ValidationReport
from app.api.deps import AuthContext, authenticated, not_found, project_roles, require_project_role
from app.api.models import Page, PageInfo, StrictModel, UUIDIn, decode_cursor, encode_cursor
from app.catalog.models import CapabilityVersion
from app.catalog.validation import content_sha256
from app.composer.validation import Report, validate_workflow
from app.core.db import get_db
from app.core.errors import ApiError
from app.project.models import RequirementRevision
from app.solution.models import Solution

router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticated)])


class SolutionCreate(StrictModel):
    project_id: UUIDIn
    requirement_revision_id: UUIDIn
    workflow: dict[str, Any]


class SolutionUpdate(StrictModel):
    workflow: dict[str, Any]


class SolutionOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    requirement_revision_id: uuid.UUID
    state: Literal["draft", "validated", "approved", "archived"]
    workflow: dict[str, Any]
    workflow_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_by: uuid.UUID
    approved_by: uuid.UUID | None
    created_at: datetime


def _out(solution: Solution, response: Response | None = None) -> SolutionOut:
    if response is not None:
        response.headers["ETag"] = solution.etag
    return SolutionOut.model_validate(solution, from_attributes=True)


def contract_lookup(db: Session) -> Any:
    def lookup(capability_id: str, version: str) -> dict[str, Any] | None:
        return db.execute(
            select(CapabilityVersion.contract).where(
                CapabilityVersion.capability_id == capability_id, CapabilityVersion.version == version
            )
        ).scalar_one_or_none()

    return lookup


def compose(db: Session, workflow: dict[str, Any]) -> Report:
    return validate_workflow(workflow, contract_lookup(db))


def _report_out(report: Report) -> ValidationReport:
    def issues(items: list[Any]) -> list[ValidationIssueOut]:
        return [ValidationIssueOut(code=i.code, message=i.message, location=i.location) for i in items[:200]]

    return ValidationReport(valid=report.valid, errors=issues(report.errors), warnings=issues(report.warnings))


def load_solution(db: Session, solution_id: uuid.UUID, ctx: AuthContext, *, lock: bool = False) -> Solution:
    """The solution if the user is a member of its project; otherwise 404 (same as non-existent)."""
    stmt = select(Solution).where(Solution.id == solution_id)
    solution = db.execute(stmt.with_for_update() if lock else stmt).scalar_one_or_none()
    if solution is None:
        raise not_found()
    project_roles(db, solution.project_id, ctx.user)
    return solution


@router.post("/solutions", response_model=SolutionOut, status_code=201, operation_id="createSolution")
def create_solution(
    body: SolutionCreate,
    response: Response,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> SolutionOut:
    require_project_role(db, body.project_id, ctx.user, {"solution_architect"})
    requirement = db.get(RequirementRevision, body.requirement_revision_id)
    if requirement is None or requirement.project_id != body.project_id:
        raise ApiError("unknown_requirement_revision", "この案件の要件の版ではありません。", 422)
    solution = Solution(
        project_id=body.project_id,
        requirement_revision_id=body.requirement_revision_id,
        state="draft",
        workflow=body.workflow,
        workflow_hash=content_sha256(body.workflow),
        revision=1,
        created_by=ctx.user.id,
    )
    db.add(solution)
    db.commit()
    return _out(solution, response)


@router.get("/solutions/{solution_id}", response_model=SolutionOut, operation_id="getSolution")
def get_solution(
    solution_id: uuid.UUID,
    response: Response,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> SolutionOut:
    return _out(load_solution(db, solution_id, ctx), response)


@router.put("/solutions/{solution_id}", response_model=SolutionOut, operation_id="updateSolutionDraft")
def update_solution(
    solution_id: uuid.UUID,
    body: SolutionUpdate,
    response: Response,
    if_match: str = Header(max_length=128),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> SolutionOut:
    solution = load_solution(db, solution_id, ctx, lock=True)
    require_project_role(db, solution.project_id, ctx.user, {"solution_architect"})
    if solution.state not in ("draft", "validated"):
        raise ApiError("solution_frozen", "承認済みの解決策は変更できません。新しい解決策を作成してください。", 409)
    if if_match != solution.etag:
        raise ApiError(
            "precondition_failed", "ほかの人が先に更新しました。最新の内容を読み込んでからやり直してください。", 412
        )
    solution.workflow = body.workflow
    solution.workflow_hash = content_sha256(body.workflow)
    solution.revision += 1
    solution.state = "draft"
    solution.updated_at = datetime.now(UTC)
    db.commit()
    return _out(solution, response)


@router.post("/solutions/{solution_id}/validate", response_model=ValidationReport, operation_id="validateSolution")
def validate_solution(
    solution_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ValidationReport:
    solution = load_solution(db, solution_id, ctx, lock=True)
    require_project_role(db, solution.project_id, ctx.user, {"solution_architect"})
    report = compose(db, solution.workflow)
    if report.valid and solution.state == "draft":
        solution.state = "validated"
        solution.updated_at = datetime.now(UTC)
    db.commit()
    return _report_out(report)


@router.post("/solutions/{solution_id}/approve", response_model=SolutionOut, operation_id="approveSolution")
def approve_solution(
    solution_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> SolutionOut:
    solution = load_solution(db, solution_id, ctx, lock=True)
    require_project_role(db, solution.project_id, ctx.user, {"solution_lead"})
    if solution.created_by == ctx.user.id:
        raise ApiError("self_approval", "自分が作成した解決策は承認できません。", 403)
    if solution.state == "approved":
        raise ApiError("already_approved", "この解決策は承認済みです。", 409)
    if solution.state != "validated" or not compose(db, solution.workflow).valid:
        raise ApiError("not_validated", "検証に合格した解決策だけを承認できます。", 409)
    requirement = db.get(RequirementRevision, solution.requirement_revision_id)
    if requirement is None or requirement.approved_by is None:
        raise ApiError("requirement_not_approved", "要件の版が承認されていません。", 409)
    solution.state = "approved"
    solution.approved_by = ctx.user.id
    solution.approved_at = solution.updated_at = datetime.now(UTC)
    db.commit()
    return _out(solution)


@router.get("/projects/{project_id}/solutions", response_model=Page[SolutionOut], operation_id="listSolutions")
def list_solutions(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[SolutionOut]:
    project_roles(db, project_id, ctx.user)
    offset = decode_cursor(cursor)
    stmt = select(Solution).where(Solution.project_id == project_id)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Solution.created_at.desc(), Solution.id).offset(offset).limit(limit)).scalars()
    return Page(
        items=[_out(s) for s in rows],
        page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total)),
    )
