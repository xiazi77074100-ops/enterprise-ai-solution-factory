import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

ZERO_USAGE: dict[str, Any] = {"llm_input_tokens": 0, "llm_output_tokens": 0, "cost_jpy": 0, "cost_known": True}


class Run(Base):
    __tablename__ = "run"
    __table_args__ = (UniqueConstraint("solution_id", "created_by", "idempotency_key", name="uq_run_idempotency"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    solution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("solution.id"), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"), index=True)
    workflow_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16))
    execution_mode: Mapped[str] = mapped_column(String(8))
    trace_id: Mapped[str] = mapped_column(String(32))
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB)
    input_sha256: Mapped[str] = mapped_column(String(64))
    outputs: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    failure_code: Mapped[str | None] = mapped_column(String(64))
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    idempotency_key: Mapped[uuid.UUID]
    request_sha256: Mapped[str] = mapped_column(String(64))
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NodeRun(Base):
    __tablename__ = "node_run"
    __table_args__ = (UniqueConstraint("run_id", "node_id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("run.id"), index=True)
    node_id: Mapped[str] = mapped_column(String(32))
    position: Mapped[int] = mapped_column(Integer)
    capability_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("capability_version.id"))
    status: Mapped[str] = mapped_column(String(16), default="pending")
    execution_mode: Mapped[str] = mapped_column(String(8), default="real")
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    input_sha256: Mapped[str | None] = mapped_column(String(64))
    output_sha256: Mapped[str | None] = mapped_column(String(64))
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    output_summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    llm: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(64))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReviewTask(Base):
    __tablename__ = "review_task"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("run.id"), index=True)
    node_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("node_run.id"), unique=True)
    node_id: Mapped[str] = mapped_column(String(32))
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    assigned_to: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), index=True)
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    decision: Mapped[str | None] = mapped_column(String(32))
    corrections: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    comment: Mapped[str | None] = mapped_column(String(2000))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[uuid.UUID | None]
    request_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunEvent(Base):
    """Append-only (DB trigger). event_hash = SHA-256(JCS(event)); event.prev_event_hash chains the run's stream."""

    __tablename__ = "run_event"
    __table_args__ = (UniqueConstraint("run_id", "seq"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("run.id"))
    seq: Mapped[int] = mapped_column(Integer)
    event: Mapped[dict[str, Any]] = mapped_column(JSONB)
    event_hash: Mapped[str] = mapped_column(String(64))
