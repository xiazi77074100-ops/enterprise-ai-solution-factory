"""Runs, node runs, review tasks and the append-only run event stream (run_execution.md §3〜§8).

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

RUN_STATUS = "'pending','running','waiting_review','succeeded','rejected','failed','cancelled'"
NODE_STATUS = "'pending','running','waiting_review','succeeded','failed','skipped'"


def upgrade() -> None:
    op.create_table(
        "run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("solution_id", sa.Uuid(), sa.ForeignKey("solution.id"), nullable=False, index=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("project.id"), nullable=False, index=True),
        sa.Column("workflow_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("execution_mode", sa.String(8), nullable=False),
        sa.Column("trace_id", sa.String(32), nullable=False),
        sa.Column("inputs", postgresql.JSONB(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("outputs", postgresql.JSONB()),
        sa.Column("failure_code", sa.String(64)),
        sa.Column("usage", postgresql.JSONB(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("solution_id", "created_by", "idempotency_key", name="uq_run_idempotency"),
        sa.CheckConstraint(f"status IN ({RUN_STATUS})", name="ck_run_status"),
        sa.CheckConstraint("execution_mode IN ('real','mock','mixed')", name="ck_run_mode"),
    )
    op.create_index("ix_run_claimable", "run", ["status", "lease_until"])
    op.create_table(
        "node_run",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("run.id"), nullable=False, index=True),
        sa.Column("node_id", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("capability_version_id", sa.Uuid(), sa.ForeignKey("capability_version.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("execution_mode", sa.String(8), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("input_sha256", sa.String(64)),
        sa.Column("output_sha256", sa.String(64)),
        sa.Column("output", postgresql.JSONB()),
        sa.Column("output_summary", postgresql.JSONB()),
        sa.Column("llm", postgresql.JSONB()),
        sa.Column("error_code", sa.String(64)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("run_id", "node_id"),
        sa.CheckConstraint(f"status IN ({NODE_STATUS})", name="ck_node_run_status"),
        sa.CheckConstraint("execution_mode IN ('real','mock')", name="ck_node_run_mode"),
        sa.CheckConstraint("attempt BETWEEN 1 AND 3", name="ck_node_run_attempt"),
    )
    op.create_table(
        "review_task",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("run.id"), nullable=False, index=True),
        sa.Column("node_run_id", sa.Uuid(), sa.ForeignKey("node_run.id"), nullable=False, unique=True),
        sa.Column("node_id", sa.String(32), nullable=False),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("project.id"), nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("assigned_to", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False, index=True),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("decision", sa.String(32)),
        sa.Column("corrections", postgresql.JSONB()),
        sa.Column("comment", sa.String(2000)),
        sa.Column("decided_by", sa.Uuid(), sa.ForeignKey("app_user.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("idempotency_key", sa.Uuid()),
        sa.Column("request_sha256", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending','completed')", name="ck_review_status"),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('approved','approved_with_corrections','rejected')",
            name="ck_review_decision",
        ),
        sa.CheckConstraint(
            "(status = 'completed') = (decision IS NOT NULL AND decided_by IS NOT NULL AND decided_at IS NOT NULL)",
            name="ck_review_completed",
        ),
    )
    op.create_table(
        "run_event",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("run_id", sa.Uuid(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("event", postgresql.JSONB(), nullable=False),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("run_id", "seq"),
    )
    # The trace is append-only (tamper evidence together with the hash chain).
    op.execute(
        "CREATE TRIGGER run_event_immutable BEFORE UPDATE OR DELETE ON run_event "
        "FOR EACH ROW EXECUTE FUNCTION reject_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER run_event_immutable ON run_event")
    op.drop_table("run_event")
    op.drop_table("review_task")
    op.drop_table("node_run")
    op.drop_index("ix_run_claimable", table_name="run")
    op.drop_table("run")
