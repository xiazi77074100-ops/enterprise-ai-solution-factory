"""Baseline: immutability guard used by versioned tables (ADR-004).

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Insurance layer for immutable rows (capability/rule pack/dataset versions); the app rejects first.
    op.execute(
        """
        CREATE FUNCTION reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
          RAISE EXCEPTION 'immutable row: % on %', TG_OP, TG_TABLE_NAME
            USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION reject_mutation()")
