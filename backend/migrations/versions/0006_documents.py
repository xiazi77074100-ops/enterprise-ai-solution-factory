"""Uploaded documents (docs/design/detail/documents.md). The file itself lives in EASF_STORAGE_DIR.

Revision ID: 0006
Revises: 0005
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("project_id", sa.Uuid(), sa.ForeignKey("project.id"), nullable=False, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("data_origin", sa.String(16), nullable=False),
        sa.Column("storage_name", sa.String(32), nullable=False, unique=True),
        sa.Column("uploaded_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("media_type IN ('application/pdf','image/png','image/jpeg')", name="ck_document_media_type"),
        sa.CheckConstraint("size_bytes BETWEEN 1 AND 10485760", name="ck_document_size"),
        sa.CheckConstraint("page_count BETWEEN 1 AND 30", name="ck_document_pages"),
        sa.CheckConstraint("data_origin = 'synthetic'", name="ck_document_origin"),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_document_sha256"),
        sa.CheckConstraint("storage_name ~ '^[0-9a-f]{32}$'", name="ck_document_storage_name"),
    )
    # The stored bytes never change, so neither does the row (evidence points at its sha256). Deletion stays
    # possible for the retention procedure (ADR-004).
    op.execute(
        "CREATE TRIGGER document_immutable BEFORE UPDATE ON document FOR EACH ROW EXECUTE FUNCTION reject_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER document_immutable ON document")
    op.drop_table("document")
