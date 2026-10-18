import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class CapabilityVersion(Base):
    """Immutable (DB trigger + application). A change requires a new version."""

    __tablename__ = "capability_version"
    __table_args__ = (UniqueConstraint("capability_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    capability_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(100))
    content_sha256: Mapped[str] = mapped_column(String(64))
    contract: Mapped[dict[str, Any]] = mapped_column(JSONB)
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RulePackVersion(Base):
    __tablename__ = "rule_pack_version"
    __table_args__ = (UniqueConstraint("rule_pack_id", "version"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    rule_pack_id: Mapped[str] = mapped_column(String(64), index=True)
    version: Mapped[str] = mapped_column(String(32))
    content_sha256: Mapped[str] = mapped_column(String(64))
    rule_pack: Mapped[dict[str, Any]] = mapped_column(JSONB)
    registered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
