"""Solutions (workflow drafts and approved, frozen workflows).

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "solution",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("project.id"), nullable=False, index=True),
        sa.Column("requirement_revision_id", sa.Uuid(), sa.ForeignKey("requirement_revision.id"), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("workflow", postgresql.JSONB(), nullable=False),
        sa.Column("workflow_hash", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("app_user.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("state IN ('draft','validated','approved','archived')", name="ck_solution_state"),
        sa.CheckConstraint(
            "(state = 'approved') = (approved_by IS NOT NULL AND approved_at IS NOT NULL) OR state = 'archived'",
            name="ck_solution_approval",
        ),
    )
    # An approved solution is frozen: its workflow cannot change and the row cannot be deleted.
    op.execute(
        """
        CREATE FUNCTION reject_approved_solution_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          IF OLD.state IN ('approved', 'archived') AND (
               TG_OP = 'DELETE'
               OR NEW.workflow IS DISTINCT FROM OLD.workflow
               OR NEW.workflow_hash IS DISTINCT FROM OLD.workflow_hash
               OR NEW.approved_by IS DISTINCT FROM OLD.approved_by
               OR NOT (NEW.state = OLD.state OR (OLD.state = 'approved' AND NEW.state = 'archived'))) THEN
            RAISE EXCEPTION 'frozen solution: % on %', TG_OP, TG_TABLE_NAME
              USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN COALESCE(NEW, OLD);
        END;
        $$;
        """
    )
    op.execute(
        "CREATE TRIGGER solution_frozen BEFORE UPDATE OR DELETE ON solution "
        "FOR EACH ROW EXECUTE FUNCTION reject_approved_solution_change()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER solution_frozen ON solution")
    op.execute("DROP FUNCTION reject_approved_solution_change()")
    op.drop_table("solution")
