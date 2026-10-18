"""Immutable, idempotent registration of capability and rule pack versions."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.catalog.models import CapabilityVersion, RulePackVersion
from app.catalog.validation import Issue, content_sha256, validate_capability, validate_rule_pack
from app.core.errors import ApiError


def _invalid(issues: list[Issue]) -> ApiError:
    return ApiError(
        "contract_invalid",
        "契約の内容に誤りがあります。",
        422,
        [{"field": i.location, "reason": i.code} for i in issues[:50]],
    )


def _conflict() -> ApiError:
    return ApiError("version_conflict", "同じ版が異なる内容で登録済みです。版を上げてください。", 409)


def register_capability(db: Session, contract: dict[str, Any], user_id: uuid.UUID) -> tuple[CapabilityVersion, bool]:
    """Returns (version, created). Same canonical content → existing row; different content → 409."""
    issues = validate_capability(contract)
    if issues:
        raise _invalid(issues)
    digest = content_sha256(contract)
    key = (
        CapabilityVersion.capability_id == contract["capability_id"],
        CapabilityVersion.version == contract["version"],
    )
    existing = db.execute(select(CapabilityVersion).where(*key)).scalar_one_or_none()
    if existing is not None:
        if existing.content_sha256 != digest:
            raise _conflict()
        return existing, False
    row = CapabilityVersion(
        capability_id=contract["capability_id"],
        version=contract["version"],
        kind=contract["kind"],
        name=contract["name"],
        content_sha256=digest,
        contract=contract,
        registered_by=user_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:  # concurrent registration of the same id@version
        db.rollback()
        existing = db.execute(select(CapabilityVersion).where(*key)).scalar_one()
        if existing.content_sha256 != digest:
            raise _conflict() from None
        return existing, False
    return row, True


def register_rule_pack(db: Session, pack: dict[str, Any], user_id: uuid.UUID) -> tuple[RulePackVersion, bool]:
    issues = validate_rule_pack(pack)
    if issues:
        raise _invalid(issues)
    digest = content_sha256(pack)
    key = (RulePackVersion.rule_pack_id == pack["rule_pack_id"], RulePackVersion.version == pack["version"])
    existing = db.execute(select(RulePackVersion).where(*key)).scalar_one_or_none()
    if existing is not None:
        if existing.content_sha256 != digest:
            raise _conflict()
        return existing, False
    row = RulePackVersion(
        rule_pack_id=pack["rule_pack_id"],
        version=pack["version"],
        content_sha256=digest,
        rule_pack=pack,
        registered_by=user_id,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.execute(select(RulePackVersion).where(*key)).scalar_one()
        if existing.content_sha256 != digest:
            raise _conflict() from None
        return existing, False
    return row, True
