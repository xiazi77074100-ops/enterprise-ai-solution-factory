"""Capability and rule pack versions (immutable).

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

IMMUTABLE = ("capability_version", "rule_pack_version")


def upgrade() -> None:
    op.create_table(
        "capability_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("capability_id", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("contract", postgresql.JSONB(), nullable=False),
        sa.Column("registered_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("capability_id", "version"),
        sa.CheckConstraint("kind IN ('local','rest','mcp_tool','llm')", name="ck_capability_kind"),
    )
    op.create_table(
        "rule_pack_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("rule_pack_id", sa.String(64), nullable=False, index=True),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("rule_pack", postgresql.JSONB(), nullable=False),
        sa.Column("registered_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("rule_pack_id", "version"),
    )
    for table in IMMUTABLE:
        op.execute(
            f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_mutation()"
        )


def downgrade() -> None:
    for table in IMMUTABLE:
        op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
        op.drop_table(table)
