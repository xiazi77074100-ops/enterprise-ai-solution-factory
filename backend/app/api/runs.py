"""Runs, node runs, trace and human review (run_execution.md §4・§6・§7, permissions.md)."""

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthContext, authenticated, forbidden, not_found, project_roles, require_project_role
from app.api.models import Page, PageInfo, StrictModel, decode_cursor, encode_cursor
from app.api.solutions import load_solution
from app.catalog.models import CapabilityVersion
from app.core.db import get_db
from app.executor import engine
from app.executor.models import NodeRun, ReviewTask, Run, RunEvent
from app.project.models import ProjectMember

router = APIRouter(prefix="/api/v1", dependencies=[Depends(authenticated)])

RunStatus = Literal["pending", "running", "waiting_review", "succeeded", "rejected", "failed", "cancelled"]
Scalar = str | int | bool


class RunCreate(StrictModel):
    inputs: dict[str, Scalar] = Field(max_length=10)


class UsageOut(BaseModel):
    llm_input_tokens: int
    llm_output_tokens: int
    cost_jpy: float | None
    cost_known: bool


class RunOut(BaseModel):
    id: uuid.UUID
    solution_id: uuid.UUID
    project_id: uuid.UUID
    workflow_hash: str
    status: RunStatus
    execution_mode: Literal["real", "mock", "mixed"]
    trace_id: str
    input_sha256: str
    failure_code: str | None
    started_at: datetime | None
    finished_at: datetime | None
    usage: UsageOut


class NodeRunOut(BaseModel):
    id: uuid.UUID
    node_id: str
    capability_id: str
    capability_version: str
    capability_version_id: uuid.UUID
    status: Literal["pending", "running", "waiting_review", "succeeded", "failed", "skipped"]
    execution_mode: Literal["real", "mock"]
    attempt: int
    duration_ms: int | None
    input_sha256: str | None
    output_sha256: str | None
    output_summary: dict[str, Any] | None
    llm: dict[str, Any] | None
    error_code: str | None


class Correction(StrictModel):
    path: str = Field(max_length=256)
    corrected_value: str | float | bool | None
    comment: str | None = Field(default=None, max_length=1000)


class ReviewDecision(StrictModel):
    decision: Literal["approved", "approved_with_corrections", "rejected"]
    corrections: list[Correction] = Field(default_factory=list, max_length=200)
    comment: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _rules(self) -> "ReviewDecision":
        if self.decision == "approved_with_corrections" and not self.corrections:
            raise ValueError("corrections are required for approved_with_corrections")
        if self.decision == "approved" and self.corrections:
            raise ValueError("corrections are only allowed with approved_with_corrections")
        if self.decision == "rejected" and not self.comment:
            raise ValueError("a comment is required to reject")
        return self


class ReviewTaskOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    node_id: str
    status: Literal["pending", "completed"]
    assigned_to: uuid.UUID
    items: list[dict[str, Any]]
    decision: Literal["approved", "approved_with_corrections", "rejected"] | None
    decided_by: uuid.UUID | None
    decided_at: datetime | None


def _run_out(run: Run) -> RunOut:
    return RunOut.model_validate(run, from_attributes=True)


def _review_out(task: ReviewTask) -> ReviewTaskOut:
    return ReviewTaskOut.model_validate(task, from_attributes=True)


def load_run(db: Session, run_id: uuid.UUID, ctx: AuthContext) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise not_found()
    project_roles(db, run.project_id, ctx.user)
    return run


@router.post("/solutions/{solution_id}/runs", response_model=RunOut, status_code=202, operation_id="startRun")
def start_run(
    solution_id: uuid.UUID,
    body: RunCreate,
    request: Request,
    idempotency_key: uuid.UUID = Header(),  # noqa: B008
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RunOut:
    solution = load_solution(db, solution_id, ctx)
    require_project_role(db, solution.project_id, ctx.user, {"solution_lead", "solution_architect", "qa_evaluator"})
    run, _ = engine.start_run(db, solution, ctx.user.id, dict(body.inputs), idempotency_key, request.app.state.handlers)
    db.commit()
    return _run_out(run)


@router.get("/runs", response_model=Page[RunOut], operation_id="listRuns")
def list_runs(
    project_id: uuid.UUID,
    status: RunStatus | None = None,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[RunOut]:
    project_roles(db, project_id, ctx.user)
    offset = decode_cursor(cursor)
    stmt = select(Run).where(Run.project_id == project_id)
    if status:
        stmt = stmt.where(Run.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(Run.created_at.desc(), Run.id).offset(offset).limit(limit)).scalars()
    return Page(
        items=[_run_out(r) for r in rows], page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total))
    )


@router.get("/runs/{run_id}", response_model=RunOut, operation_id="getRun")
def get_run(
    run_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> RunOut:
    return _run_out(load_run(db, run_id, ctx))


@router.get("/runs/{run_id}/nodes", response_model=list[NodeRunOut], operation_id="listNodeRuns")
def list_node_runs(
    run_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[NodeRunOut]:
    run = load_run(db, run_id, ctx)
    rows = db.execute(
        select(NodeRun, CapabilityVersion)
        .join(CapabilityVersion, CapabilityVersion.id == NodeRun.capability_version_id)
        .where(NodeRun.run_id == run.id)
        .order_by(NodeRun.position)
    ).all()
    return [
        NodeRunOut(
            id=n.id,
            node_id=n.node_id,
            capability_id=c.capability_id,
            capability_version=c.version,
            capability_version_id=c.id,
            status=n.status,
            execution_mode=n.execution_mode,
            attempt=n.attempt,
            duration_ms=n.duration_ms,
            input_sha256=n.input_sha256,
            output_sha256=n.output_sha256,
            output_summary=n.output_summary,
            llm=n.llm,
            error_code=n.error_code,
        )
        for n, c in rows
    ]


@router.get("/runs/{run_id}/trace", response_model=Page[dict[str, Any]], operation_id="getRunTrace")
def get_run_trace(
    run_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[dict[str, Any]]:
    run = load_run(db, run_id, ctx)
    offset = decode_cursor(cursor)
    total = db.execute(select(func.count()).where(RunEvent.run_id == run.id)).scalar_one()
    rows = db.execute(
        select(RunEvent.event).where(RunEvent.run_id == run.id).order_by(RunEvent.seq).offset(offset).limit(limit)
    ).scalars()
    return Page(items=list(rows), page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total)))


@router.get("/reviews", response_model=Page[ReviewTaskOut], operation_id="listReviewTasks")
def list_review_tasks(
    status: Literal["pending", "completed"] | None = None,
    assigned_to_me: bool = True,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None, max_length=200),
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Page[ReviewTaskOut]:
    roles = ("solution_lead", "business_reviewer")
    projects = select(ProjectMember.project_id).where(
        ProjectMember.user_id == ctx.user.id, ProjectMember.roles.overlap(list(roles))
    )
    if db.execute(select(func.count()).select_from(projects.subquery())).scalar_one() == 0:
        raise forbidden()
    offset = decode_cursor(cursor)
    stmt = select(ReviewTask).where(ReviewTask.project_id.in_(projects))
    if assigned_to_me:
        stmt = stmt.where(ReviewTask.assigned_to == ctx.user.id)
    if status:
        stmt = stmt.where(ReviewTask.status == status)
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(stmt.order_by(ReviewTask.created_at.desc(), ReviewTask.id).offset(offset).limit(limit)).scalars()
    return Page(
        items=[_review_out(t) for t in rows],
        page=PageInfo(total=total, next_cursor=encode_cursor(offset, limit, total)),
    )


def _load_review(db: Session, run_id: uuid.UUID, review_id: uuid.UUID, ctx: AuthContext, lock: bool) -> ReviewTask:
    run = load_run(db, run_id, ctx)
    stmt = select(ReviewTask).where(ReviewTask.id == review_id, ReviewTask.run_id == run.id)
    task = db.execute(stmt.with_for_update() if lock else stmt).scalar_one_or_none()
    if task is None:
        raise not_found()
    return task


@router.get("/runs/{run_id}/reviews/{review_id}", response_model=ReviewTaskOut, operation_id="getReviewTask")
def get_review_task(
    run_id: uuid.UUID,
    review_id: uuid.UUID,
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewTaskOut:
    return _review_out(_load_review(db, run_id, review_id, ctx, lock=False))


@router.post(
    "/runs/{run_id}/reviews/{review_id}/decision", response_model=ReviewTaskOut, operation_id="decideReviewTask"
)
def decide_review_task(
    run_id: uuid.UUID,
    review_id: uuid.UUID,
    body: ReviewDecision,
    idempotency_key: uuid.UUID = Header(),  # noqa: B008
    ctx: AuthContext = Depends(authenticated),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> ReviewTaskOut:
    task = _load_review(db, run_id, review_id, ctx, lock=True)
    require_project_role(db, task.project_id, ctx.user, {"business_reviewer"})
    if task.assigned_to != ctx.user.id:
        raise forbidden()
    corrections = [c.model_dump(exclude_none=True) for c in body.corrections]
    engine.decide_review(db, task, ctx.user.id, body.decision, corrections, body.comment, idempotency_key)
    db.commit()
    return _review_out(task)
