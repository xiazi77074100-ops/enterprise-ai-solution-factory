import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

SOLUTION_STATES = ("draft", "validated", "approved", "archived")


class Solution(Base):
    """A workflow for a project. Once approved, workflow and workflow_hash are frozen (application + DB trigger)."""

    __tablename__ = "solution"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("project.id"), index=True)
    requirement_revision_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirement_revision.id"))
    state: Mapped[str] = mapped_column(String(16), default="draft")
    workflow: Mapped[dict[str, Any]] = mapped_column(JSONB)
    workflow_hash: Mapped[str] = mapped_column(String(64))
    revision: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def etag(self) -> str:
        return f'"{self.workflow_hash}:{self.revision}"'
